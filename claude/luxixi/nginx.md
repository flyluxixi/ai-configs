# Nginx 规则

适用范围：Nginx 配置、反向代理、静态文件、限流、压缩、访问日志、上游缓存、TLS、WebSocket 和发布切换。

生成或修改配置前先读取现有 `nginx.conf`、站点配置、upstream、日志格式、证书路径、部署方式和应用监听端口，确认配置所属层级与线上影响。

## 优先使用 Nginx 能力

遇到以下情况，必须在回复中说明为什么无法使用 Nginx 能力，不得静默绕开：

- 打算让应用层处理静态文件，而不是用 `try_files`
- 打算在业务代码里做简单限流，而不是用 `limit_req`
- 打算在业务代码里做可由 Nginx 处理的压缩、缓存或代理行为
- 打算让应用暴露真实文件路径或内部服务地址，而不是通过 Nginx 控制访问边界
- 打算在应用层处理简单跨域、缓存头、上传体大小等网关层策略

必须优先使用的平台特性：

- `try_files`、`limit_req`、`gzip`、upstream 缓存、`proxy_set_header`、`client_max_body_size`

## 禁止事项

- 禁止直接改线上配置后 reload；必须先 `nginx -t`，确认无误再 reload
- 禁止把私钥、证书、鉴权 token、内网地址、管理后台路径等敏感信息写入公开仓库
- 禁止使用过宽的 `location /` 吞掉静态资源、API、管理后台或回调路径的差异
- 禁止暴露 `.git`、`.env`、备份文件、上传临时目录、内部管理端口或调试端口
- 禁止 `proxy_pass` 后不设置必要的 `Host`、`X-Real-IP`、`X-Forwarded-For`、`X-Forwarded-Proto`
- 禁止反向代理无超时配置；必须明确连接、读、写超时
- 禁止未限制上传体大小、请求速率或连接数就开放高风险接口
- 禁止把所有 4xx / 5xx 都转成 200 或隐藏真实失败语义
- 禁止为了解决跨域问题直接放开任意 origin、任意 header、任意 method
- 禁止缓存带用户身份、权限、购物车、订单、支付状态等私有响应
- 禁止忽略 WebSocket、SSE、长轮询等长连接对 header、超时和 buffer 的要求
- 禁止在不了解作用域和匹配优先级时使用 `alias`、`rewrite`、`if` 或正则 `location`
- 禁止关闭 TLS 校验、使用过期证书或把 HTTP 临时方案当作长期配置
- 禁止配置变更没有回滚方式；涉及线上站点必须说明影响范围和恢复方案

## 配置输出规范

- 给出 Nginx 配置时，提供完整配置块，不给片段
- 明确配置应放在 `http`、`server` 还是 `location` 块
- 涉及日志格式时，给出完整 `log_format` 和 `access_log` 配置
- 涉及 reload 时，说明需要先 `nginx -t` 再 reload
- 涉及新增域名、证书、端口、upstream、缓存目录时，说明依赖的文件路径、权限和目录创建要求
- 涉及线上切换时，说明验证命令、回滚方式和需要观察的日志

## 反向代理与上游

- upstream 名称、端口、协议和应用监听地址必须与实际部署一致
- 代理到应用时必须保留真实请求信息，避免应用拿不到 scheme、host、client ip
- WebSocket / SSE / 长轮询必须显式处理 `Upgrade`、`Connection`、超时和 buffer

## 静态资源与缓存

- 静态文件优先由 Nginx 提供，使用 `try_files` 控制 fallback
- SPA fallback 必须限定在前端路由范围内，不能吞掉 API 404
- 缓存策略区分 HTML、静态 hash 资源、接口响应和下载文件
- 带用户态或权限的数据默认不缓存；确需缓存时必须说明 cache key 和失效策略

## TLS 与安全头

- HTTPS 站点必须说明证书路径、续期方式和 reload 策略
- HTTP 到 HTTPS 跳转应明确状态码和域名范围
- 安全响应头按项目需要配置，避免盲目添加导致 iframe、下载、跨域或第三方登录异常
- CORS 配置必须按明确域名白名单，不使用无边界的通配策略

## 日志与运维

- Nginx 访问日志应包含 request id，便于和应用日志串联
- logrotate 配置要明确保留周期、压缩策略和 reopen 行为
- 不要把由应用日志库自管轮转的日志文件放进 Nginx logrotate 配置
- 错误日志级别按排障需要调整，不长期保留 debug 级别
- 发布后至少观察访问日志、错误日志、upstream 响应时间、4xx / 5xx 比例

## 文档查询

- 查询 Nginx 指令、模块、变量、TLS、缓存、限流、日志格式时，优先使用 Nginx 官方文档或当前安装版本文档
- 不凭记忆假设指令作用域、默认值、版本兼容性或 reload 行为
