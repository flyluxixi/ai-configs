# ai-configs

个人 AI 编程助手配置源库，统一维护 Claude Code 与 Codex 的全局入口、技术栈规则、agents / skills、踩坑知识库和更新 / 检查脚本。

本仓库是唯一源头，`~/.claude/` 和 `~/.codex/` 是同步目标，不作为手工维护目录。

## 定位

- 同时支持 Claude Code 与 Codex，两侧共用中立技术栈规则源
- 覆盖 Go + Gin、Vue 3、Nuxt 4、Flutter、微信小程序、Python、PostgreSQL、Redis、Nginx 等技术栈
- 通用规则（入口文件）、技术栈规则（`luxixi/`）、工具专用资产（agents / skills）分层维护

历史架构规划见 [docs/ai-assistant-config-architecture.md](docs/ai-assistant-config-architecture.md)（迁移期规划文档，当前实际状态以本文件和根 `CLAUDE.md` 为准）。

## 目录结构

```text
ai-configs/
├── CLAUDE.md                 # 本仓库给 Claude Code 使用的项目级入口
├── AGENTS.md                 # 本仓库给 Codex 使用的项目级入口
├── claude/
│   ├── CLAUDE.md             # Claude Code 全局入口，~/.claude/CLAUDE.md 已 symlink 到此
│   ├── rules/                # Claude Code rules 源（context7.md），~/.claude/rules 已 symlink 到此
│   ├── luxixi/               # Claude / Codex 共用的中立技术栈规则源（13 个技术栈）
│   ├── agents/               # Claude Code 专用 agents（当前无自建；php-expert 已废弃移除）
│   ├── skills/               # 所有 skill 的唯一源头（8 个 d-* skill）
│   ├── pitfall/              # 各技术栈踩坑知识库，由 d-pitfall skill 写入
│   └── settings.json         # ~/.claude/settings.json 的版本化快照（cp 双向同步）
├── codex/
│   ├── AGENTS.md             # Codex 全局入口，~/.codex/AGENTS.md 已 symlink 到此
│   ├── skills/               # Codex 适配版 skills（由 claude/skills 适配语法生成）
│   └── luxixi -> ../claude/luxixi
├── scripts/
│   ├── update.sh             # 每日：同步源（双向）+ 软链装配 + 更新 CLI / 第三方资产
│   └── check-sync.sh         # 源库 ↔ 本机 同步一致性检查
├── docs/
└── README.md
```

`claude/commands/` 预留，尚未落地。

## 同步机制

| 内容 | 机制 | 装配方 |
| --- | --- | --- |
| `claude/CLAUDE.md` → `~/.claude/CLAUDE.md` | symlink | update.sh 步骤 B 自动建 / 校验 |
| `claude/rules/` → `~/.claude/rules` | symlink | update.sh 步骤 B 自动建 / 校验 |
| `claude/luxixi/` → `~/.claude/luxixi` | symlink | update.sh 步骤 B 自动建 / 校验 |
| `claude/skills/d-*` → `~/.claude/skills/d-*` | symlink | update.sh 步骤 B 自动建 / 校验（8 个自建 skill） |
| `codex/AGENTS.md` → `~/.codex/AGENTS.md`、`codex/luxixi` | symlink | 手工建立（Codex 侧，不在 update.sh 内） |
| 第三方 skills / agents / commands | cp | update.sh 步骤 1-5 从各 GitHub 源拉取后 cp 到 `~/.claude/` |
| `claude/settings.json` | cp 双向 | 本机被 CLI 改写后合并回仓库；从仓库恢复时反向 cp |

- 自建项（CLAUDE.md / rules / luxixi / d-* skill）由 update.sh 步骤 B 幂等装配为软链，源改即时生效，无需手工 cp；第三方项才走 cp
- skill 的唯一源头是 `claude/skills/*/SKILL.md`；`codex/skills/` 是适配产物（去 `@path`、改显式读取指令），不单独维护内容
- 同步完成后运行 `bash scripts/check-sync.sh` 验证一致性

## 资产清单

- agents：当前无自建 agent（`php-expert` 已废弃移除，2026-07-23）
- skills（8 个）：`d-ask`（需求追问）、`d-step`（原子拆解执行）、`d-review`（审查 + 提交 + 部署，仅 Claude Code）、`d-stop`（会话收尾）、`d-pitfall`（记坑）、`d-decision`（设计决策固化）、`d-nginx`（Nginx 专家）、`d-prompt`（生图提示词优化）
- codex/skills：除 `d-review` 外的 7 个适配版

## update.sh 职责（v16）

`scripts/update.sh` 每日通过 crontab 执行，是「源 → 运行时」的闭环装配器：

- **A 同步源（双向对等）**：`git fetch` 后按状态决策——干净且落后远端则 fast-forward 拉取；有未提交改动 / 本地领先 / 两端分叉则只告警，提示手动 `commit + push`（绝不自动 push，避免推半成品到另一端）
- **B 装配自建软链**：把 `claude/CLAUDE.md`、`rules/`、`luxixi/`、`skills/d-*` 软链到 `~/.claude/`（幂等，仅白名单，不触碰第三方拷贝）
- **0 更新 CLI**：Claude（native 后台自更 / npm 走 `npm install -g @latest`）+ Codex（`codex update`）
- **1-5 拉第三方**：从各 GitHub 源增量拉取 agents / skills / commands 并 cp 到 `~/.claude/`

### 两台运行时

| 机器 | 角色 | 与本仓库关系 |
| --- | --- | --- |
| mac | 对等写入端（主开发） | 编辑本仓库并 push；`~/.claude/` 自建项软链到本仓库 |
| topnew2 | 对等写入端（移动开发） | 编辑本仓库并 push；每日 update.sh 步骤 A fetch 后 ff-pull / 告警，装配软链 |

**双向对等，GitHub 仓库是唯一真相源**：两台都可改，任一端改完自建配置都要手动 `commit + push`；另一端下次 update.sh 步骤 A `git fetch` 后自动 fast-forward 拉取（干净且落后时）或告警（dirty / 本地领先 / 两端分叉）。脚本**绝不自动 push**——谁改谁手动推，否则两台漂移。随时 `bash scripts/check-sync.sh` 看 `0/5 git 同步状态` 段确认与远端是否一致（topnew2 无公网，经 topnew1 ProxyJump 接入）。

## 维护原则

- 长期规则源头只在本仓库：两侧入口文件、`claude/luxixi/*.md`、`claude/skills/*/SKILL.md`、`claude/agents/*.md`、`claude/rules/*.md`
- `~/.claude/` 和 `~/.codex/` 不作为规则源头
- 全局入口保持薄，不绑定单一技术栈；技术栈规则放 `luxixi/`
- Claude 与 Codex skills 内容相近，但路径引用和工具语法必须分别适配（Codex 不支持 `@path` 自动展开）
- 双向对等：mac 与 topnew2 任一端改完都要按用户指令 `commit + push` 到 `git@github.com:flyluxixi/ai-configs.git`；另一端 update.sh 步骤 A 自动 ff-pull 或告警，脚本绝不自动 push
