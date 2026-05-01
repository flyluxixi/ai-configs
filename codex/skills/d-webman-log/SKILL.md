---
name: d-webman-log
description: 为 Webman + PHP8.x + PostgreSQL + Redis + Nginx 技术栈的项目初始化日志配置。执行后自动生成符合规范的 config/log.php 和 RequestIdMiddleware，并输出 Nginx logrotate、PostgreSQL 日志配置和 cron 清理条目供手动部署。在以下场景主动使用此 skill：用户输入 /d-webman-log、提到"日志初始化"、"log setup"、"初始化日志"、"配置日志"、"日志规范"、"request_id 中间件"，或在 Webman 项目目录下提到日志相关问题时。
---

# d-webman-log — Webman 项目日志初始化

## 执行流程

### 第一步：探测项目环境

依次读取以下信息，收集完再生成代码，不要边探测边输出：

1. **验证 Monolog 安装状态**（硬性前置，不满足则停止）
   - 检查 `vendor/monolog` 目录是否存在
     - 不存在 → **停止**，输出：`Monolog 未安装，请先执行 composer require monolog/monolog:^3.0，完成后重新执行此 skill。`
   - 读 `composer.json` 中 `require` 的 `monolog/monolog` 版本约束
     - `^2` 或 `2.*` → **停止**，输出：`检测到 Monolog 2.x，当前技术栈支持 3.x。请先执行 composer require monolog/monolog:^3.0 升级，完成后重新执行此 skill。`
     - `^3` 或 `3.*`，或 composer.json 中未声明但 vendor/monolog 已存在 → 继续，使用 3.x

2. **检查 `config/log.php`**
   - 存在且包含 `'default'` key → 标记为"已有配置，需确认覆盖"
   - 不存在或内容为空 → 标记为"新建"

3. **检查 `app/middleware/RequestIdMiddleware.php`**
   - 不存在 → 标记为"待生成"
   - 存在且内容使用 `?: uniqid` → 标记为"已存在且合规，跳过"
   - 存在但使用 `?? uniqid` 或其他写法 → 标记为"已存在但不合规"。输出差异要点（比如"现有版本用 `??`，无法过滤空字符串 request_id"），提示用户自行修正或删除后重新执行，skill 不自动覆盖

4. **探测项目结构**（Webman 单应用 vs 多应用）
   - `app/middleware/` 存在 → 单应用模式，按默认路径生成
   - 只存在 `app/<app-name>/middleware/`（如 `app/api/middleware/`）→ 多应用模式，列出候选目录询问用户选择哪个，或全部生成
   - 两者都不存在 → 按单应用默认创建 `app/middleware/`

5. **探测操作系统**（用于确定 PG 日志路径）
   - 读 `/etc/os-release` 判断发行版：Debian/Ubuntu 系 / RHEL 系
   - fallback：依次 `ls /var/lib/postgresql` 和 `ls /var/lib/pgsql`，哪个存在用哪个对应的路径
   - 仍无法确定 → 在 PHPLOG.md 同时列出两条路径，注明让用户按实际情况选择
   - 路径对照：
     - Debian/Ubuntu：`/var/lib/postgresql/<version>/main/log/`
     - RHEL/AlmaLinux/Rocky/CentOS：`/var/lib/pgsql/<version>/data/log/`

6. **探测 Webman 进程日志路径**
   - 读 `config/server.php`，提取 `'log_file'` 对应的值（通常形如 `runtime_path() . '/logs/webman.log'`）
   - 若未找到 → 使用默认值 `<项目根绝对路径>/runtime/logs/webman.log`
   - 将解析后的绝对路径记为 `{WEBMAN_LOG_PATH}`，用于 PHPLOG.md 中 logrotate 配置
   - 同样读取 `'stdout_file'` 对应的值（通常形如 `runtime_path() . '/logs/stdout.log'`）
   - 若未找到 → 使用默认值 `<项目根绝对路径>/runtime/logs/stdout.log`
   - 将解析后的绝对路径记为 `{STDOUT_LOG_PATH}`

---

### 第二步：生成文件

#### config/log.php

- 如果标记为"已有配置，需确认覆盖"：先告知用户当前文件已有 default channel，询问是否覆盖，等用户确认后再写入；用户拒绝覆盖不影响 RequestIdMiddleware 的生成流程
- 如果标记为"新建"：直接写入

```php
<?php
declare(strict_types=1);

// 所有 channel 复用同一 formatter，避免重复配置
$defaultFormatter = [
    'class' => Monolog\Formatter\LineFormatter::class,
    'constructor' => [
        "[%datetime%] %channel%.%level_name%: %message% %context% %extra%\n",
        'Y-m-d H:i:s',
        false,
        true,
    ],
];

// 日志级别由环境变量控制：APP_DEBUG 为 true 时开 DEBUG，否则用 LOG_LEVEL，都没有则默认 WARNING。
// 生产环境在 .env 或 systemd unit 中清除 APP_DEBUG，确保不会把调试日志写到生产磁盘。
$logLevel = filter_var(getenv('APP_DEBUG'), FILTER_VALIDATE_BOOLEAN)
    ? Monolog\Level::Debug
    : Monolog\Level::fromName(getenv('LOG_LEVEL') ?: 'WARNING');

// processor 在配置加载时注册一次，运行时从 Context 动态读取当前请求的 request_id。
// 禁止在中间件里调用 pushProcessor——Webman 常驻进程下 Logger 是单例，
// 每次请求 push 会导致处理器无限叠加，内存泄漏且日志重复写入。
$requestIdProcessor = function (array $record): array {
    $record['extra']['request_id'] = \support\Context::get('request_id', '');
    return $record;
};

return [
    'default' => [
        'handlers' => [
            [
                'class' => Monolog\Handler\RotatingFileHandler::class,
                'constructor' => [
                    runtime_path() . '/logs/app.log',
                    30,                          // 保留近 30 天，写入时自动清理旧文件
                    $logLevel,
                    true,                        // bubble
                    0644,
                    true,                        // useLocking：flock 防多 worker 并发写错乱
                ],
                'formatter' => $defaultFormatter,
            ],
        ],
        'processors' => [$requestIdProcessor],
    ],
    // 业务敏感日志（支付、订单、审计）须单独 channel，不写入 default
    // 按需参照 default 结构新增：'payment' => [...], 'audit' => [...]
];
```

#### RequestIdMiddleware

仅当标记为"待生成"时写入。若多应用模式生成多份，path 对应调整 namespace。

```php
<?php
declare(strict_types=1);

namespace app\middleware;

use Webman\MiddlewareInterface;
use Webman\Http\Request;
use Webman\Http\Response;
use support\Context;

class RequestIdMiddleware implements MiddlewareInterface
{
    public function process(Request $request, callable $handler): Response
    {
        // 优先复用上游网关传入的 X-Request-Id，保持链路一致；
        // 用 ?: 而非 ?? 以同时过滤空字符串（上游可能传空值）
        $requestId = $request->header('X-Request-Id') ?: uniqid('req_', true);
        Context::set('request_id', $requestId);

        $response = $handler($request);
        $response->withHeader('X-Request-Id', $requestId);
        return $response;
    }
}
```

---

### 第三步：生成 PHPLOG.md

写入项目 `docs/PHPLOG.md`，已存在则直接覆盖。该文件是部署参考文档，**建议提交到 git 共享给团队**，后续重新生成时用 `git diff` 查看变化。

PHPLOG.md 使用**编号步骤**而非 `- [ ]` checkbox，因为此文件由 skill 覆写，勾选状态不会保留；具体部署进度由 git 状态或团队工单追踪。

PHPLOG.md 完整模板（填入探测结果）：

````markdown
# 日志配置部署清单

> 由 `/d-webman-log` 生成于 {YYYY-MM-DD HH:mm}
> Monolog 版本：{2.x / 3.x}  |  OS：{探测结果}  |  结构：{单应用 / 多应用}

本文件建议提交到 git。重新执行 `/d-webman-log` 会覆盖本文件，变更通过 git diff 审阅。

---

## 部署步骤

1. 在 `config/middleware.php` 全局注册 `RequestIdMiddleware`：
   `app\middleware\RequestIdMiddleware::class`
2. 将下方 Nginx logrotate 配置写入 `/etc/logrotate.d/nginx`（需要 sudo）
3. 将下方 **Webman 进程日志 logrotate** 配置写入 `/etc/logrotate.d/webman`（需要 sudo）
4. 将下方 Nginx log_format 加入 `nginx.conf` 的 http 块，并在 server 块引用
5. 将下方 PostgreSQL 配置加入 `postgresql.conf`，执行 `SELECT pg_reload_conf();` 生效
6. 将下方 PG 旧日志清理 cron 加入 `crontab -e`（将 `<version>` 替换为实际版本号）
7. （可选）在 `support/bootstrap/Log.php` 注册 Monolog ErrorHandler，防日志写入失败阻断业务：
   `Monolog\ErrorHandler::register(\support\Log::channel());`
8. （可选，高并发）worker 数 32+ 且 QPS 高时，改用每 worker 独立日志文件或异步写日志（推入 Redis List，独立进程消费写盘）

---

## Nginx logrotate

写入 `/etc/logrotate.d/nginx`（需要 sudo）。

**⚠️ 重要：不要在此文件里添加由 Monolog 管理的 `runtime/logs/app*.log` 等文件。**
这类文件由 `RotatingFileHandler` 自管切割，logrotate 介入会导致双重切割、句柄错乱、日志丢失。
`runtime/logs/webman.log`（Workerman 进程日志）不属于此类，单独用 `/etc/logrotate.d/webman` 处理（见下节）。

```
/var/log/nginx/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    sharedscripts
    postrotate
        nginx -s reopen 2>/dev/null || true
    endscript
}
```

---

## Webman 进程日志 logrotate

`webman.log` 和 `stdout.log` 均由 Workerman 持有文件句柄，不受 Monolog 管理，**不会自动轮转**，会无限增长：

| 文件 | 配置项 | 记录内容 |
|---|---|---|
| `webman.log` | `Worker::$logFile` / `config/server.php` `log_file` | worker 启停、PHP fatal、进程级错误 |
| `stdout.log` | `Worker::$stdoutFile` / `config/server.php` `stdout_file` | echo 输出、PHP notice/warning、未捕获的普通输出 |

**必须用 `copytruncate`**：Workerman 持有句柄且无 reopen 信号，`copytruncate` 先复制再清空，进程始终写同一 inode，不会丢日志也不会句柄错乱。

写入 `/etc/logrotate.d/webman`（路径从 `config/server.php` 中 `log_file` / `stdout_file` 取实际值）：

```
{WEBMAN_LOG_PATH}
{STDOUT_LOG_PATH} {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    copytruncate
}
```

---

## Nginx log_format

加入 `nginx.conf` 的 `http` 块（名字用 `webman` 避免与 Nginx 默认 `main` 冲突）：

```nginx
log_format webman '$remote_addr - $remote_user [$time_local] "$request" '
                  '$status $body_bytes_sent "$http_referer" '
                  '"$http_user_agent" "$http_x_request_id"';
```

在需要记录 request_id 的 `server` 块中引用：

```nginx
access_log /var/log/nginx/access.log webman;
```

---

## PostgreSQL 日志配置

加入 `postgresql.conf`：

```
log_destination = 'stderr'
logging_collector = on
log_directory = 'log'
log_filename = 'postgresql-%Y-%m-%d.log'
log_rotation_age = 1d
log_rotation_size = 0
log_min_duration_statement = 1000   # 慢查询阈值，单位 ms
```

---

## PostgreSQL 旧日志清理

加入 `crontab -e`（PG 自带切割但不删旧文件，必须外部清理）：

{根据探测结果只保留一条；无法确定时列出两条并注明}

Debian/Ubuntu：
```bash
0 2 * * * find /var/lib/postgresql/<version>/main/log/ -name "postgresql-*.log" -mtime +30 -delete
```

RHEL/AlmaLinux/Rocky/CentOS：
```bash
0 2 * * * find /var/lib/pgsql/<version>/data/log/ -name "postgresql-*.log" -mtime +30 -delete
```
````

---

### 第四步：告知用户

简短输出结果摘要：

```
✓ config/log.php 已生成（Monolog {版本}，日志级别由 APP_DEBUG / LOG_LEVEL 控制）
✓ app/middleware/RequestIdMiddleware.php 已生成
  （或："已存在且合规，跳过" / "已存在但不合规：xxx，请手动修正或删除后重新执行"）
✓ PHPLOG.md 已生成（含部署步骤和配置参考）

下一步：
  → 打开 docs/PHPLOG.md 完成手动部署步骤
  → 建议将 PHPLOG.md 提交到 git
  → 在 CHANGELOG.md 追加条目，记录本次日志体系初始化
```

---

## 注意事项

- **Monolog 3.x 为唯一支持版本**：要求 PHP 8.1+，level 常量为 enum（`Monolog\Level::Debug` 等）；项目若为 2.x 须先升级，skill 不生成 2.x 兼容代码
- **日志级别由环境变量控制**：`APP_DEBUG=true` 开 DEBUG，否则读 `LOG_LEVEL`（DEBUG/INFO/NOTICE/WARNING/ERROR/CRITICAL/ALERT/EMERGENCY），都没有则默认 WARNING
- **禁止在中间件 pushProcessor**：Webman 常驻进程，Logger 单例，每次请求 push 会内存泄漏
- **useLocking 锁竞争**：worker 数量多（32+）且 QPS 高时 flock 可能成瓶颈，届时参照 PHPLOG.md 步骤 7 的异步方案
- **Nginx log_format 命名**：使用 `webman`，避免与 Nginx 默认 `main` 冲突
- **`webman.log` 和 `stdout.log` 必须独立 logrotate + copytruncate**：两者均由 Workerman 持有句柄，无轮转机制，不处理会无限增长；无法 reopen，必须用 `copytruncate`
- **Monolog 应用日志不走 logrotate**：`runtime/logs/app*.log` 由 `RotatingFileHandler` 自管切割，外部 logrotate 介入会句柄错乱
- **PG 路径**：`<version>` 替换为实际版本号，如 `14`、`16`；不同发行版路径不同，skill 会按 OS 探测
- **CLI 脚本 / 队列任务中使用日志**：processor 依赖 Context，需手动 `Context::set('request_id', ...)` 否则字段为空
- **多应用模式**：如项目为 `app/<app-name>/` 结构，skill 会询问在哪个应用下生成中间件，或全部生成
