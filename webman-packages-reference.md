# Webman 项目常用包参考

> 备忘用途。按需复制对应章节补充到项目级 CLAUDE.md 的「依赖约定」部分。

---

## 依赖约定

| 用途 | 包 | 说明 |
|---|---|---|
| Web 框架 | `workerman/webman-framework ^1.5` | 正确包名，非 `webman/framework`（不存在） |
| 日志 | `monolog/monolog ^3.0` | Webman 日志底层依赖，执行 `/d-webman-log` 前确认已安装；2.x 与 3.x API 有差异 |
| ORM / Query Builder | `illuminate/database ^10` | Eloquent + Query Builder，`db()` 辅助函数即为此包 |
| Redis | `illuminate/redis ^10` + `phpredis` 扩展 | 连接池 + Pipeline + Lua，底层用 phpredis 扩展；不用 `predis/predis`（纯 PHP，性能差） |
| HTTP Client | `guzzlehttp/guzzle ^7.8` | 所有外部 HTTP 调用统一用 Guzzle；Client 实例在 bootstrap 注册为单例，禁止请求内 new |
| 参数验证 | `illuminate/validation ^10` | Controller 入口请求参数校验，同 Laravel 生态 |
| 支付 | `yansongda/pay ^3.0` | 微信支付 V2/V3、支付宝、银联；所有密钥走环境变量 |
| 队列（轻量） | `webman/redis-queue ^1.0` | 简单异步任务，API 简洁 |
| 队列（完整） | `illuminate/queue ^10` | 延迟任务、失败重试、死信队列，适合复杂业务 |
| 定时任务 | `workerman/crontab ^1.0` | 后台进程定时器 |

引入新包前必须说明理由，确认后再写入 `composer.json`。

---

## 各包关键约束

**日志（monolog）**
- 禁止在中间件 `pushProcessor`，Webman 常驻进程 Logger 是单例，每次请求 push 导致内存泄漏
- 日志级别由 `APP_DEBUG` / `LOG_LEVEL` 环境变量控制

**Redis（illuminate/redis）**
- 计数/限流用 `INCR/DECR`，加锁用 `SETNX`，批量操作用 Pipeline
- 禁止 PHP 层手动循环 get/set

**HTTP Client（guzzle）**
- 必须设置超时：`connect_timeout=3, timeout=10`（按接口实际调整）
- 所有外部调用必须有异常捕获和重试策略

**支付（yansongda/pay）**
- appid、appsecret、密钥全部走环境变量，禁止硬编码
- 涉及金额的接口必须有幂等性保护

**队列**
- 所有任务必须有唯一业务 key 保证幂等性
- 必须配置死信队列和最大重试次数，不能静默丢弃失败任务
- 建议退避策略：指数退避，最大重试 3 次
