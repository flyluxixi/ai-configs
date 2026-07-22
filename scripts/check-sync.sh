#!/bin/bash
# ============================================================
# 源库 ↔ 本机 同步一致性检查
#
# 检查项：
#   1. symlink 指向（~/.claude/CLAUDE.md、~/.claude/luxixi、~/.claude/rules、
#      ~/.codex/AGENTS.md、~/.codex/luxixi、仓库内 codex/luxixi）
#   2. claude/skills/*  ↔ ~/.claude/skills/*
#   3. codex/skills/*   ↔ ~/.codex/skills/*
#   4. claude/agents/*  ↔ ~/.claude/agents/*
#   5. claude/settings.json ↔ ~/.claude/settings.json
#
# 只核对以仓库为源头的文件；本机侧多出的第三方资产（update.sh 安装）不算漂移。
#
# 用法：bash ~/projects/ai-configs/scripts/check-sync.sh
# 退出码：0 = 全部一致；1 = 存在漂移
# ============================================================

set -uo pipefail
shopt -s nullglob

REPO="$HOME/projects/ai-configs"
DRIFT=0

drift() {
    DRIFT=1
    echo "✗ $1"
}

check_symlink() {
    local link="$1" expect="$2" actual
    actual=$(readlink "$link" 2>/dev/null || true)
    if [ "$actual" = "$expect" ]; then
        echo "✓ $link -> $expect"
    else
        drift "$link 应指向 $expect，实际：${actual:-不存在或不是 symlink}"
    fi
}

echo "== 1/5 symlink 指向 =="
check_symlink "$HOME/.claude/CLAUDE.md" "$REPO/claude/CLAUDE.md"
check_symlink "$HOME/.claude/luxixi"    "$REPO/claude/luxixi"
check_symlink "$HOME/.claude/rules"     "$REPO/claude/rules"
check_symlink "$HOME/.codex/AGENTS.md"  "$REPO/codex/AGENTS.md"
check_symlink "$HOME/.codex/luxixi"     "$REPO/claude/luxixi"
check_symlink "$REPO/codex/luxixi"      "../claude/luxixi"

echo
echo "== 2/5 claude/skills ↔ ~/.claude/skills =="
for dir in "$REPO"/claude/skills/*/; do
    name=$(basename "$dir")
    target="$HOME/.claude/skills/$name"
    if [ ! -d "$target" ]; then
        drift "skill $name：~/.claude/skills/ 缺失，需 cp"
    elif diff -rq "$dir" "$target" >/dev/null 2>&1; then
        echo "✓ $name"
    else
        drift "skill $name 内容漂移："
        diff -rq "$dir" "$target" 2>/dev/null | sed 's/^/    /'
    fi
done

echo
echo "== 3/5 codex/skills ↔ ~/.codex/skills =="
for dir in "$REPO"/codex/skills/*/; do
    name=$(basename "$dir")
    target="$HOME/.codex/skills/$name"
    if [ ! -d "$target" ]; then
        drift "skill $name：~/.codex/skills/ 缺失，需 cp"
    elif diff -rq "$dir" "$target" >/dev/null 2>&1; then
        echo "✓ $name"
    else
        drift "skill $name 内容漂移："
        diff -rq "$dir" "$target" 2>/dev/null | sed 's/^/    /'
    fi
done

echo
echo "== 4/5 claude/agents ↔ ~/.claude/agents =="
for file in "$REPO"/claude/agents/*.md; do
    name=$(basename "$file")
    target="$HOME/.claude/agents/$name"
    if [ ! -f "$target" ]; then
        drift "agent $name：~/.claude/agents/ 缺失，需 cp"
    elif diff -q "$file" "$target" >/dev/null 2>&1; then
        echo "✓ $name"
    else
        drift "agent $name 内容漂移（比较两侧 mtime 判断方向后 cp）"
    fi
done

echo
echo "== 5/5 claude/settings.json ↔ ~/.claude/settings.json =="
if diff -q "$REPO/claude/settings.json" "$HOME/.claude/settings.json" >/dev/null 2>&1; then
    echo "✓ settings.json 一致"
else
    drift "settings.json 漂移（CLI 会动态改写本机侧，按根 CLAUDE.md 约定合并后双向 cp）："
    diff "$REPO/claude/settings.json" "$HOME/.claude/settings.json" 2>/dev/null | head -40 | sed 's/^/    /'
fi

echo
if [ "$DRIFT" -eq 0 ]; then
    echo "✅ 全部一致"
else
    echo "⚠️  存在漂移，处理约定见根 CLAUDE.md「维护规则」"
fi
exit "$DRIFT"
