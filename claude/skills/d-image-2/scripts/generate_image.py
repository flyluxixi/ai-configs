#!/usr/bin/env python3
"""Generate an image with two interchangeable backends.

后端（--via）：
  - openai：走公开 Images API + OPENAI_API_KEY，显式 gpt-image-2，纯标准库。
  - codex ：复用本机 Codex CLI 的 ChatGPT 登录态（~/.codex/auth.json），打
            chatgpt.com/backend-api/codex/responses 的 image_generation 工具，
            免单独 API key 计费；需要 curl_cffi 过 Cloudflare TLS 指纹。

⚠️ codex 后端依赖逆向得来的 ChatGPT 内部端点 + Codex 的 OAuth client_id，属
   非官方用法：OpenAI 调整端点/版本下限/模型时随时可能失效，且用订阅登录态驱动
   自动化端点踩 ToS，账号有风险。openai 后端是稳定契约路径，二者按需取舍。
"""

from __future__ import annotations

import argparse
import base64
import fcntl
import json
import os
import re
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# ---- openai 后端常量 -------------------------------------------------------
API_URL = "https://api.openai.com/v1/images/generations"
MODEL = "gpt-image-2"
SIZE_RE = re.compile(r"^(\d+)x(\d+)$")
MIN_PIXELS = 655_360
MAX_PIXELS = 8_294_400
MAX_EDGE = 3_840
MAX_RATIO = 3.0
MAX_ERROR_CHARS = 1_200

# ---- codex 后端：写死的稳定常量（各自失效条件见注释）-----------------------
# 复用 Codex CLI 的 OAuth client_id（public client，无 secret，可公开抄）。
# 失效条件：OpenAI 轮换 codex 的 OAuth app，或开始校验 client_id 与请求来源绑定。
OAUTH_CLIENT_ID = "app_EMoamEEZ73f0CkXaXp7hrann"
# 失效条件：OpenAI 改 OAuth 刷新端点路径。
TOKEN_REFRESH_URL = "https://auth.openai.com/oauth/token"
# 失效条件：OpenAI 改 ChatGPT 后端 Codex 端点路径，或下线该端点。
RESPONSES_URL = "https://chatgpt.com/backend-api/codex/responses"
# 失效条件：后端改 originator 识别逻辑。
ORIGINATOR = "codex_cli_rs"
# 编排模型读不到本机配置时的兜底。
FALLBACK_ORCH_MODEL = "gpt-5.5"
# codex --version 读不到时的兜底。
FALLBACK_CODEX_VERSION = "0.135.0"
# access_token 过期前提前量（秒），留刷新缓冲。
EXPIRY_BUFFER_S = 5 * 60
REFRESH_TIMEOUT_S = 15
MAX_EDIT_IMAGES = 5
MIME_BY_EXT = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
    ".gif": "image/gif",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate an image via the openai or codex backend."
    )
    parser.add_argument("--prompt", required=True, help="Text prompt for the image.")
    parser.add_argument("--output", required=True, help="Output image file path.")
    parser.add_argument(
        "--via",
        choices=("codex", "openai"),
        default="codex",
        help="Backend: 'codex' reuses Codex login (no API key), 'openai' uses OPENAI_API_KEY.",
    )
    parser.add_argument(
        "--size",
        default="1024x1024",
        help="Image size, such as 1024x1024, 1536x1024, 1024x1536, or auto.",
    )
    parser.add_argument(
        "--quality",
        default="high",
        choices=("low", "medium", "high", "auto"),
        help="Rendering quality.",
    )
    parser.add_argument(
        "--background",
        default="auto",
        choices=("transparent", "opaque", "auto"),
        help="Background mode. Non-auto only valid for --via codex.",
    )
    parser.add_argument(
        "--image",
        dest="images",
        action="append",
        default=[],
        metavar="PATH",
        help="Input image for image-to-image (repeatable, 1-5). Only for --via codex.",
    )
    parser.add_argument(
        "--model",
        default=None,
        help="Orchestration model for --via codex (default: read ~/.codex/config.toml).",
    )
    parser.add_argument(
        "--format",
        dest="output_format",
        default="png",
        choices=("png", "jpeg", "webp"),
        help="Output image format. Only for --via openai.",
    )
    parser.add_argument(
        "--compression",
        type=int,
        default=None,
        help="JPEG/WebP compression 0-100. Only for --via openai (not valid for PNG).",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite the output file if it already exists.",
    )
    parser.add_argument(
        "--codex-home",
        default=None,
        help="Codex home dir for --via codex (default: $CODEX_HOME or ~/.codex).",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=600.0,
        help="HTTP timeout in seconds. Codex turns can take minutes.",
    )
    return parser.parse_args()


def fail(message: str) -> None:
    print(f"error: {message}", file=sys.stderr)
    raise SystemExit(1)


def validate_size(size: str) -> None:
    if size == "auto":
        return

    match = SIZE_RE.match(size)
    if not match:
        fail("--size must be 'auto' or WIDTHxHEIGHT, for example 1024x1024")

    width = int(match.group(1))
    height = int(match.group(2))
    pixels = width * height
    short_edge = min(width, height)
    long_edge = max(width, height)

    if width <= 0 or height <= 0:
        fail("--size dimensions must be positive")
    if width % 16 != 0 or height % 16 != 0:
        fail("--size dimensions must both be multiples of 16 for gpt-image-2")
    if long_edge > MAX_EDGE:
        fail(f"--size maximum edge must be <= {MAX_EDGE}px for gpt-image-2")
    if long_edge / short_edge > MAX_RATIO:
        fail("--size long edge to short edge ratio must not exceed 3:1")
    if pixels < MIN_PIXELS or pixels > MAX_PIXELS:
        fail(f"--size total pixels must be between {MIN_PIXELS} and {MAX_PIXELS}")


def resolve_output_path(args: argparse.Namespace) -> Path:
    output_path = Path(args.output).expanduser()
    if output_path.exists() and output_path.is_dir():
        fail(f"output path is a directory: {output_path}")
    if output_path.exists() and not args.overwrite:
        fail(f"output file already exists: {output_path} (use --overwrite to replace it)")
    return output_path


def write_image(output_path: Path, image_bytes: bytes) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(image_bytes)
    print(f"saved {len(image_bytes)} bytes to {output_path}")


# ===========================================================================
# openai backend
# ===========================================================================
def summarize_api_error(raw_body: bytes) -> str:
    text = raw_body.decode("utf-8", errors="replace")
    try:
        data: Any = json.loads(text)
    except json.JSONDecodeError:
        return text[:MAX_ERROR_CHARS]

    error = data.get("error") if isinstance(data, dict) else None
    if isinstance(error, dict):
        message = error.get("message") or error.get("code") or error.get("type")
        if message:
            return str(message)[:MAX_ERROR_CHARS]
    return text[:MAX_ERROR_CHARS]


def format_http_error(status_code: int, details: str) -> str:
    normalized = details.lower()
    if (
        "billing hard limit" in normalized
        or "usage limit" in normalized
        or "insufficient_quota" in normalized
    ):
        return (
            "OpenAI API usage or billing limit reached. The d-image-2 command is "
            "working, but this API key's organization cannot create new images "
            "until the API budget/usage limit is increased or quota becomes "
            f"available again. Original API error: HTTP {status_code}: {details}"
        )
    return f"OpenAI API returned HTTP {status_code}: {details}"


def call_images_api(args: argparse.Namespace) -> bytes:
    api_key = os.environ["OPENAI_API_KEY"]
    payload: dict[str, Any] = {
        "model": MODEL,
        "prompt": args.prompt,
        "size": args.size,
        "quality": args.quality,
        "output_format": args.output_format,
    }
    if args.compression is not None:
        payload["output_compression"] = args.compression

    request = urllib.request.Request(
        API_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=args.timeout) as response:
            response_body = response.read()
    except urllib.error.HTTPError as exc:
        details = summarize_api_error(exc.read())
        fail(format_http_error(exc.code, details))
    except urllib.error.URLError as exc:
        fail(f"OpenAI API request failed: {exc.reason}")

    try:
        data = json.loads(response_body.decode("utf-8"))
    except json.JSONDecodeError as exc:
        fail(f"OpenAI API returned invalid JSON: {exc}")

    images = data.get("data") if isinstance(data, dict) else None
    if not isinstance(images, list) or not images:
        fail("OpenAI API response did not include data[0]")

    image_base64 = images[0].get("b64_json") if isinstance(images[0], dict) else None
    if not isinstance(image_base64, str) or not image_base64:
        fail("OpenAI API response did not include data[0].b64_json")

    try:
        return base64.b64decode(image_base64, validate=True)
    except ValueError as exc:
        fail(f"OpenAI API returned invalid base64 image data: {exc}")


def run_openai(args: argparse.Namespace) -> None:
    if args.images:
        fail("--image (image-to-image) is only available with --via codex")
    if args.background != "auto":
        fail("--background is only available with --via codex (gpt-image-2 has no transparency)")
    if not os.environ.get("OPENAI_API_KEY"):
        fail("OPENAI_API_KEY is not set")
    validate_size(args.size)
    if args.compression is not None:
        if args.output_format == "png":
            fail("--compression is only valid when --format is jpeg or webp")
        if args.compression < 0 or args.compression > 100:
            fail("--compression must be between 0 and 100")

    output_path = resolve_output_path(args)
    write_image(output_path, call_images_api(args))


# ===========================================================================
# codex backend — auth (stdlib only; only the final image call needs curl_cffi)
# ===========================================================================
def default_codex_home(args: argparse.Namespace) -> Path:
    if args.codex_home:
        return Path(args.codex_home).expanduser()
    return Path(os.environ.get("CODEX_HOME") or (Path.home() / ".codex"))


def decode_jwt_payload(jwt: str) -> dict[str, Any] | None:
    parts = jwt.split(".")
    if len(parts) < 2:
        return None
    try:
        padded = parts[1] + "=" * (-len(parts[1]) % 4)
        return json.loads(base64.urlsafe_b64decode(padded))
    except (ValueError, json.JSONDecodeError):
        return None


def load_tokens(codex_home: Path) -> dict[str, str]:
    path = codex_home / "auth.json"
    if not path.exists():
        fail(f"{path} not found; run `codex login` first")
    try:
        raw = json.loads(path.read_text("utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        fail(f"failed to parse {path}: {exc}")

    tokens = raw.get("tokens") if isinstance(raw, dict) else None
    if not isinstance(tokens, dict) or not tokens.get("access_token"):
        fail(f"{path} has no valid tokens.access_token; re-run `codex login`")

    return {
        "access_token": tokens.get("access_token", ""),
        "id_token": tokens.get("id_token", ""),
        "refresh_token": tokens.get("refresh_token", ""),
        "account_id": tokens.get("account_id", ""),
    }


def is_token_expired(access_token: str) -> bool:
    payload = decode_jwt_payload(access_token)
    exp = payload.get("exp") if payload else None
    if not isinstance(exp, (int, float)):
        return True
    return time.time() >= exp - EXPIRY_BUFFER_S


def extract_account_id(access_token: str) -> str | None:
    payload = decode_jwt_payload(access_token)
    auth = payload.get("https://api.openai.com/auth") if payload else None
    if isinstance(auth, dict):
        account_id = auth.get("chatgpt_account_id")
        if isinstance(account_id, str):
            return account_id
    return None


def refresh_tokens(refresh_token: str) -> dict[str, str]:
    body = json.dumps(
        {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "client_id": OAUTH_CLIENT_ID,
        }
    ).encode("utf-8")
    request = urllib.request.Request(
        TOKEN_REFRESH_URL,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=REFRESH_TIMEOUT_S) as response:
            data = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        fail(f"token refresh failed: HTTP {exc.code}; re-run `codex login`")
    except urllib.error.URLError as exc:
        fail(f"token refresh request failed: {exc.reason}")
    except json.JSONDecodeError as exc:
        fail(f"token refresh returned invalid JSON: {exc}")

    return {
        "access_token": data.get("access_token", ""),
        "id_token": data.get("id_token", ""),
        "refresh_token": data.get("refresh_token", "") or refresh_token,
        "account_id": "",
    }


def save_tokens_merged(codex_home: Path, tokens: dict[str, str]) -> None:
    """读-合并-原子写回 auth.json。读失败时拒绝回写，避免把损坏/半写文件
    覆盖成缩水版而丢掉 refresh_token 等字段；写入走临时文件 + fsync + os.replace
    原子替换，并保留 0600 权限。调用方须持有 codex_home 的刷新锁（见 ensure_valid_token）。"""
    path = codex_home / "auth.json"
    try:
        existing = json.loads(path.read_text("utf-8")) if path.exists() else {}
    except (OSError, json.JSONDecodeError) as exc:
        fail(f"refusing to rewrite {path}: cannot read current content ({exc}); re-run `codex login`")
    if not isinstance(existing, dict):
        fail(f"refusing to rewrite {path}: unexpected content; re-run `codex login`")

    prev = existing.get("tokens") if isinstance(existing.get("tokens"), dict) else {}
    updates = {k: v for k, v in tokens.items() if v not in ("", None)}
    merged = {
        **existing,
        "tokens": {**prev, **updates},
        "last_refresh": datetime.now(timezone.utc).isoformat(),
    }
    data = json.dumps(merged, indent=2).encode("utf-8")

    fd, tmp_name = tempfile.mkstemp(dir=str(path.parent), prefix=".auth-", suffix=".tmp")
    try:
        os.write(fd, data)
        os.fsync(fd)
        os.fchmod(fd, 0o600)
    finally:
        os.close(fd)
    try:
        os.replace(tmp_name, path)
    except OSError:
        os.unlink(tmp_name)
        raise


def ensure_valid_token(codex_home: Path) -> tuple[str, str]:
    """在 codex_home 的独占文件锁内完成「判过期 → 刷新 → 写回」临界区，
    串行化并发刷新；锁内重新 load_tokens，避免用旧 refresh_token 覆盖他人刚写的新值。"""
    codex_home.mkdir(parents=True, exist_ok=True)
    lock_path = codex_home / ".auth.lock"
    with open(lock_path, "w") as lock_file:
        fcntl.flock(lock_file, fcntl.LOCK_EX)  # POSIX 独占锁，进程退出/关闭自动释放
        tokens = load_tokens(codex_home)
        access_token = tokens["access_token"]
        if is_token_expired(access_token):
            if not tokens["refresh_token"]:
                fail("access_token expired and no refresh_token; re-run `codex login`")
            refreshed = refresh_tokens(tokens["refresh_token"])
            if not refreshed["access_token"]:
                fail("token refresh returned empty access_token; re-run `codex login`")
            access_token = refreshed["access_token"]
            account_id = extract_account_id(access_token) or tokens["account_id"]
            save_tokens_merged(codex_home, {**refreshed, "account_id": account_id})
            return access_token, account_id
        account_id = extract_account_id(access_token) or tokens["account_id"]
        return access_token, account_id


# ===========================================================================
# codex backend — request build / SSE parse
# ===========================================================================
def read_codex_version() -> str:
    try:
        result = subprocess.run(
            ["codex", "--version"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        match = re.search(r"(\d+\.\d+\.\d+)", result.stdout)
        if match:
            return match.group(1)
    except (OSError, subprocess.SubprocessError):
        pass
    return FALLBACK_CODEX_VERSION


def read_orchestration_model(codex_home: Path, override: str | None) -> str:
    if override:
        return override
    config_path = codex_home / "config.toml"
    if config_path.exists():
        try:
            for line in config_path.read_text("utf-8").splitlines():
                match = re.match(r'^\s*model\s*=\s*["\']?([^"\'\n#]+)', line)
                if match:
                    return match.group(1).strip()
        except OSError:
            pass
    return FALLBACK_ORCH_MODEL


def image_to_data_url(path_str: str) -> str:
    path = Path(path_str).expanduser()
    if not path.exists():
        fail(f"input image not found: {path}")
    mime = MIME_BY_EXT.get(path.suffix.lower())
    if not mime:
        fail(f"unsupported image type: {path.suffix or '(no ext)'} (png/jpg/jpeg/webp/gif)")
    return f"data:{mime};base64,{base64.b64encode(path.read_bytes()).decode('ascii')}"


def codex_headers(token: str, account_id: str, codex_version: str) -> dict[str, str]:
    headers = {
        "Authorization": f"Bearer {token}",
        "originator": ORIGINATOR,
        "User-Agent": f"{ORIGINATOR}/{codex_version}",
        "Content-Type": "application/json",
        "Accept": "text/event-stream",
        "x-codex-turn-metadata": json.dumps(
            {
                "session_id": str(uuid.uuid4()),
                "turn_id": str(uuid.uuid4()),
                "sandbox": "seatbelt",
            }
        ),
    }
    if account_id:
        headers["ChatGPT-Account-Id"] = account_id
    return headers


def build_codex_request(args: argparse.Namespace, model: str) -> dict[str, Any]:
    tool: dict[str, Any] = {"type": "image_generation"}
    if args.size and args.size != "auto":
        tool["size"] = args.size
    if args.quality and args.quality != "auto":
        tool["quality"] = args.quality
    if args.background and args.background != "auto":
        tool["background"] = args.background

    content: list[dict[str, Any]] = [{"type": "input_text", "text": args.prompt}]
    for image_path in args.images:
        content.append({"type": "input_image", "image_url": image_to_data_url(image_path)})

    return {
        "model": model,
        "instructions": (
            "You are an image generation assistant. When the user requests an image, "
            "immediately call the image_generation tool to create or edit it. "
            "Do not ask clarifying questions."
        ),
        "input": [{"type": "message", "role": "user", "content": content}],
        "tools": [tool],
        "tool_choice": "auto",
        "stream": True,
        "store": False,
        "reasoning": {"effort": "low"},
        "text": {"verbosity": "low"},
        "include": ["reasoning.encrypted_content"],
    }


def parse_sse(text: str) -> list[dict[str, Any]]:
    """按 SSE 规范解析：事件以空行分隔，块内多个 `data:` 行用换行聚合后再解析。
    兼容当前后端的单行 data 形态，同时不在多行 data 时静默丢事件。"""
    events: list[dict[str, Any]] = []
    for block in re.split(r"\r?\n\r?\n", text):
        data_lines = [line[5:].lstrip() for line in block.splitlines() if line.startswith("data:")]
        if not data_lines:
            continue
        data = "\n".join(data_lines).strip()
        if not data or data == "[DONE]":
            continue
        try:
            events.append(json.loads(data))
        except json.JSONDecodeError:
            continue
    return events


def extract_image_b64(text: str) -> str:
    """从 SSE 事件流取最终图片。失败事件优先：只要出现 response.failed/error 就报错，
    不把已流出的 partial preview 当成功；仅接受最终完成事件
    response.output_item.done 里 image_generation_call 的 result。
    没有最终结果（如连接被截断只剩 partial）一律按失败处理，绝不写半成品。"""
    events = parse_sse(text)

    # 1) 失败事件优先，避免把失败/中断当成功
    for event in events:
        if event.get("type") in ("response.failed", "error"):
            response = event.get("response") if isinstance(event.get("response"), dict) else {}
            err = event.get("error") or response.get("error") or {}
            message = err.get("message") if isinstance(err, dict) else None
            fail(f"image generation failed: {message or 'backend reported failure'}")

    # 2) 仅接受最终完成事件里的 result
    final_b64: str | None = None
    for event in events:
        item = event.get("item")
        if (
            event.get("type") == "response.output_item.done"
            and isinstance(item, dict)
            and item.get("type") == "image_generation_call"
        ):
            result = item.get("result")
            if isinstance(result, str) and len(result) > 100:
                final_b64 = result

    if not final_b64:
        fail("image generation failed: no completed image in stream (possibly truncated)")
    return final_b64


def map_codex_http_error(status: int, text: str) -> str:
    try:
        data = json.loads(text)
        detail = (
            data.get("error", {}).get("message")
            or data.get("message")
            or data.get("detail")
            or text[:300]
        )
    except (json.JSONDecodeError, AttributeError):
        detail = text[:300]

    if status in (401, 403):
        return (
            f"codex auth/permission failed ({status}): account may be free-tier; "
            f"image generation needs ChatGPT Plus/Pro. {detail}"
        )
    if status == 429:
        return f"codex rate limited (429): retry later. {detail}"
    if status == 400:
        return f"codex request rejected (400): {detail}"
    return f"codex backend returned {status}: {detail}"


def run_codex(args: argparse.Namespace) -> None:
    if args.images and not (1 <= len(args.images) <= MAX_EDIT_IMAGES):
        fail(f"image-to-image needs 1-{MAX_EDIT_IMAGES} input images, got {len(args.images)}")
    if args.compression is not None:
        print("warning: --compression is ignored with --via codex", file=sys.stderr)

    validate_size(args.size)
    output_path = resolve_output_path(args)

    try:
        from curl_cffi import requests as cffi_requests
    except ImportError:
        fail(
            "--via codex needs curl_cffi (TLS-fingerprint client to pass Cloudflare). "
            "Install it: pip3 install curl_cffi"
        )

    codex_home = default_codex_home(args)
    access_token, account_id = ensure_valid_token(codex_home)
    model = read_orchestration_model(codex_home, args.model)
    codex_version = read_codex_version()

    payload = build_codex_request(args, model)
    headers = codex_headers(access_token, account_id, codex_version)

    try:
        response = cffi_requests.post(
            RESPONSES_URL,
            headers=headers,
            data=json.dumps(payload),
            impersonate="chrome",
            timeout=args.timeout,
            allow_redirects=False,
        )
    except Exception as exc:  # curl_cffi raises its own RequestsError family
        fail(f"codex request failed: {exc}")

    if response.status_code != 200:
        fail(map_codex_http_error(response.status_code, response.text))

    b64 = extract_image_b64(response.text)
    try:
        image_bytes = base64.b64decode(b64, validate=True)
    except ValueError as exc:
        fail(f"codex backend returned invalid base64 image data: {exc}")
    write_image(output_path, image_bytes)


def main() -> None:
    args = parse_args()
    if not args.prompt.strip():
        fail("--prompt cannot be empty")
    if args.via == "openai":
        run_openai(args)
    else:
        run_codex(args)


if __name__ == "__main__":
    main()
