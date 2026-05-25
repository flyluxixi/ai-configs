#!/usr/bin/env python3
"""Generate an image with OpenAI Images API using gpt-image-2."""

from __future__ import annotations

import argparse
import base64
import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

API_URL = "https://api.openai.com/v1/images/generations"
MODEL = "gpt-image-2"
SIZE_RE = re.compile(r"^(\d+)x(\d+)$")
MIN_PIXELS = 655_360
MAX_PIXELS = 8_294_400
MAX_EDGE = 3_840
MAX_RATIO = 3.0
MAX_ERROR_CHARS = 1_200


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate an image with OpenAI Images API using gpt-image-2."
    )
    parser.add_argument("--prompt", required=True, help="Text prompt for the image.")
    parser.add_argument("--output", required=True, help="Output image file path.")
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
        "--format",
        dest="output_format",
        default="png",
        choices=("png", "jpeg", "webp"),
        help="Output image format.",
    )
    parser.add_argument(
        "--compression",
        type=int,
        default=None,
        help="JPEG/WebP compression level from 0 to 100. Not valid for PNG.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite the output file if it already exists.",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=180.0,
        help="HTTP timeout in seconds. Complex image requests can take up to 2 minutes.",
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


def validate_args(args: argparse.Namespace) -> Path:
    if not args.prompt.strip():
        fail("--prompt cannot be empty")

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        fail("OPENAI_API_KEY is not set")

    validate_size(args.size)

    if args.compression is not None:
        if args.output_format == "png":
            fail("--compression is only valid when --format is jpeg or webp")
        if args.compression < 0 or args.compression > 100:
            fail("--compression must be between 0 and 100")

    output_path = Path(args.output).expanduser()
    if output_path.exists() and output_path.is_dir():
        fail(f"output path is a directory: {output_path}")
    if output_path.exists() and not args.overwrite:
        fail(f"output file already exists: {output_path} (use --overwrite to replace it)")

    return output_path


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
        fail(f"OpenAI API returned HTTP {exc.code}: {details}")
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


def main() -> None:
    args = parse_args()
    output_path = validate_args(args)
    image_bytes = call_images_api(args)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(image_bytes)
    print(f"saved {len(image_bytes)} bytes to {output_path}")


if __name__ == "__main__":
    main()
