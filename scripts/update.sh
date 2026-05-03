#!/bin/bash

# ============================================================
# AI 工具配置自动更新脚本 v13-mac
#
# 更新内容：
#   0. Claude CLI 本身
#   0.5. Codex CLI 本身
#   1. everything-claude-code          — agents / skills / commands
#   2. superpowers                     — systematic-debugging / verification-before-completion
#   3. anthropics/claude-plugins-official — frontend-design / code-review /
#                                           skill-creator / claude-md-management /
#                                           agent-sdk-dev / claude-code-setup /
#                                           mcp-server-dev / php-lsp / plugin-dev /
#                                           feature-dev
#   4. nextlevelbuilder/ui-ux-pro-max-skill — ui-ux-pro-max skill
#   5. jnMetaCode/agency-agents-zh     — engineering-wechat-mini-program-developer agent
#
# 用法：
#   手动执行：bash ~/projects/ai-configs/scripts/update.sh
#   cron（日志按天写入 scripts/update-logs/）：
#   0 10 * * * bash ~/projects/ai-configs/scripts/update.sh
#
# macOS 注意事项：
#   - PATH 中加入了 Homebrew（/opt/homebrew/bin）和 npm global 路径
#   - claude / codex 均通过 npm global 安装，路径已包含
#   - cron 在 macOS 上需要授予"完全磁盘访问"权限给 /usr/sbin/cron
#     路径：系统设置 → 隐私与安全性 → 完全磁盘访问
# ============================================================

set -uo pipefail

# macOS: 加入 Homebrew 路径（Apple Silicon: /opt/homebrew/bin，Intel: /usr/local/bin）
export PATH="/opt/homebrew/bin:/opt/homebrew/sbin:$HOME/.npm-global/bin:/usr/local/bin:/usr/bin:/bin:$PATH"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_DIR="$HOME/claude-sources"
CLAUDE_DIR="$HOME/.claude"
LOG_DIR="${SCRIPT_DIR}/update-logs"
declare -a ERRORS=()
SYNC_RESULT=""
ORIGIN_DIR="$PWD"

# ============================================================
# 日志：同时输出到 stderr 和按天命名的 log 文件
# 只保留最近 3 个 log 文件
# ============================================================
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/$(date '+%Y-%m-%d').log"

log() {
    local msg="[$(date '+%Y-%m-%d %H:%M:%S')] $1"
    echo "$msg" >&2
    echo "$msg" >> "$LOG_FILE"
}
ok()   { log "✓ $1"; }
warn() { log "✗ $1"; ERRORS+=("$1"); }

# 清理旧 log，只保留最新 3 个
# macOS 的 ls -t 与 Linux 一致，tail -n +4 也兼容
cleanup_logs() {
    local count
    count=$(ls -1 "$LOG_DIR"/*.log 2>/dev/null | wc -l | tr -d ' ')
    if [ "$count" -gt 3 ]; then
        ls -1t "$LOG_DIR"/*.log | tail -n +4 | while IFS= read -r f; do
            rm -f "$f"
        done
    fi
}

# ============================================================
# sync_repo
#   结果写入全局 SYNC_RESULT（UPDATED / NO_UPDATE / FAILED）
#   cd 操作限制在子 shell，不影响调用方 PWD
# ============================================================
sync_repo() {
    local name=$1 url=$2
    local dir="$REPO_DIR/$name"
    SYNC_RESULT="NO_UPDATE"

    if [ ! -d "$dir" ]; then
        log "首次 clone $name ..."
        if git clone --depth=1 "$url" "$dir" >/dev/null 2>&1; then
            ok "$name clone 完成"
            SYNC_RESULT="UPDATED"
            return 0
        else
            warn "$name clone 失败"
            SYNC_RESULT="FAILED"
            return 0
        fi
    fi

    local result
    result=$(
        cd "$dir" 2>/dev/null || { echo "CD_FAIL"; exit 0; }

        git fetch origin --depth=1 --quiet 2>/dev/null || { echo "FETCH_FAIL"; exit 0; }

        local local_ref remote_ref
        local_ref=$(git rev-parse HEAD 2>/dev/null || echo "")
        remote_ref=$(git rev-parse origin/main 2>/dev/null \
                  || git rev-parse origin/master 2>/dev/null \
                  || echo "")

        [ -z "$remote_ref" ] && { echo "REF_FAIL"; exit 0; }
        [ "$local_ref" = "$remote_ref" ] && { echo "NO_UPDATE"; exit 0; }

        git checkout --quiet --detach "$remote_ref" 2>/dev/null \
            && echo "UPDATED" \
            || echo "RESET_FAIL"
    )

    case "$result" in
        UPDATED)    ok "$name 更新完成";           SYNC_RESULT="UPDATED" ;;
        NO_UPDATE)  log "$name 已是最新，跳过";    SYNC_RESULT="NO_UPDATE" ;;
        CD_FAIL)    warn "$name 目录无法进入";     SYNC_RESULT="FAILED" ;;
        FETCH_FAIL) warn "$name fetch 失败";       SYNC_RESULT="FAILED" ;;
        REF_FAIL)   warn "$name 无法获取远程版本"; SYNC_RESULT="FAILED" ;;
        RESET_FAIL) warn "$name checkout 失败";    SYNC_RESULT="FAILED" ;;
        *)          warn "$name 未知状态: $result"; SYNC_RESULT="FAILED" ;;
    esac
    return 0
}

# install_skill: 按候选路径依次尝试，找到第一个存在的目录即安装
install_skill() {
    local skill_name=$1; shift
    for candidate in "$@"; do
        if [ -d "$candidate" ]; then
            rm -rf "${CLAUDE_DIR}/skills/${skill_name}"
            cp -r "$candidate" "${CLAUDE_DIR}/skills/${skill_name}"
            ok "skill: $skill_name"
            return 0
        fi
    done
    warn "未找到 skill: $skill_name"
    return 1
}

# install_agent: 安装单个 agent .md 文件
install_agent() {
    local src=$1
    if [ -f "$src" ]; then
        cp "$src" "${CLAUDE_DIR}/agents/"
        ok "agent: $(basename "$src")"
    else
        warn "未找到 agent: $(basename "$src")"
    fi
}

# copy_dir_contents: 安全复制目录内容（避免 glob 空展开问题）
copy_dir_contents() {
    local src=$1 dst=$2 label=$3
    if [ ! -d "$src" ]; then
        warn "$label 源目录不存在: $src"
        return 1
    fi
    if [ -z "$(ls -A "$src" 2>/dev/null)" ]; then
        warn "$label 源目录为空: $src"
        return 1
    fi
    find "$src" -maxdepth 1 -mindepth 1 -exec cp -r {} "$dst/" \; 2>/dev/null \
        && ok "$label" \
        || warn "$label 复制失败"
}

# ============================================================
# 初始化目录
# ============================================================
mkdir -p \
    "$REPO_DIR" \
    "${CLAUDE_DIR}/agents" \
    "${CLAUDE_DIR}/skills" \
    "${CLAUDE_DIR}/commands"

log "========================================================"
log "开始执行 update.sh v13-mac"
log "========================================================"

# ============================================================
# 0/5 更新 Claude CLI 本身
# ============================================================
log "======== 0/5 更新 Claude CLI ========"
if command -v claude >/dev/null 2>&1; then
    if claude update --yes 2>/dev/null; then
        ok "Claude CLI 已更新至最新版"
    else
        # fallback：通过 npm 更新
        if npm update -g @anthropic-ai/claude-code 2>/dev/null; then
            ok "Claude CLI 已通过 npm 更新至最新版"
        else
            warn "Claude CLI 更新失败，请手动执行：npm update -g @anthropic-ai/claude-code"
        fi
    fi
else
    warn "未找到 claude 命令，跳过更新（请先安装：npm install -g @anthropic-ai/claude-code）"
fi

# ============================================================
# 0.5/5 更新 Codex CLI
# ============================================================
log "======== 0.5/5 更新 Codex CLI ========"
if npm update -g @openai/codex 2>/dev/null; then
    ok "Codex CLI 已更新至最新版"
else
    warn "Codex CLI 更新失败，请手动执行：npm update -g @openai/codex"
fi

# ============================================================
# 1/5 everything-claude-code
# ============================================================
log "======== 1/5 everything-claude-code ========"
sync_repo "everything-claude-code" "https://github.com/affaan-m/everything-claude-code.git"
if [ "$SYNC_RESULT" = "UPDATED" ]; then
    ECC_DIR="$REPO_DIR/everything-claude-code"

    for agent in build-error-resolver database-reviewer security-reviewer; do
        install_agent "$ECC_DIR/agents/${agent}.md"
    done

    for skill in api-design postgres-patterns security-review; do
        install_skill "$skill" "$ECC_DIR/skills/$skill"
    done

    for cmd in build-fix update-docs verify; do
        if [ -f "$ECC_DIR/commands/${cmd}.md" ]; then
            cp "$ECC_DIR/commands/${cmd}.md" "${CLAUDE_DIR}/commands/"
            ok "command: $cmd"
        else
            warn "未找到 command: $cmd"
        fi
    done
fi

# ============================================================
# 2/5 superpowers
# ============================================================
log "======== 2/5 superpowers ========"
sync_repo "superpowers" "https://github.com/obra/superpowers.git"
if [ "$SYNC_RESULT" = "UPDATED" ]; then
    SP_DIR="$REPO_DIR/superpowers"
    for skill in systematic-debugging verification-before-completion; do
        install_skill "$skill" "$SP_DIR/skills/$skill"
    done
fi

# ============================================================
# 3/5 anthropics/claude-plugins-official
# ============================================================
log "======== 3/5 anthropics/claude-plugins-official ========"
sync_repo "anthropics-claude-plugins-official" "https://github.com/anthropics/claude-plugins-official.git"
if [ "$SYNC_RESULT" = "UPDATED" ]; then
    APO_DIR="$REPO_DIR/anthropics-claude-plugins-official"

    for plugin in \
        frontend-design \
        skill-creator \
        agent-sdk-dev \
        claude-code-setup \
        mcp-server-dev \
        php-lsp \
        plugin-dev \
        feature-dev
    do
        install_skill "$plugin" \
            "$APO_DIR/plugins/$plugin/skills/$plugin" \
            "$APO_DIR/plugins/$plugin"
    done

    install_skill "claude-md-improver" \
        "$APO_DIR/plugins/claude-md-management/skills/claude-md-improver" \
        "$APO_DIR/plugins/claude-md-management"

    CODE_REVIEW_DIR="$APO_DIR/plugins/code-review"
    if [ -d "$CODE_REVIEW_DIR" ]; then
        if [ -d "$CODE_REVIEW_DIR/agents" ]; then
            find "$CODE_REVIEW_DIR/agents" -maxdepth 1 -name "*.md" \
                -exec cp {} "${CLAUDE_DIR}/agents/" \; 2>/dev/null \
                && ok "code-review agents" \
                || warn "code-review agents 复制失败"
        fi
        if [ -f "$CODE_REVIEW_DIR/commands/code-review.md" ]; then
            cp "$CODE_REVIEW_DIR/commands/code-review.md" "${CLAUDE_DIR}/commands/"
            ok "command: /code-review"
        else
            warn "未找到 code-review command"
        fi
    else
        warn "未找到 code-review plugin"
        find "$APO_DIR/plugins" -maxdepth 1 -type d 2>/dev/null | sed 's/^/  /' >&2
    fi
fi

# ============================================================
# 4/5 nextlevelbuilder/ui-ux-pro-max-skill
# ============================================================
log "======== 4/5 ui-ux-pro-max-skill ========"
sync_repo "ui-ux-pro-max-skill" "https://github.com/nextlevelbuilder/ui-ux-pro-max-skill.git"
if [ "$SYNC_RESULT" = "UPDATED" ]; then
    UX_DIR="$REPO_DIR/ui-ux-pro-max-skill"
    UX_DEST="${CLAUDE_DIR}/skills/ui-ux-pro-max"
    UX_SRC="$UX_DIR/src/ui-ux-pro-max"
    UX_SKILL_MD="$UX_DIR/.claude/skills/ui-ux-pro-max/SKILL.md"

    if [ ! -d "$UX_SRC" ]; then
        warn "ui-ux-pro-max: 找不到 src/ui-ux-pro-max/"
    elif [ ! -f "$UX_SKILL_MD" ]; then
        warn "ui-ux-pro-max: 找不到 .claude/skills/ui-ux-pro-max/SKILL.md"
    else
        rm -rf "$UX_DEST"
        mkdir -p "$UX_DEST"
        copy_dir_contents "$UX_SRC" "$UX_DEST" "ui-ux-pro-max/src"
        cp "$UX_SKILL_MD" "$UX_DEST/SKILL.md" \
            && ok "ui-ux-pro-max/SKILL.md" \
            || warn "ui-ux-pro-max SKILL.md 复制失败"
    fi
fi

# ============================================================
# 5/5 jnMetaCode/agency-agents-zh
# ============================================================
log "======== 5/5 agency-agents-zh ========"
sync_repo "agency-agents-zh" "https://github.com/jnMetaCode/agency-agents-zh.git"
if [ "$SYNC_RESULT" = "UPDATED" ]; then
    AA_DIR="$REPO_DIR/agency-agents-zh"
    install_agent "$AA_DIR/engineering/engineering-wechat-mini-program-developer.md"
fi

# ============================================================
# 汇总
# ============================================================
cd "$ORIGIN_DIR" 2>/dev/null || true
log "========================================================"
log "======== 完成 ========"
log "Claude CLI 版本：$(claude --version 2>/dev/null || echo '未知')"
log "Codex CLI 版本：$(codex --version 2>/dev/null || echo '未知')"
log "skills  : $(ls "${CLAUDE_DIR}/skills/"   2>/dev/null | tr '\n' ' ')"
log "agents  : $(ls "${CLAUDE_DIR}/agents/"   2>/dev/null | tr '\n' ' ')"
log "commands: $(ls "${CLAUDE_DIR}/commands/" 2>/dev/null | tr '\n' ' ')"

if [ "${#ERRORS[*]}" -gt 0 ]; then
    log ""
    log "⚠️  以下项目需要手动检查："
    for err in "${ERRORS[@]}"; do
        log "  - $err"
    done
    cleanup_logs
    exit 1
fi

log ""
log "✅ 全部成功，无错误"
log "log 文件：$LOG_FILE"
cleanup_logs
exit 0
