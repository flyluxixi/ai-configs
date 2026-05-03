# Claude Code / Codex 配置仓库规划

本文记录本仓库从 Claude Code 专用配置仓库，升级为 Claude Code 与 Codex 共享配置源仓库后的目录规划和使用原则。

## 背景

当前发生了两点变化：

1. 除 Claude Code 外，也需要支持 Codex。
2. 技术栈从 PHP + Webman 扩展为多技术栈：
   - 后端：PHP + Webman、Go + Gin
   - 前端：微信小程序、Nuxt 4、Flutter
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

### 3. 技术栈规则使用 luxixi + 可选 rules 适配

技术栈规则的中立源放在 `luxixi/`，Claude Code 与 Codex 共同引用。

Claude Code 官方支持 `~/.claude/rules/` 机制。如需自动按文件路径加载，可以在 `claude/rules/` 下创建带 frontmatter `paths` 的适配文件，再引用 `luxixi/` 中的中立规则。

这样既能让 Claude Code 自动按文件路径加载相关规则，也避免把 Claude 专用 frontmatter 写进 Codex 共用规则源。

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
├── CLAUDE.md                 # 本仓库自身给 Claude Code 使用
├── AGENTS.md                 # 本仓库自身给 Codex 使用
├── claude/
│   ├── CLAUDE.md             # 同步到 ~/.claude/CLAUDE.md
│   ├── rules/                # 同步到 ~/.claude/rules/
│   ├── luxixi/               # Claude / Codex 共用的中立规则源
│   │   ├── go.md
│   │   ├── php-webman.md
│   │   ├── nuxt4.md
│   │   ├── flutter.md
│   │   ├── miniprogram.md
│   │   ├── postgresql.md
│   │   ├── redis.md
│   │   └── nginx.md
│   ├── agents/               # 同步到 ~/.claude/agents/
│   ├── skills/               # 同步到 ~/.claude/skills/
│   └── commands/             # 同步到 ~/.claude/commands/
├── codex/
│   ├── AGENTS.md             # 同步到 ~/.codex/AGENTS.md
│   └── luxixi -> ../claude/luxixi
├── scripts/
│   └── update.sh             # Claude Code 专用每日更新脚本，保持现有职责
└── docs/
```

同步后的目标结构：

```text
~/.claude/
├── CLAUDE.md
├── luxixi/
├── rules/
├── agents/
├── skills/
└── commands/

~/.codex/
├── AGENTS.md
└── luxixi/
```

## rules 适配文件写法

`luxixi/` 是 Claude / Codex 共用的中立规则源，不绑定 Claude Code 的 frontmatter 格式。

如需使用 Claude Code 的 `~/.claude/rules/` 自动按路径加载机制，应在 `claude/rules/` 下新增适配文件，通过 `paths` 限定触发范围，再引用 `luxixi/` 中的中立规则。

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

@~/.claude/luxixi/php-webman.md
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

@~/.claude/luxixi/go.md
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

@~/.claude/luxixi/postgresql.md
```

`paths` 用于 Claude Code 自动触发，但不能替代项目显式声明。

## 项目显式声明

每个业务项目建议保留很薄的入口文件，用于声明项目技术栈。

Go + Gin 项目的 `CLAUDE.md`：

```md
# Project Profile

本项目使用 Go + Gin + PostgreSQL + Redis + Nginx。

@~/.claude/luxixi/go.md
@~/.claude/luxixi/postgresql.md
@~/.claude/luxixi/redis.md
@~/.claude/luxixi/nginx.md
```

Go + Gin 项目的 `AGENTS.md`：

```md
# Project Profile

本项目使用 Go + Gin + PostgreSQL + Redis + Nginx。

执行前必须先读取以下规则文件：
- `~/.codex/luxixi/go.md`
- `~/.codex/luxixi/postgresql.md`
- `~/.codex/luxixi/redis.md`
- `~/.codex/luxixi/nginx.md`
```

PHP + Webman 项目只需替换对应规则（Claude 侧，`@` 自动展开）：

```md
@~/.claude/luxixi/php-webman.md
@~/.claude/luxixi/postgresql.md
@~/.claude/luxixi/redis.md
@~/.claude/luxixi/nginx.md
```

PHP + Webman 项目的 `AGENTS.md`（Codex 侧，需显式读取）：

```md
执行前必须先读取以下规则文件：
- `~/.codex/luxixi/php-webman.md`
- `~/.codex/luxixi/postgresql.md`
- `~/.codex/luxixi/redis.md`
- `~/.codex/luxixi/nginx.md`
```

前端项目示例（Claude 侧）：

```md
@~/.claude/luxixi/nuxt4.md
```

## @ 语法在 Claude Code 与 Codex 中的差异

Claude Code 与 Codex 对 `@path` 语法的处理**完全不同**，编写入口文件和 skills 时必须区分对待。

| 场景 | Claude Code | Codex |
|------|-------------|-------|
| `CLAUDE.md` / `AGENTS.md` 中的 `@path` | 会话启动时**自动展开**，文件内容注入上下文 | **不自动展开**，仅作路径提示，模型不会主动读取 |
| Skills 中的 `@path` | skill 被调用时**自动展开** | **不自动展开**，模型不会主动读取 |

Codex 侧需要将 `@path` 改为显式读取指令：

```
# 错误（Codex 不会自动加载）
@~/.codex/luxixi/nginx.md

# 正确
首先读取 `~/.codex/luxixi/nginx.md`，获取完整规范。
```

注意：项目级 `AGENTS.md` 中引用技术栈规则时同样适用此规则，不能使用 `@` 语法。

## agents 与 skills 的定位

现有 `agents/` 和 `skills/` 仍视为 Claude Code 专用形态：

- Claude agent 文件包含 `tools`、`model`、`color` 等 Claude 专用 frontmatter。
- Claude skill 文件包含 `/d-stop`、`/d-webman-log` 等 Claude Code 使用语义。

其中的专家知识和流程可以复用，但文件格式不应直接视为 Codex 通用。

后续如需让 Codex 复用相同能力，应先抽取中立知识源，再分别生成 Claude / Codex 适配文件。

## 实施顺序

1. 从现有 `CLAUDE.md` 抽出真正全局的规则，作为 Claude / Codex 入口文件的共同基础。
2. 新增 `claude/luxixi/`，拆分 Claude / Codex 共用的中立技术栈规则。
3. 新增 `claude/CLAUDE.md` 和 `codex/AGENTS.md`。
4. 将 `codex/luxixi` 设为指向 `../claude/luxixi` 的 symlink，确保中立规则只维护一份。
5. 将现有 `agents/`、`skills/` 保持在 `claude/` 下，作为 Claude Code 专用资产。
6. 将 `~/.claude/CLAUDE.md`、`~/.codex/AGENTS.md` 改为 symlink 指向本仓库对应文件，无需 sync 脚本。
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

技术栈规则以 `luxixi/` 作为中立源；Claude Code 如需自动触发，可在 `rules/` 下用 `paths` 创建适配文件。业务项目通过 `CLAUDE.md` / `AGENTS.md` 显式声明 profile，避免路径遗漏导致规则失效。
