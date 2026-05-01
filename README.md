# ai-configs

个人 AI 编程助手配置源库，用于统一维护 Claude Code 与 Codex 的长期规则、技术栈约定、agents、skills 和同步脚本。

本仓库是源头，`~/.claude/` 和 `~/.codex/` 是同步目标，不作为手工维护目录。

## 当前定位

本项目原本是 Claude Code + PHP/Webman 的个人配置仓库，现在正在升级为：

- 同时支持 Claude Code 与 Codex
- 同时覆盖 PHP Webman、Go Gin、Nuxt 3、Flutter、微信小程序、PostgreSQL、Redis、Nginx 等技术栈
- 将通用规则、技术栈规则、工具适配层拆开维护
- 保留 Claude Code 专用 agents / skills，同时为 Codex 提供独立入口

详细规划见 [docs/ai-assistant-config-architecture.md](docs/ai-assistant-config-architecture.md)。

## 目录规划

目标结构：

```text
ai-configs/
├── CLAUDE.md                 # 本仓库给 Claude Code 使用的项目级入口
├── AGENTS.md                 # 本仓库给 Codex 使用的项目级入口
├── claude/
│   ├── CLAUDE.md             # 同步到 ~/.claude/CLAUDE.md
│   ├── rules/                # 同步到 ~/.claude/rules/
│   ├── luxixi/               # Claude / Codex 共用的中立规则源
│   │   ├── go.md
│   │   ├── php-webman.md
│   │   ├── nuxt3.md
│   │   ├── flutter.md
│   │   ├── miniprogram.md
│   │   ├── postgresql.md
│   │   ├── redis.md
│   │   └── nginx.md
│   ├── agents/               # Claude Code 专用 agents
│   ├── skills/               # Claude Code 专用 skills
│   └── commands/             # Claude Code 专用 commands
├── codex/
│   ├── AGENTS.md             # 同步到 ~/.codex/AGENTS.md
│   └── luxixi -> ../claude/luxixi
├── scripts/
│   ├── update.sh             # Claude Code 生态更新脚本
│   ├── sync-claude.sh        # 同步配置到 ~/.claude/
│   ├── sync-codex.sh         # 同步配置到 ~/.codex/
│   └── sync-all.sh           # 同步两边
├── docs/
└── README.md
```

当前仓库仍处于迁移阶段，部分目标目录和同步脚本尚未落地。

## 规则分层

### Claude / Codex 入口

- `claude/CLAUDE.md`：Claude Code 全局入口，最终同步到 `~/.claude/CLAUDE.md`
- `codex/AGENTS.md`：Codex 全局入口，最终同步到 `~/.codex/AGENTS.md`
- 根目录 `CLAUDE.md` / `AGENTS.md`：本仓库自身的项目级入口，不同步到全局目录

入口文件只放所有项目都成立的规则，例如：

- 回复语言和沟通方式
- 使用 `rtk` 执行 shell 命令
- 先读项目 README / CLAUDE.md / AGENTS.md
- 项目级规则优先
- 不覆盖用户未授权改动
- Git、文档、安全底线等通用要求

技术栈专项规则不直接堆进全局入口。

### 中立规则源

`claude/luxixi/` 是 Claude Code 与 Codex 共用的中立规则源，后续计划维护：

- `go.md`
- `php-webman.md`
- `nuxt3.md`
- `flutter.md`
- `miniprogram.md`
- `postgresql.md`
- `redis.md`
- `nginx.md`

`codex/luxixi` 应作为 symlink 指向 `../claude/luxixi`，保证中立规则只维护一份。

在本机 macOS 环境中，`~/.claude/luxixi` 和 `~/.codex/luxixi` 已直接 symlink 到源库：

```bash
ln -sfn ~/projects/ai-configs/claude/luxixi ~/.claude/luxixi
ln -sfn ~/projects/ai-configs/claude/luxixi ~/.codex/luxixi
```

因此修改 `claude/luxixi/*.md` 后无需同步，Claude Code 与 Codex 会通过 symlink 直接读取最新内容。

### 长期维护源头

长期维护源头只有：

- `claude/CLAUDE.md`
- `codex/AGENTS.md`
- `claude/luxixi/*.md`

同步规则：

- 修改 `claude/CLAUDE.md` 后，手动同步到 `~/.claude/CLAUDE.md`
- 修改 `codex/AGENTS.md` 后，手动同步到 `~/.codex/AGENTS.md`
- 修改 `claude/luxixi/*.md` 后不需要同步
- 不直接修改 `~/.claude/luxixi`、`~/.codex/luxixi` 或 `codex/luxixi`

### Claude Code 专用资产

`claude/agents/` 和 `claude/skills/` 保留 Claude Code 专用格式，不要求与 Codex skills 保持一致。

当前已有：

- `claude/agents/php-expert.md`：PHP / Webman 专项 agent
- `claude/skills/d-stop/SKILL.md`：会话收尾，维护 `PROJECT_STATUS.md`
- `claude/skills/d-webman-log/SKILL.md`：Webman 日志初始化

这些文件里的专家知识可以复用，但格式不直接视为 Codex 通用。

## 现有文件说明

- `CLAUDE.md`：本仓库给 Claude Code 使用的项目级入口
- `AGENTS.md`：本仓库给 Codex 使用的项目级入口
- `claude/CLAUDE.md`：Claude Code 全局入口源文件
- `codex/AGENTS.md`：Codex 全局入口源文件
- `webman-packages-reference.md`：Webman 常用依赖备忘
- `scripts/update.sh`：Claude Code 生态更新脚本，只服务 Claude Code
- `docs/ai-assistant-config-architecture.md`：Claude Code / Codex 共用源库的架构规划

## update.sh 职责

`scripts/update.sh` 负责每日更新 Claude Code 生态内容：

- 更新 Claude CLI
- 拉取第三方 Claude agents / skills / commands
- 安装到 `~/.claude/`

它不负责 Codex，也不承担本仓库到 `~/.claude/` / `~/.codex/` 的同步职责。同步职责后续由 `sync-claude.sh`、`sync-codex.sh`、`sync-all.sh` 承担。

## 维护原则

- 长期规则源头只维护 `claude/CLAUDE.md`、`codex/AGENTS.md` 和 `claude/luxixi/*.md`
- `~/.claude/` 和 `~/.codex/` 不作为规则源头
- 全局入口保持薄，不绑定单一技术栈
- 技术栈规则放入 `luxixi/`，由 Claude / Codex 共同引用
- Claude Code 的 agents / skills 保持在 `claude/` 下，不直接迁移为 Codex 格式
- 修改后根据需要提交并推送到 `git@github.com:flyluxixi/ai-configs.git`
