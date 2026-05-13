---
name: d-review
description: 代码审查 + 修复循环 + Git 提交推送 + 服务器部署 + 运行状态检查的一站式 skill。触发条件：用户输入 /d-review 或 /d-review --codex。/d-review 由 Claude Code 自行审查；/d-review --codex 调用 /codex:adversarial-review --background 进行对抗性审查。两条路径审查通过后均执行：git commit → git push → 部署到服务器 → 检查运行状态。仅供 Claude Code 使用，不适用于 Codex。
---

# d-review — 审查 · 修复 · 提交 · 部署

> **执行约定**：本 skill 中所有 shell 命令均通过 `rtk` 前缀执行（全局规范）。示例中的 `git`、`ssh`、`curl` 等命令在实际执行时均写作 `rtk git ...`、`rtk ssh ...`、`rtk curl ...`。

## 入口识别

| 用户输入 | 审查方式 |
|----------|----------|
| `/d-review` | Claude Code 自审（内联分析） |
| `/d-review --codex` | `/codex:adversarial-review --background`（对抗性审查） |

收到触发指令后，**不要询问确认，直接进入第一步**。

---

## 第一步：确定审查范围

1. 运行 `git diff HEAD` 查看未提交变更；若无未提交变更，运行 `git diff main...HEAD`（或当前分支与主分支的差异）
2. 列出本次涉及的文件清单，告知用户审查范围
3. 若变更为空，停止并提示："当前没有待提交的变更，d-review 终止。"

---

## 第二步：代码审查（Fix Loop）

### 路径 A — Claude 自审（无 --codex）

对第一步确定的变更文件逐一检查：

检查维度（按优先级）：
1. **安全**：硬编码密钥/token、未转义输出、未校验用户输入、CSRF 缺失、SQL 注入风险
2. **正确性**：逻辑错误、边界条件、空值处理、类型不匹配
3. **性能**：N+1 查询、不必要的全表扫描、重复计算、内存泄漏风险
4. **可维护性**：命名歧义、重复代码（三处以上相似逻辑）、缺失必要注释（非显而易见的 WHY）

发现问题则修复，但**修复必须保守**：只改有客观依据的问题，不因"可以更好"就顺手重构；每次只改最小必要范围，不连带修改审查范围外的代码。修复后重新检查被修复的文件，**循环直到该轮无新问题**。

每轮修复完成后，输出简洁摘要：
```
[审查轮次 N] 修复 X 处问题：<简短描述>
```

无问题时输出：
```
[审查通过] 未发现问题，进入提交流程。
```

### 路径 B — Codex 对抗性审查（--codex）

#### B-1：调用审查

通过 Bash 后台运行 codex-companion 脚本（**不得使用 Skill 工具调用**，会因 disable-model-invocation 报错）：

```bash
COMPANION=$(find ~/.claude/plugins -name "codex-companion.mjs" 2>/dev/null | head -1)
node "$COMPANION" adversarial-review ""
```

- `$COMPANION` 有值 → 以 `run_in_background: true` 方式启动，等待任务完成通知后读取输出文件
- `$COMPANION` 为空 → 停止并提示用户 codex-plugin-cc 未安装，请手动在 Claude Code 终端执行：
  ```
  /plugin marketplace add openai/codex-plugin-cc
  /plugin install codex@openai-codex
  /codex:setup
  ```

#### B-2：评估每条反馈（不盲信，先判断）

Codex 对抗性审查的职责是质疑和挑战，其反馈不代表事实，必须逐条独立评估后再决定是否修复。

对每条反馈，按以下标准分类：

| 分类 | 判断标准 | 处理 |
|------|----------|------|
| **必须修复** | 安全漏洞、明确 bug、数据丢失/损坏风险，有客观依据 | 直接修复 |
| **建议修复** | 性能隐患、可维护性问题，Codex 给出了合理依据且与项目上下文不矛盾 | 修复 |
| **设计争议** | 架构风格、命名偏好、无客观正误，或 Codex 基于假设而非代码事实提出的质疑 | 列出告知用户，**不阻塞流程**，由用户决定 |
| **误报/不适用** | 基于错误假设、不了解项目约定、与项目技术栈不符 | 记录原因后跳过 |

评估时的判断原则：
- Codex 说"应该用 X 方案"，先确认当前方案是否有客观缺陷；若仅是风格差异，归为设计争议
- Codex 指出潜在 bug，先在代码中验证该路径是否真实存在；若无对应代码路径，归为误报
- 安全类反馈从严：有合理怀疑即归为必须修复，不要求 100% 确定
- **修复必须保守**：只改 Codex 明确指出的问题，不借机重构周边代码，不扩大改动范围

#### B-3：一次性修复，不循环

仅对「必须修复」和「建议修复」的条目执行修复，**不再重跑 Codex 做复审**。

对抗性审查的职责是挑战，不是验收——重复运行只会让它越来越偏离代码本身，不构成有效的终止条件。

修复完成后输出一次性摘要：
```
[Codex 审查完成]
  修复：X 处（安全/bug/性能）
  设计争议：Y 处（已列出，待用户确认）
  跳过误报：Z 处
```

输出后直接进入第三步（运行测试）。

---

## 第三步：运行测试

审查/修复完成后，在提交前自动发现并运行项目测试。

### 测试发现顺序

按以下顺序找到第一个可用的测试命令并执行：

| 特征文件 | 测试命令 |
|----------|----------|
| `package.json` 含 `"test"` script | `npm test` 或 `yarn test` |
| `composer.json` 含 `"test"` script | `composer test` |
| `phpunit.xml` / `phpunit.xml.dist` 存在 | `./vendor/bin/phpunit` |
| `go.mod` 存在 | `go test ./...` |
| `Makefile` 含 `test` target | `make test` |
| `pytest.ini` / `pyproject.toml` 存在 | `pytest` |
| `Cargo.toml` 存在 | `cargo test` |

- 找到可用命令 → 执行，输出结果摘要
- 未找到任何测试配置 → 输出"未发现测试配置，跳过。"后直接继续，**不询问是否创建测试**
- **测试失败 → 停止，输出失败信息，不进入提交流程**，等用户修复后重新触发

### 输出格式

```
[测试] 使用 npm test
✓ 全部通过（42 tests, 0 failures）

或

✗ 测试失败（3 failures）
  → <失败摘要>
  → 请修复后重新执行 /d-review
```

---

## 第四步：确认后 Git 提交 · 推送

审查/修复通过且测试通过后，**必须暂停并向用户明确确认**，再执行任何 git 操作：

```
审查已通过，共修复 X 处问题。
准备执行：git add → commit → push → 部署。
确认继续？（回复"继续"或"跳过提交/部署"）
```

用户回复"跳过"或"不提交" → 停止，输出审查摘要后结束，不执行后续任何步骤。

用户确认继续后执行：

```bash
git status   # 确认暂存区只含本次任务相关文件，无 .DS_Store / PROJECT_STATUS.md / .env
git add <本次变更的具体文件>   # 不用 git add -A 或 git add .
git commit -m "<type>: <description>"
git push
```

Commit message 格式遵循全局规范：`feat` / `fix` / `docs` / `refactor` / `perf` / `test` / `build` / `ci` / `chore`。

**提交前必须检查**：
- `git status` 输出中是否有 `.env`、`PROJECT_STATUS.md`、`.DS_Store` 或其他不相关文件
- 有则排除后再提交，并告知用户哪些文件被排除

---

## 第五步：部署到服务器

### 5.1 读取部署约定

按以下顺序查找部署信息：

1. **读项目记忆**：检查 Claude Code 记忆文件中是否有当前项目的服务器地址、部署命令、部署路径的记录
2. **读项目文档**：依次检查 `PROJECT_STATUS.md`、`CLAUDE.md`、`docs/DEPLOY.md`（或同名变体）是否声明了部署方式
3. **读 Makefile / 脚本**：检查项目根目录是否有 `Makefile`（含 `deploy` target）或 `scripts/deploy.sh`
4. **从 `.env` 只提取连接元数据（显式白名单）**：不读整个 `.env` 文件，只提取以下纯连接信息键名：
   ```bash
   grep -E '^(DEPLOY_HOST|DEPLOY_USER|DEPLOY_PATH|DEPLOY_PORT)=' .env 2>/dev/null
   ```
   - `DEPLOY_COMMAND` **不在白名单内**：部署命令可能内嵌 token、私钥路径、webhook URL 等，不从 `.env` 读取，改从项目文档/Makefile/脚本中获取，或直接询问用户
   - **若检测到键名含 `TOKEN`、`PASSWORD`、`SECRET`、`KEY` 等字样，拒绝读取并告知用户**，改为询问用户直接提供服务器信息

找到可信部署信息 → 直接执行，告知用户正在使用哪种方式。

### 5.2 部署信息不完整时

若以上均无部署信息，向用户提问（**一次问完，不分多轮**）：

```
未找到部署配置，请提供以下信息（不需要部署可直接回复"跳过"）：

1. 是否要登录服务器部署？
2. 服务器地址（如 user@host 或 IP）
3. 项目在服务器上的路径
4. 部署命令（如 "cd /path && git pull && supervisorctl restart app"）
```

用户回复"跳过"或"不部署"→ 跳过第五步和第六步，输出"已跳过部署。"后结束。

收到部署信息后，**自动将以下内容存入 Claude Code 记忆（project 类型），无需额外询问**：
- 服务器地址
- 项目路径
- 部署命令

存入记忆后告知用户："部署配置已保存到记忆，下次无需重复输入。"

### 5.3 执行部署

根据部署命令执行，实时输出关键步骤结果。

常见部署模式参考（按项目实际情况选用，不强制）：

| 模式 | 典型命令 |
|------|----------|
| SSH + git pull | `ssh user@host "cd /path && git pull && <restart>"` |
| rsync | `rsync -avz --exclude='.env' ./ user@host:/path/` |
| Docker | `ssh user@host "docker pull <image> && docker-compose up -d"` |
| Makefile | `make deploy` |

---

## 第六步：检查运行状态

部署完成后，根据项目类型选择最合适的检查方式（优先级从高到低）：

### 检测顺序

1. **HTTP 健康检查**（首选）
   - 检查项目中是否有 `/health`、`/ping`、`/status` 等端点（搜索路由文件）
   - 有则：`curl -sf https://<host>/health` 并验证响应码 200 和响应体
   - 无则进入下一项

2. **进程检查**
   - Webman / PHP：`ssh user@host "ps aux | grep webman | grep -v grep"`
   - Go：`ssh user@host "ps aux | grep <binary-name> | grep -v grep"`（binary 名从项目 `Makefile` 或 `go.mod` 的 module name 推断）
   - Node.js：`ssh user@host "pm2 status <app-name>"` 或 `ps aux | grep node`
   - Docker：`ssh user@host "docker ps --filter name=<container>"`
   - Systemd 服务：`ssh user@host "systemctl is-active <service>"`

3. **端口检查**（进程检查失败时补充）
   - `ssh user@host "ss -tlnp | grep <port>"` 或 `curl -sf http://localhost:<port>/`

4. **数据库连通性检查**（可选，仅在应用无健康端点时补充）
   - 在服务器上执行，不读取也不传递凭据到 assistant 上下文：
   - PostgreSQL：`ssh user@host "pg_isready -h localhost"`
   - MySQL/MariaDB：`ssh user@host "mysqladmin ping -h localhost"`
   - 上述命令不需要密码，仅探测服务端口是否可达

5. **近期日志检查**（任何方式检查后都附加）
   - `ssh user@host "tail -n 20 <log_path>"` 查看有无 ERROR / FATAL / panic

### 输出格式

```
[部署状态]
✓ 进程运行中（PID: xxx）
✓ 健康检查通过（HTTP 200）
✓ 日志无异常（近 20 行）

或

✗ 健康检查失败（HTTP 503）
  → 近期日志：<关键错误行>
  → 建议：<简短排查方向>
```

发现异常时，**不自动回滚**，告知用户具体错误和初步排查方向，由用户决定下一步。

---

## 流程总览

```
触发
  ↓
[1] 确定变更范围
  ↓
[2A] Claude 自审          [2B] Codex 对抗性审查
     ↓ fix loop                ↓ 评估每条反馈（必须/建议/争议/误报）
                               ↓ 仅修复「必须」和「建议」→ 复审循环
  审查通过
  ↓
[3] 发现并运行项目测试 → 失败则停止
  ↓
[确认门] 暂停，等用户明确确认后才继续
  ↓
[4] git add → commit → push
  ↓
[5] 读取/询问部署配置 → 执行部署
  ↓
[6] 健康检查 → 输出状态
  ↓
完成
```

---

## 注意事项

- **禁止写入测试数据**：部署和运行状态检查过程中，严禁向数据库插入、更新或删除任何数据，除非用户明确要求
- **不自动回滚**：部署后发现异常，告知用户并提供方向，不擅自执行回滚
- **不跳过审查**：fix loop 必须至少完整执行一轮，不允许零问题直接跳过
- **修复保守原则**：只修有客观依据的问题，不因"可以更好"扩大改动；每次只改最小必要范围，不连带重构审查范围外的代码
- **Codex 结果不盲信**：必须逐条评估，仅修复「必须修复」和「建议修复」；设计争议告知用户，误报跳过并说明原因
- **安全类从严**：有合理怀疑即归为必须修复，不要求 100% 确定
- **插件安装须确认**：`--codex` 模式下检测到未安装时，告知插件身份和安装步骤，等用户明确回复"安装"后才执行
- **Codex 调用方式**：必须通过 Bash 执行 codex-companion.mjs，禁止使用 Skill 工具（会触发 disable-model-invocation 错误）
- **确认门不可跳过**：审查通过后必须等用户明确回复"继续"才执行 git 和部署，不得静默推进
- **健康检查不持有数据库密码**：DB 连通性通过 `pg_isready` / `mysqladmin ping` 在服务器端探测（无需密码），不读取 `.env` 中的凭据
- **`.env` 只 grep `DEPLOY_*`**：禁止读取整个 `.env` 文件，DB 密码等其他内容不进入 assistant 上下文
- **Git 安全**：永远不用 `git add -A`，永远检查暂存区，永远不跳过 pre-commit hook
- **密钥不进日志**：部署命令输出中若出现疑似 token/密码，用 `***` 遮盖后再展示
- **仅限 Claude Code**：本 skill 依赖 `/codex:adversarial-review` 插件调用，不适用于 Codex CLI
