# Nginx 规则

适用范围：Nginx 配置、反向代理、静态文件、限流、压缩、访问日志、上游缓存。

## 优先使用 Nginx 能力

遇到以下情况，必须在回复中说明为什么无法使用 Nginx 能力，不得静默绕开：

- 打算让应用层处理静态文件，而不是用 `try_files`
- 打算在业务代码里做简单限流，而不是用 `limit_req`
- 打算在业务代码里做可由 Nginx 处理的压缩、缓存或代理行为

必须优先使用的平台特性：

| 应该用 | 不该绕开 |
|---|---|
| `try_files` | 应用层处理静态文件 |
| `limit_req` | 应用层简单限流 |
| `gzip` | 应用层手动压缩响应 |
| upstream 缓存 | 业务代码重复计算可缓存响应 |

## 配置输出规范

- 给出 Nginx 配置时，提供完整配置块，不给片段
- 明确配置应放在 `http`、`server` 还是 `location` 块
- 涉及日志格式时，给出完整 `log_format` 和 `access_log` 配置
- 涉及 reload 时，说明需要先 `nginx -t` 再 reload

## 日志与运维

- Nginx 访问日志应包含 request id，便于和应用日志串联
- logrotate 配置要明确保留周期、压缩策略和 reopen 行为
- 不要把由应用日志库自管轮转的日志文件放进 Nginx logrotate 配置
