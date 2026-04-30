# Claude Code 全局规范

最后更新：2026-04-30

本文件是 Claude Code 全局入口，只放所有项目都成立的规则。具体技术栈规则放在 `~/.claude/luxixi/`，由业务项目的 `CLAUDE.md` 按需引用。

当本规范与项目级 `CLAUDE.md` 冲突时，项目级优先。

## 基本原则

- 不默认假设项目技术栈；先读项目 `README.md`、`CLAUDE.md`、`AGENTS.md` 和相关文档
- 复杂任务（涉及多文件修改、架构变更）动手前先说明方案，确认后再执行
- 单文件小修改直接执行，完成后说明改了什么
- 需求不明确时直接问，不自行假设
- 若任务本身存在明显的设计缺陷、性能风险或安全风险，直接说明并提出替代方案
- 每次只修改任务范围内的文件，不顺手重构无关模块
- 不覆盖用户未授权改动
- 不自动生成测试文件，除非明确要求

## 技术栈规则

技术栈规则按需由项目级文件显式引用，例如：

```md
@~/.claude/luxixi/php-webman.md
@~/.claude/luxixi/postgresql.md
@~/.claude/luxixi/redis.md
@~/.claude/luxixi/nginx.md
```

当前规划的中立规则文件：

- `~/.claude/luxixi/php-webman.md`
- `~/.claude/luxixi/go.md`
- `~/.claude/luxixi/nuxt3.md`
- `~/.claude/luxixi/flutter.md`
- `~/.claude/luxixi/miniprogram.md`
- `~/.claude/luxixi/postgresql.md`
- `~/.claude/luxixi/redis.md`
- `~/.claude/luxixi/nginx.md`

## 平台优先

性能和稳定性优先。遇到多种实现方案时，优先选择资源开销更小、执行路径更短、由成熟平台能力承担更多工作的方案。

通用判断：

- 能让平台解决的，不用业务代码绕
- 能一次解决的，不做两次
- 跑通不等于正确；没有资源泄漏、垃圾数据和状态残留，才算完成

## 安全规范

- 密钥、appid、appsecret、token 等全部走环境变量，禁止硬编码
- 所有用户输入必须验证和过滤
- 所有输出到 HTML 的内容必须转义，防止 XSS
- 文件上传必须校验 MIME 类型和扩展名，禁止存储到 Web 可访问路径
- 涉及状态变更的接口必须有 CSRF 防护或等效防护
- 敏感数据（密码、密钥、完整 token）不写入日志
- 涉及金额或状态变更的操作必须有幂等性保护
- 除完全公开接口外，API 必须有认证和授权检查
- 其他 Web 安全问题遵循 OWASP Top 10，具体防护措施按项目要求补充

## 配置管理

- 配置与代码分离：端口、进程数、超时、日志级别等运行时配置一律通过环境变量注入
- `config/` 文件只写结构和安全默认值，不写环境差异
- `config/` 文件进 git，`.env` 不进 git
- `.env.example` 提供所有变量的说明和安全默认值
- 系统级新依赖需说明理由和运维影响

## 项目文档规范

以下为原则性约束，具体文件路径、文档结构和访问方式在各项目级 `CLAUDE.md` 中声明。

- 每个项目必须在项目级 `CLAUDE.md` 中声明文档清单（有哪些文档、各自职责、谁来维护）
- 文档文件名一经在项目级确定，不得自行新增、重命名或拆分
- 需要对齐其他项目接口时，必须先 fetch 该项目声明的接口文档，不得凭记忆假设接口结构
- `CHANGELOG.md` 格式统一遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)
- 每次完成功能或修复后追加对应条目，不得回溯覆盖历史记录

## 行为规范

- 接到多步骤任务时，先列出每步的完成标准，确认后再动手
- 完成后说明改了什么、为什么、有何注意事项、用了哪些平台特性
- 不罗列执行步骤，直接给结论
- 发现潜在问题（性能隐患、安全漏洞、逻辑缺陷）主动提出
- 遇到多种可行方案，直接推荐最优的一种并说明理由，不做冗长对比
- 代码不省略关键实现，不用 `// ...` 占位，不用“其余保持不变”之类模糊表述
- 代码之外的解释保持简洁，不重复已知信息
- 给出 Nginx / Redis / PostgreSQL 配置时，提供完整配置块，不给片段

## Agent / Skill 使用规范

以下 Agent / Skill 在适配场景时应主动调用，无需等用户提示：

| Agent / Skill | 触发场景 |
|---|---|
| php-expert | PHP 代码编写、Webman 进程问题、PHP 侧 Redis 集成、QueryBuilder/Eloquent 写法审查、PHP 层性能审查（N+1/幂等性） |
| database-reviewer | 编写 SQL、设计 Schema、排查数据库性能（含 ORM/QueryBuilder 生成的 SQL 优化） |
| security-reviewer | 认证授权、用户输入处理、API 端点、敏感数据操作、SQL 注入防护 |
| build-error-resolver | 构建失败、类型错误 |
| 微信小程序开发者 | 微信小程序相关开发 |
| /d-webman-log | Webman 项目日志初始化、配置 request_id 中间件；详细触发词见 `skills/d-webman-log/SKILL.md` |
| /d-stop | 会话收尾、更新项目状态；详细触发词见 `skills/d-stop/SKILL.md` |

多个独立任务尽量并行调用，不串行等待。

## 工具使用规范

- Shell 命令使用 `rtk` 前缀执行
- 查询第三方库文档优先使用 context7，不得凭训练记忆回答 API / 配置细节
- Webman 文档 library ID：`/webman-php/webman-manual`
- 只有 context7 明确返回“未找到”时才降级到 WebFetch

## Git 规范

Commit 格式：

```text
<type>: <description>

<optional body>
```

类型：`feat`、`fix`、`refactor`、`docs`、`test`、`chore`、`perf`、`ci`

Pull Request：

1. 分析完整 commit 历史（不只看最新一条），用 `git diff [base-branch]...HEAD` 查看全量变更
2. PR 描述包含：变更摘要、测试计划

## 本配置仓库维护

本项目是 `~/.claude/` 和 `~/.codex/` 的源仓库。修改本项目文件后，必须询问用户是否同步到全局目录，不得自动同步。

## 语言规范

- 回复语言：简体中文
- 代码：变量名、函数名、类名用英文
- 注释与文档：简体中文

@RTK.md
