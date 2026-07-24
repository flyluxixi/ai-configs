#!/bin/bash

# ============================================================
# AI 工具配置自动更新脚本 v16
#
# 更新内容：
#   A. 同步 ai-configs 源（single source of truth，双向对等）：fetch 后按状态决策——干净且落后则 ff-pull；有未提交/本地领先/分叉则只告警（绝不自动 push）
#   B. 装配自建配置软链：CLAUDE.md / rules / luxixi / d-* skills → 软链到 ai-configs 源
#   0. CLI 本身：Claude（native→后台自更新跳过 / npm→npm install 更新）+ Codex（codex update）
#   1. everything-claude-code          — agents / skills / commands
#   2. superpowers                     — systematic-debugging / verification-before-completion
#   3. anthropics/claude-plugins-official — frontend-design / code-review /
#                                           skill-creator / claude-md-management
#   4. nextlevelbuilder/ui-ux-pro-max-skill — ui-ux-pro-max skill
#   5. jnMetaCode/agency-agents-zh     — engineering-wechat-mini-program-developer agent
#
# 用法：
#   手动执行：bash ~/projects/ai-configs/scripts/update.sh
#   cron（日志按天写入 scripts/update-logs/）：
#   0 10 * * * bash ~/projects/ai-configs/scripts/update.sh
#
# 平台 / 安装方式说明（一份脚本，Mac 与服务器 git 同步后各走各的分支）：
#   - Mac 本机：claude 为 native 安装（~/.local/bin/claude → ~/.local/share/claude/versions/），自带后台 auto-updater
#   - 服务器（如 topnew2）：claude 为 npm 全局安装；downloads.claude.ai 不可达导致后台/`claude update` 更新失败，
#     故脚本按安装方式自适应：native 跳过、npm 走 `npm install -g @anthropic-ai/claude-code@latest`
#   - PATH 已覆盖 Homebrew、~/.local/bin、npm global；Linux 上 Homebrew 路径不存在会被忽略，无害
#   - cron 在 macOS 上需要授予"完全磁盘访问"权限给 /usr/sbin/cron（系统设置 → 隐私与安全性 → 完全磁盘访问）
# ============================================================

set -uo pipefail

# macOS: 加入 Homebrew 路径（Apple Silicon: /opt/homebrew/bin，Intel: /usr/local/bin）
export PATH="/opt/homebrew/bin:/opt/homebrew/sbin:$HOME/.local/bin:$HOME/.npm-global/bin:/usr/local/bin:/usr/bin:/bin:$PATH"

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

# link_selfbuilt: 把自建项软链到 ai-configs 源（幂等、安全）
#   $1 源路径  $2 目标路径  $3 标签
#   - 源不存在：warn 返回
#   - 目标已是指向源的正确软链：跳过（幂等）
#   - 目标是真实文件/目录或错误软链：移除后重建
#     （rm 不带尾斜杠：对 symlink 只删链接不跟随，对真实目录删目录本身；仅白名单调用）
link_selfbuilt() {
    local src=$1 dst=$2 label=$3
    if [ ! -e "$src" ]; then
        warn "自建项源不存在，跳过 $label: $src"
        return 1
    fi
    if [ -L "$dst" ] && [ "$(readlink "$dst")" = "$src" ]; then
        ok "$label 软链已就绪"
        return 0
    fi
    rm -rf "$dst"
    if ln -s "$src" "$dst"; then
        ok "$label 软链已建 → $src"
    else
        warn "$label 软链创建失败"
    fi
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
log "开始执行 update.sh v16"
log "========================================================"

# ============================================================
# A 同步 ai-configs 源（single source of truth，双向对等）
#   两台机器（mac / topnew2）都是对等写入端，任一端可改；GitHub 仓库是唯一真相源。
#   fetch 后按状态决策，绝不自动 commit/push（避免把半成品/临时文件推上去）：
#     · 干净且落后远端         → fast-forward 拉取（纯消费端的正常路径）
#     · 有未提交改动 / 本地领先  → 只告警，提示手动 commit + push 同步到另一端
#     · 两端都有新提交（已分叉） → 只告警，需手动合并
#   脚本自身位于该仓库内，ff 更新脚本对当前运行无影响（下次运行生效）
# ============================================================
log "======== A 同步 ai-configs 源 ========"

AI_CONFIGS_DIR="$HOME/projects/ai-configs"
if [ ! -d "$AI_CONFIGS_DIR/.git" ]; then
    warn "ai-configs 不是 git 仓库: ${AI_CONFIGS_DIR}（自建配置无法自更新）"
elif ! git -C "$AI_CONFIGS_DIR" fetch --quiet 2>/dev/null; then
    warn "ai-configs git fetch 失败（网络或权限），跳过本次同步检查"
else
    ac_upstream=$(git -C "$AI_CONFIGS_DIR" rev-parse --abbrev-ref '@{u}' 2>/dev/null)
    if [ -z "$ac_upstream" ]; then
        warn "ai-configs 当前分支未设置 upstream，无法判断同步状态"
    else
        ac_dirty=""
        [ -n "$(git -C "$AI_CONFIGS_DIR" status --porcelain 2>/dev/null)" ] && ac_dirty=1
        ac_ahead=$(git -C "$AI_CONFIGS_DIR" rev-list --count '@{u}..HEAD' 2>/dev/null)
        ac_behind=$(git -C "$AI_CONFIGS_DIR" rev-list --count 'HEAD..@{u}' 2>/dev/null)
        ac_ahead=${ac_ahead:-0}
        ac_behind=${ac_behind:-0}

        if [ -n "$ac_dirty" ]; then
            warn "⚠ ai-configs 有未提交改动（本地领先 ${ac_ahead} / 落后 ${ac_behind}）——请先 commit + push 同步到另一端；已跳过 pull 避免覆盖本地改动"
        elif [ "$ac_ahead" -gt 0 ] && [ "$ac_behind" -gt 0 ]; then
            warn "⚠ ai-configs 两端已分叉（本地 $ac_ahead / 远端 $ac_behind 各有新提交）——需手动合并，脚本不自动处理"
        elif [ "$ac_ahead" -gt 0 ]; then
            warn "⚠ ai-configs 本地领先远端 $ac_ahead 个提交未推送——请 git push，否则另一端拿不到（双边会漂移）"
        elif [ "$ac_behind" -gt 0 ]; then
            if git -C "$AI_CONFIGS_DIR" merge --ff-only --quiet '@{u}' 2>/dev/null; then
                ok "ai-configs 源已更新（fast-forward 拉取 $ac_behind 个提交）"
            else
                warn "ai-configs fast-forward 失败，请手动检查（可能有冲突）"
            fi
        else
            ok "ai-configs 已与远端一致（无新提交）"
        fi
    fi
fi

# ============================================================
# B 装配自建配置（软链到 ai-configs 源）
#   仅处理自建项白名单，绝不触碰第三方拷贝（步骤 1-5 负责）
#   幂等：已是指向源的正确软链则跳过；真实文件/目录或错误软链则重建
#   （mac 历史遗留的 d-* 真实拷贝已核实与源逐字节一致，转软链无损，
#    顺带修复「源更新拷贝不同步」的断裂）
# ============================================================
log "======== B 装配自建配置软链 ========"

AI_CONFIGS_CLAUDE="$AI_CONFIGS_DIR/claude"
if [ ! -d "$AI_CONFIGS_CLAUDE" ]; then
    warn "ai-configs 源目录不存在: ${AI_CONFIGS_CLAUDE}，跳过自建项装配"
else
    link_selfbuilt "$AI_CONFIGS_CLAUDE/CLAUDE.md" "$CLAUDE_DIR/CLAUDE.md" "CLAUDE.md"
    link_selfbuilt "$AI_CONFIGS_CLAUDE/rules"     "$CLAUDE_DIR/rules"     "rules/"
    link_selfbuilt "$AI_CONFIGS_CLAUDE/luxixi"    "$CLAUDE_DIR/luxixi"    "luxixi/"
    for s in d-ask d-decision d-nginx d-pitfall d-prompt d-review d-step d-stop; do
        link_selfbuilt "$AI_CONFIGS_CLAUDE/skills/$s" "$CLAUDE_DIR/skills/$s" "skill: $s"
    done
fi

# ============================================================
# 0/5 更新 CLI 本身（Claude + Codex）
#   Claude 按安装方式自适应：
#     · native 安装（Mac，~/.local/share/claude/versions/ 存在）：自带后台 auto-updater，脚本跳过
#     · npm 全局安装（服务器）：downloads.claude.ai 不可达使后台更新失败，改走 npm registry
#       官方要求用 `npm install -g @anthropic-ai/claude-code@latest`，勿用 `npm update -g`（受原始 semver 约束不一定到最新）
#   Codex 用官方 `codex update`：按安装方式（npm / standalone）自动选更新方式
# ============================================================
log "======== 0/5 更新 CLI 本身 ========"

# --- Claude ---
if [ -d "$HOME/.local/share/claude/versions" ]; then
    ok "Claude 为 native 安装，由自带后台 auto-updater 更新，脚本跳过"
elif command -v npm >/dev/null 2>&1 && npm ls -g @anthropic-ai/claude-code >/dev/null 2>&1; then
    log "检测到 npm 全局安装的 Claude，执行 npm 更新..."
    if npm install -g @anthropic-ai/claude-code@latest >/dev/null 2>&1; then
        ok "Claude CLI 已更新至最新版（npm）"
    else
        warn "Claude CLI npm 更新失败，请手动执行：npm install -g @anthropic-ai/claude-code@latest"
    fi
else
    warn "未识别 Claude 安装方式，跳过 Claude 更新"
fi

# --- Codex ---
if command -v codex >/dev/null 2>&1; then
    if codex update 2>/dev/null; then
        ok "Codex CLI 已更新至最新版"
    else
        warn "Codex CLI 更新失败，请手动执行：codex update"
    fi
else
    warn "未找到 codex 命令，跳过更新（请先安装：npm install -g @openai/codex）"
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

    for skill in api-design security-review; do
        install_skill "$skill" "$ECC_DIR/skills/$skill"
    done

    for cmd in build-fix update-docs; do
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
        skill-creator
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
