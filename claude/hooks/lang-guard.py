#!/usr/bin/env python3
"""Stop hook：检测助手回复里的语言漂移（日语假名 / 韩文谚文），命中则拦截并要求用简体中文重写。

依据 ~/.claude/CLAUDE.md「语言规范」：回复正文一律简体中文，禁止串入日语 / 韩语等。
本脚本是 harness 层强制，弥补模型自觉失效的场景。仅 Claude Code 生效（Codex 不读 settings.json hooks）。

行为：
- 读取 transcript 最后一条 assistant 文本回复。
- 扫描前先剥离代码块与行内反引号——这样在正文里用 `の` 形式举例外语词不会误伤，也给合法引用留了出口。
- 命中假名 / 谚文 → 输出 {"decision":"block","reason":...}，harness 把 reason 回喂给模型要求重写。
- stop_hook_active 为真（已处于一次拦截后的续写）时直接放行，保证每轮最多拦一次，杜绝死循环。
- 任何异常一律 fail-open（exit 0 不拦截），不因守卫脚本本身打断会话。
"""
import sys
import json
import re

# 日语平假名 / 片假名（排除中点 ・U+30FB，中文也用）、韩文谚文音节与字母
DRIFT_RE = re.compile(
    r"[぀-ゟ゠-ヺー-ヿ가-힣ᄀ-ᇿ㄰-㆏]"
)


def last_assistant_text(transcript_path):
    try:
        with open(transcript_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
    except Exception:
        return ""
    for line in reversed(lines):
        line = line.strip()
        if not line:
            continue
        try:
            ev = json.loads(line)
        except Exception:
            continue
        if ev.get("type") != "assistant":
            continue
        content = ev.get("message", {}).get("content", [])
        parts = []
        if isinstance(content, list):
            for block in content:
                if isinstance(block, dict) and block.get("type") == "text":
                    parts.append(block.get("text", ""))
        elif isinstance(content, str):
            parts.append(content)
        text = "".join(parts)
        if text.strip():
            return text
    return ""


def main():
    try:
        data = json.load(sys.stdin)
    except Exception:
        sys.exit(0)

    # 已在拦截后的续写轮，放行避免死循环
    if data.get("stop_hook_active"):
        sys.exit(0)

    transcript_path = data.get("transcript_path")
    if not transcript_path:
        sys.exit(0)

    text = last_assistant_text(transcript_path)
    if not text.strip():
        sys.exit(0)

    # 剥离 ```代码块``` 与 `行内代码`，再扫描正文
    scan = re.sub(r"```.*?```", "", text, flags=re.S)
    scan = re.sub(r"`[^`]*`", "", scan)

    hit = DRIFT_RE.search(scan)
    if not hit:
        sys.exit(0)

    reason = (
        "上一条回复检测到非简体中文字符（日语假名或韩文谚文：「{0}」），属于语言漂移，"
        "违反 CLAUDE.md 语言规范。请立即用纯简体中文重写整条回复，正文不得夹杂任何"
        "日语 / 韩语词汇、假名或谚文；代码标识符、命令、英文技术术语不受影响，"
        "确需举例外语词时放进反引号或代码块。"
    ).format(hit.group(0))

    print(json.dumps({"decision": "block", "reason": reason}, ensure_ascii=False))
    sys.exit(0)


if __name__ == "__main__":
    main()
