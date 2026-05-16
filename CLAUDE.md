# Project Profile

本项目是个人 AI 编程助手配置源库，用于维护 Claude Code 与 Codex 的全局入口、技术栈规则、agents / skills 和同步脚本。

`~/.claude/` 与 `~/.codex/` 是同步目标，不作为手工维护源头。所有长期规则先改本仓库，再按用户要求同步。

先读项目 `README.md`、`CLAUDE.md`、`AGENTS.md`、`PROJECT_STATUS.md` 和相关文档。

## 目录职责

- `claude/CLAUDE.md`：Claude Code 全局入口源文件，`~/.claude/CLAUDE.md` 已 symlink 到此，修改后无需手动同步
- `codex/AGENTS.md`：Codex 全局入口源文件，`~/.codex/AGENTS.md` 已 symlink 到此，修改后无需手动同步
- `~/.claude/RTK.md` 与 `~/.codex/RTK.md`：本机 RTK 工具规则文件，均真实存在；入口文件引用时使用 `@~`，不要硬编码用户名路径
- `claude/luxixi/`：Claude / Codex 共用的中立技术栈规则源
- `codex/luxixi`：指向 `../claude/luxixi` 的 symlink，不维护第二份规则
- `claude/agents/`、`claude/skills/`、`claude/commands/`：Claude Code 专用资产
- `claude/pitfall/`：各技术栈踩坑记录数据目录，由 pitfall skill 写入，进版本控制
- `codex/skills/`：Codex 专用 skills，启用时同步到 `~/.codex/skills/`
- `scripts/update.sh`：Claude Code 生态更新脚本，只负责更新 Claude CLI 和第三方 Claude agents / skills / commands
- `docs/`：架构规划和维护说明

## 维护规则

- 长期维护源头：`claude/CLAUDE.md`、`codex/AGENTS.md`、`claude/luxixi/*.md`、`claude/skills/*/SKILL.md`
- `claude/CLAUDE.md` 与 `codex/AGENTS.md` 已 symlink，修改后无需额外操作
- `~/.claude/luxixi` 与 `~/.codex/luxixi` 已 symlink 到 `claude/luxixi`，修改 `claude/luxixi/*.md` 后无需同步
- `claude/skills/*/SKILL.md` 是所有 skill 的唯一源头，不单独修改 `codex/skills/`
- 修改 `claude/skills/<skill>/SKILL.md` 后：cp 到 `~/.claude/skills/<skill>/`；若 `codex/skills/<skill>/` 存在，适配 Codex 语法同步后 cp 到 `~/.codex/skills/<skill>/`
- 不要直接修改 `~/.claude/luxixi`、`~/.codex/luxixi` 或 `codex/luxixi`
- 不要把 `scripts/update.sh` 扩展成 Codex 同步脚本
- 不要把 Claude Code 或 Codex 专用 frontmatter、agent、skill 格式写进 `claude/luxixi/` 中立规则源
- Codex skills 中不能使用 `@path` 语法（Codex 不自动展开），需改为显式读取指令，例如：`首先读取 ~/.codex/luxixi/nginx.md`；Claude Code 的 `@path` 会在加载时自动展开
- 技术栈规则文件应只写对应技术栈内的约束，跨技术栈规则应拆到独立文件
- `PROJECT_STATUS.md` 是本地会话状态文件，不提交
- `AGENTS.md` 中引用文件需要使用绝对路径，`CLAUDE.md` 可以使用相对路径

## 文档清单

- `README.md`：仓库定位、目录规划、维护原则
- `docs/ai-assistant-config-architecture.md`：Claude Code / Codex 共用配置源架构规划

## Git

仓库远程地址：`git@github.com:flyluxixi/ai-configs.git`

代码审查、会话收尾和 `PROJECT_STATUS.md` 更新不构成默认提交授权；除非用户明确要求，否则不主动执行 `git commit` 或 `git push`。

提交前检查 `git status`，确认没有 `.DS_Store`、`PROJECT_STATUS.md` 或无关文件进入暂存区。
