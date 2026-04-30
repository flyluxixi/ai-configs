# Claude Code / Codex 配置仓库规划

本文记录本仓库从 Claude Code 专用配置仓库，升级为 Claude Code 与 Codex 共享配置源仓库后的目录规划和使用原则。

## 背景

当前发生了两点变化：

1. 除 Claude Code 外，也需要支持 Codex。
2. 技术栈从 PHP + Webman 扩展为多技术栈：
   - 后端：PHP + Webman、Go + Gin
   - 前端：微信小程序、Nuxt 3、Flutter
   - 数据库：PostgreSQL
   - 缓存 / 队列：Redis
   - Web Server：Nginx

因此，本仓库不应继续以单一技术栈作为全局默认，而应成为多技术栈 AI 编程助手配置源。

## 核心原则

### 1. 本仓库是唯一源头

`~/.claude/` 和 `~/.codex/` 都是同步目标，不作为手工维护源头。

所有长期规则、模板、agents、skills、同步脚本都应先在本仓库中维护，再由脚本同步到对应目录。

### 2. 全局规则只放所有项目都成立的内容

全局入口文件只放不依赖具体技术栈的规则，例如：

- 回复语言和沟通方式
- 使用 `rtk` 执行 shell 命令
- 不默认假设项目技术栈
- 先读项目 README / CLAUDE.md / AGENTS.md
- 项目级规则优先
- 不覆盖用户未授权改动
- Git、文档、安全底线等通用要求

不要把 PHP、Go、Nuxt、Flutter 等专项规则直接写入全局入口。

### 3. 技术栈规则使用 rules + paths

Claude Code 官方支持 `~/.claude/rules/` 机制。技术栈规则应放在 rules 目录，并通过 frontmatter 的 `paths` 限定触发范围。

这样可以让 Claude Code 自动按文件路径加载相关规则，同时避免所有技术栈规则无条件进入上下文。

### 4. 项目 profile 作为兜底

`paths` 可能写不全，尤其 PostgreSQL / Redis / Nginx 这类跨语言规则很难完全靠路径判断。

因此业务项目仍应通过 `CLAUDE.md` / `AGENTS.md` 显式声明项目技术栈，作为规则启用兜底。

### 5. update.sh 不改职责

`scripts/update.sh` 是每日执行的 Claude Code 生态更新脚本，只服务 Claude Code：

- 更新 Claude CLI
- 拉取 Claude 生态 agents / skills / commands
- 安装到 `~/.claude/`

它不负责 Codex，也不需要改造成 Codex 兼容脚本。

## 推荐目录结构

```text
ai-configs/
├── README.md
├── PROJECT_STATUS.md
├── claude/
│   ├── CLAUDE.md             # 同步到 ~/.claude/CLAUDE.md
│   ├── rules/                # 同步到 ~/.claude/rules/
│   ├── luxixi/               # Claude / Codex 共用的中立规则源
│   │   ├── go.md
│   │   ├── php-webman.md
│   │   ├── nuxt3.md
│   │   ├── flutter.md
│   │   └── miniprogram.md
│   ├── agents/               # 同步到 ~/.claude/agents/
│   ├── skills/               # 同步到 ~/.claude/skills/
│   └── commands/             # 同步到 ~/.claude/commands/
├── codex/
│   ├── AGENTS.md             # 同步到 ~/.codex/AGENTS.md
│   └── luxixi -> ../claude/luxixi
├── scripts/
│   ├── update.sh             # Claude Code 专用每日更新脚本，保持现有职责
│   ├── sync-claude.sh        # 同步本仓库配置到 ~/.claude/
│   ├── sync-codex.sh         # 同步本仓库配置到 ~/.codex/
│   └── sync-all.sh           # 同步两边
└── docs/
```

同步后的目标结构：

```text
~/.claude/
├── CLAUDE.md
├── rules/
├── agents/
├── skills/
└── commands/

~/.codex/
├── AGENTS.md
└── luxixi/
```

## rules 文件写法

每个技术栈规则文件都应带 `paths`，避免无条件加载。

PHP / Webman 示例：

```md
---
paths:
  - "**/*.php"
  - "composer.json"
  - "composer.lock"
  - "config/**/*.php"
  - "app/**/*.php"
  - "process/**/*.php"
---

# PHP / Webman 规则
```

Go / Gin 示例：

```md
---
paths:
  - "**/*.go"
  - "go.mod"
  - "go.sum"
  - "**/router/**/*.go"
  - "**/middleware/**/*.go"
---

# Go / Gin 规则
```

PostgreSQL 示例：

```md
---
paths:
  - "**/*.sql"
  - "**/migrations/**"
  - "**/database/**"
  - "**/db/**"
  - "**/*.php"
  - "**/*.go"
---

# PostgreSQL 规则
```

`paths` 用于自动触发，但不能替代项目显式声明。

## 项目显式声明

每个业务项目建议保留很薄的入口文件，用于声明项目技术栈。

Go + Gin 项目的 `CLAUDE.md`：

```md
# Project Profile

本项目使用 Go + Gin + PostgreSQL + Redis + Nginx。

@~/.claude/rules/backend.md
@~/.claude/rules/go-gin.md
@~/.claude/rules/postgres.md
@~/.claude/rules/redis.md
@~/.claude/rules/nginx.md
```

Go + Gin 项目的 `AGENTS.md`：

```md
# Project Profile

本项目使用 Go + Gin + PostgreSQL + Redis + Nginx。

@~/.codex/rules/backend.md
@~/.codex/rules/go-gin.md
@~/.codex/rules/postgres.md
@~/.codex/rules/redis.md
@~/.codex/rules/nginx.md
```

PHP + Webman 项目只需替换对应规则：

```md
@~/.claude/rules/backend.md
@~/.claude/rules/php-webman.md
@~/.claude/rules/postgres.md
@~/.claude/rules/redis.md
@~/.claude/rules/nginx.md
```

前端项目示例：

```md
@~/.claude/rules/frontend.md
@~/.claude/rules/nuxt3.md
```

## agents 与 skills 的定位

现有 `agents/` 和 `skills/` 仍视为 Claude Code 专用形态：

- Claude agent 文件包含 `tools`、`model`、`color` 等 Claude 专用 frontmatter。
- Claude skill 文件包含 `/d-stop`、`/d-webman-log` 等 Claude 指令语义。

其中的专家知识和流程可以复用，但文件格式不应直接视为 Codex 通用。

后续如需让 Codex 复用相同能力，应先抽取中立知识源，再分别生成 Claude / Codex 适配文件。

## 实施顺序

1. 从现有 `CLAUDE.md` 抽出真正全局的规则，作为 Claude / Codex 入口文件的共同基础。
2. 新增 `claude/luxixi/`，拆分 Claude / Codex 共用的中立技术栈规则。
3. 新增 `claude/CLAUDE.md` 和 `codex/AGENTS.md`。
4. 将 `codex/luxixi` 设为指向 `../claude/luxixi` 的 symlink，确保中立规则只维护一份。
5. 将现有 `agents/`、`skills/` 保持在 `claude/` 下，作为 Claude Code 专用资产。
6. 新增 `scripts/sync-claude.sh`、`scripts/sync-codex.sh`、`scripts/sync-all.sh`。
7. 保持 `scripts/update.sh` 原职责不变。
8. 更新 README，说明本仓库是 Claude Code / Codex 共享配置源。

## 最终结论

本仓库应采用：

```text
luxixi/ 作为 Claude / Codex 共用的中立规则源
claude/ 作为 Claude Code 适配层
codex/ 作为 Codex 适配层
~/.claude/ 和 ~/.codex/ 作为同步目标
```

技术栈规则使用 `rules/` 命名，并通过 `paths` 实现自动触发；业务项目通过 `CLAUDE.md` / `AGENTS.md` 显式声明 profile，避免路径遗漏导致规则失效。
