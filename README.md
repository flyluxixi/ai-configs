# Claude Code 个人配置仓库

本仓库是针对 **PHP / Webman 技术栈**的 Claude Code 自定义配置，包含全局开发规范和可复用的自定义 Skill。

---

## 技术栈

| 层级 | 技术 |
|---|---|
| 语言 | PHP 8.5 |
| 框架 | Webman（常驻内存，非 FPM） |
| 数据库 | PostgreSQL |
| 缓存 / 队列 | Redis |
| Web Server | Nginx |
| 操作系统 | Ubuntu 24.04 / AlmaLinux 10.1 |

---

## 仓库结构

```
claude-code/
├── CLAUDE.md            # 全局开发规范（同步至 ~/.claude/CLAUDE.md）
├── PROJECT_STATUS.md    # 会话状态记录，由 /d-stop 维护
├── agents/
│   └── php-expert.md   # PHP/Webman 专项 agent
├── scripts/
│   └── update.sh        # 一键更新 Claude CLI 及所有 skills/agents/commands
├── skills/
│   ├── d-stop/
│   │   └── SKILL.md    # 会话收尾 skill
│   └── d-webman-log/
│       └── SKILL.md    # Webman 日志初始化 skill
└── README.md
```

---

## CLAUDE.md 规范要点

全局规范涵盖以下核心约束，在所有项目中生效：

- **最高原则**：性能和稳定性优先；能用平台（PostgreSQL / Redis / Nginx）解决的不用代码绕
- **Webman 高风险区域**：明确禁止静态属性缓存请求数据、循环内 DB 查询、手动 new PDO、$GLOBALS 传递请求状态
- **PHP 编码**：强制 `strict_types=1`，命名规范、类型优先级、方法行数上限
- **数据库**：禁止字符串拼接 SQL，优先 CTE / 窗口函数，迁移脚本幂等
- **安全**：密钥走环境变量、禁止硬编码、所有用户输入必须验证
- **配置管理**：config/ 只写结构和默认值，运行时差异通过环境变量注入
- **Agent 使用**：php-expert / database-reviewer / security-reviewer 等专项 Agent 应主动调用，不等用户提示

---

## 自定义 Agents

### `php-expert` — PHP / Webman 专项 Agent

**触发时机**：涉及 PHP 代码编写、修改或审查时自动调用，包括：
- Controller / Service / Model / Middleware / Process 文件
- Webman 常驻进程问题（静态变量污染、内存泄漏、Worker 配置）
- PHP 侧 Redis 集成（缓存策略、分布式锁、Pipeline）
- Eloquent / Query Builder 写 PostgreSQL / PostGIS 查询
- PHP 代码安全审查（SQL 注入、幂等性、N+1 优化）

**不触发**：纯 SQL 建表/迁移/索引、纯 Redis 或 Nginx 配置、非 PHP 语言、不含 PHP 代码的数据库架构设计。

**文件**：`agents/php-expert.md`

---

## 自定义 Skills

### `/d-stop` — 会话收尾

**触发时机**：每次工作结束时调用。

**行为**：
- 更新 `PROJECT_STATUS.md`，记录本次完成事项、下次继续方向、未解决问题和重要上下文
- 写完后朗读"下次继续"部分确认，并推送到远程仓库

**文件**：`skills/d-stop/SKILL.md`

---

### `/d-webman-log` — Webman 日志初始化

**触发时机**：在 Webman 项目目录下执行 `/d-webman-log`，或提到"日志初始化"、"log setup"、"request_id 中间件"等关键词时主动触发。

**执行流程**：

1. **探测环境**：读取 `composer.json` 判断 Monolog 版本（2.x / 3.x），检查 `config/log.php` 和 `RequestIdMiddleware` 是否已存在，探测单应用 / 多应用目录结构，读取 `/etc/os-release` 确认 OS 类型
2. **生成 `config/log.php`**：日志级别由 `APP_DEBUG` / `LOG_LEVEL` 环境变量控制，不硬编码；使用 `RotatingFileHandler` 按天切割保留 30 天；通过 `support\Context` 注入 `request_id`，禁止在中间件 `pushProcessor`（Webman 常驻进程内存泄漏风险）
3. **生成 `RequestIdMiddleware`**：优先复用上游 `X-Request-Id` 请求头，用 `?:` 过滤空字符串（而非 `??`）；已存在但不合规时不自动覆盖，提示用户手动修正
4. **生成 `docs/PHPLOG.md`**：含编号部署步骤（注册中间件、Nginx logrotate、Nginx log_format、PostgreSQL 日志配置、PG 旧日志清理 cron），建议提交到 git 供团队共享

**关键设计决策**：
- Webman 应用日志由 Monolog 自管切割，**不走 logrotate**（双重切割会导致句柄错乱）
- Nginx `log_format` 命名为 `webman`，避免与默认 `main` 冲突
- PG 日志路径按 OS 自动选择（Ubuntu 路径 vs RHEL/AlmaLinux 路径）

**文件**：`skills/d-webman-log/SKILL.md`

---

## 安装与使用

将本仓库的 `CLAUDE.md` 内容同步至 `~/.claude/CLAUDE.md`，将 `skills/` 和 `agents/` 目录下的内容复制到 `~/.claude/skills/` 和 `~/.claude/agents/`，Claude Code 会自动加载，无需额外注册。

---

## update.sh — 一键更新脚本

`scripts/update.sh` 负责自动更新 Claude CLI 本身以及以下第三方 skills / agents / commands：

| 来源仓库 | 内容 |
|---|---|
| affaan-m/everything-claude-code | build-error-resolver、database-reviewer、security-reviewer agents；api-design、postgres-patterns、security-review skills；build-fix、update-docs、verify commands |
| obra/superpowers | systematic-debugging、verification-before-completion skills |
| anthropics/claude-plugins-official | frontend-design、skill-creator、agent-sdk-dev 等官方 skills；code-review command |
| nextlevelbuilder/ui-ux-pro-max-skill | ui-ux-pro-max skill |
| jnMetaCode/agency-agents-zh | 微信小程序开发者 agent |

### 手动执行

```bash
bash ~/.claude/scripts/update.sh
```

### 设置 cron 定时（每天凌晨 4 点）

```
0 4 * * * bash ~/.claude/scripts/update.sh
```

日志自动写入 `~/.claude/update-logs/YYYY-MM-DD.log`，只保留最近 3 天。

### macOS 注意事项

- 依赖 Homebrew（`/opt/homebrew/bin`）和 npm global 路径，脚本启动时已自动写入 `PATH`
- 若 cron 执行时报权限错误，可尝试授予完全磁盘访问权限：系统设置 → 隐私与安全性 → 完全磁盘访问 → 点击 `+` → 按 `⌘⇧G` 输入 `/usr/sbin/cron` 添加

---

## 维护说明

- 每次工作结束调用 `/d-stop`，由 Skill 自动维护 `PROJECT_STATUS.md`
- 规范变更直接修改 `CLAUDE.md`，同步至 `~/.claude/CLAUDE.md`
- Skill 迭代可使用 `/skill-creator` 进行评估和优化
