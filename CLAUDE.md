# Project Profile

本项目是个人 AI 编程助手配置源库，用于维护 Claude Code 与 Codex 的全局入口、技术栈规则、Claude 专用 agents / skills 和同步脚本。

`~/.claude/` 与 `~/.codex/` 是同步目标，不作为手工维护源头。所有长期规则先改本仓库，再按用户要求同步。

## 目录职责

- `claude/CLAUDE.md`：Claude Code 全局入口源文件，同步目标为 `~/.claude/CLAUDE.md`
- `codex/AGENTS.md`：Codex 全局入口源文件，同步目标为 `~/.codex/AGENTS.md`
- `~/.claude/RTK.md` 与 `~/.codex/RTK.md`：本机 RTK 工具规则文件，均真实存在；入口文件引用时使用 `@~`，不要硬编码用户名路径
- `claude/luxixi/`：Claude / Codex 共用的中立技术栈规则源
- `codex/luxixi`：指向 `../claude/luxixi` 的 symlink，不维护第二份规则
- `claude/agents/`、`claude/skills/`、`claude/commands/`：Claude Code 专用资产，不要求与 Codex skills 保持一致
- `scripts/update.sh`：Claude Code 生态更新脚本，只负责更新 Claude CLI 和第三方 Claude agents / skills / commands
- `docs/`：架构规划和维护说明

## 维护规则

- 修改 `claude/CLAUDE.md`、`codex/AGENTS.md` 或 `claude/luxixi/` 后，先提交源库；是否同步到 `~/.claude/` / `~/.codex/` 由用户明确决定
- 不要把 `scripts/update.sh` 扩展成 Codex 同步脚本；Codex 同步应由独立 `sync-codex.sh` 负责
- 不要在 `codex/luxixi` 下直接写文件；应修改 `claude/luxixi/`
- 不要把 Claude Code 专用 frontmatter、agent、skill 格式写进 `claude/luxixi/` 中立规则源
- 技术栈规则文件应只写对应技术栈内的约束，跨技术栈规则应拆到独立文件
- `PROJECT_STATUS.md` 是本地会话状态文件，不提交

## 文档清单

- `README.md`：仓库定位、目录规划、维护原则
- `docs/ai-assistant-config-architecture.md`：Claude Code / Codex 共用配置源架构规划
- `webman-packages-reference.md`：Webman 常用依赖备忘

## Git

仓库远程地址：`git@github.com:flyluxixi/ai-configs.git`

提交前检查 `git status`，确认没有 `.DS_Store`、`PROJECT_STATUS.md` 或无关文件进入暂存区。
