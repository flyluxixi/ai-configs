# Project Profile

本项目是个人 AI 编程助手配置源库，用于维护 Claude Code 与 Codex 的全局入口、技术栈规则、agents / skills 和同步脚本。

`~/.claude/` 与 `~/.codex/` 是同步目标，不作为手工维护源头。所有长期规则先改本仓库，再按用户要求同步。

先读项目 `README.md`、`CLAUDE.md`、`AGENTS.md`、`PROJECT_STATUS.md` 和相关文档。

## 目录职责

- `claude/CLAUDE.md`：Claude Code 全局入口源文件，`~/.claude/CLAUDE.md` 已 symlink 到此，修改后无需手动同步
- `codex/AGENTS.md`：Codex 全局入口源文件，`~/.codex/AGENTS.md` 已 symlink 到此，修改后无需手动同步
- `claude/luxixi/`：Claude / Codex 共用的中立技术栈规则源
- `codex/luxixi`：指向 `../claude/luxixi` 的 symlink，不维护第二份规则
- `claude/rules/`：Claude Code rules 规则源（当前含 `context7.md`），`~/.claude/rules` 已 symlink 到此，修改后无需手动同步
- `claude/skills/`：所有 skill 的唯一源头；自建 `d-*` 由 update.sh 步骤 B 软链装配到 `~/.claude/skills/`，改源即时生效（无需 cp）
- `claude/agents/`：Claude Code 专用 agents，以本仓库为源头，修改后 cp 到 `~/.claude/agents/`（当前无自建 agent，`claude/commands/` 预留未落地）
- `claude/pitfall/`：各技术栈踩坑记录数据目录，由 pitfall skill 写入，进版本控制
- `claude/settings.json`：Claude Code 全局 settings 的版本化快照（permissions、enabledPlugins、effortLevel、theme 等通用可移植配置），进版本控制；与本机 `~/.claude/settings.json` 通过 cp 双向同步，不做 symlink（settings.json 会被 CLI 动态写入，symlink 易被原子写替换而漂移）。机器私有项放本机 `~/.claude/settings.local.json`，不进本仓
- `codex/skills/`：Codex 专用 skills，启用时同步到 `~/.codex/skills/`（codex 侧当前仍手工，未纳入 update.sh）
- `scripts/update.sh`（v16）：每日更新脚本，四项职责——**A** 同步 ai-configs 源（fetch 后 ff-pull 或告警，双向对等、绝不自动 push）；**B** 幂等软链装配 claude 侧自建项（`CLAUDE.md`/`rules`/`luxixi`/`skills/d-*`）到 `~/.claude/`；**0** 更新 Claude / Codex CLI 本身；**1-5** 拉第三方 agents / skills / commands 并 cp 到 `~/.claude/`。codex 侧暂不纳入自动装配
- `scripts/check-sync.sh`：同步一致性检查——先核对本机 ↔ 远端 git 状态（dirty/ahead/behind，判断两台是否漂移），再核对 symlink 指向与 skills / agents / settings 内容；怀疑漂移时先运行它
- `docs/`：架构规划和维护说明

## 维护规则

- 长期维护源头：`claude/CLAUDE.md`、`codex/AGENTS.md`、`claude/luxixi/*.md`、`claude/skills/*/SKILL.md`、`claude/agents/*.md`、`claude/rules/*.md`
- `claude/CLAUDE.md` 与 `codex/AGENTS.md` 已 symlink，修改后无需额外操作
- `~/.claude/luxixi` 与 `~/.codex/luxixi` 已 symlink 到 `claude/luxixi`，修改 `claude/luxixi/*.md` 后无需同步
- `~/.claude/rules` 已 symlink 到 `claude/rules`，修改 `claude/rules/*.md` 后无需同步
- `claude/skills/*/SKILL.md` 是所有 skill 的唯一源头，不单独修改 `codex/skills/`
- 自建 `d-*` skill 已由 update.sh 步骤 B 软链装配到 `~/.claude/skills/`，改 `claude/skills/<skill>/` 后即时生效、无需 cp（仅第三方 skill 走 cp）；若 `codex/skills/<skill>/` 存在，适配 Codex 语法后 cp 到 `~/.codex/skills/<skill>/`（codex 侧仍手工）
- 修改 `claude/agents/<agent>.md` 后：cp 到 `~/.claude/agents/`
- 修改 `claude/CLAUDE.md` 或 `codex/AGENTS.md` 的通用规则时，同步评估另一侧是否需要同条更新，保持双侧入口对等
- 完成任何 cp 同步或本机配置修改后，运行 `bash scripts/check-sync.sh` 验证源库与本机一致
- 全局 settings 由 CLI 在本机侧驱动（`/config`、`/model`、`/fast` 等会写 `~/.claude/settings.json`）：本机改动后 cp 到 `claude/settings.json` 再提交；从仓库恢复时反向 cp 回 `~/.claude/settings.json`。机器私有项（本地覆盖）只写 `~/.claude/settings.local.json`，不进仓
- 不要直接修改 `~/.claude/luxixi`、`~/.codex/luxixi` 或 `codex/luxixi`
- **双向同步（核心）**：mac 与 topnew2 是对等写入端，任一端改完都要 `commit + push`；另一端下次 update.sh 步骤 A 会 fetch 后 ff-pull（干净且落后时）或告警（dirty / 本地领先 / 分叉）。脚本绝不自动 push——谁改谁手动推，否则两台漂移；随时 `bash scripts/check-sync.sh` 看 `0/5 git 同步状态` 段确认是否与远端一致
- update.sh 目前只自动装配 claude 侧（步骤 B）；codex 侧（`~/.codex/`）装配暂缓，不要擅自把 update.sh 扩展到 codex
- 不要把 Claude Code 或 Codex 专用 frontmatter、agent、skill 格式写进 `claude/luxixi/` 中立规则源
- Codex skills 中不能使用 `@path` 语法（Codex 不自动展开），需改为显式读取指令，例如：`首先读取 ~/.codex/luxixi/nginx.md`；Claude Code 的 `@path` 会在加载时自动展开
- 技术栈规则文件应只写对应技术栈内的约束，跨技术栈规则应拆到独立文件
- `PROJECT_STATUS.md` 是本地会话状态文件，不提交
- `AGENTS.md` 中引用文件需要使用绝对路径，`CLAUDE.md` 可以使用相对路径
- 修改根 `CLAUDE.md` 的目录职责或维护规则时，同步更新根 `AGENTS.md` 保持内容对齐

## 文档清单

- `README.md`：仓库定位、目录规划、维护原则
- `docs/ai-assistant-config-architecture.md`：Claude Code / Codex 共用配置源架构规划（迁移期规划文档，现状以 README 为准）

## Git

仓库远程地址：`git@github.com:flyluxixi/ai-configs.git`

代码审查、会话收尾和 `PROJECT_STATUS.md` 更新不构成默认提交授权；除非用户明确要求，否则不主动执行 `git commit` 或 `git push`。

提交前检查 `git status`，确认没有 `.DS_Store`、`PROJECT_STATUS.md` 或无关文件进入暂存区。
