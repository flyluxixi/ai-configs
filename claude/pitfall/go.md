## 2026-05-14 - Go time.Truncate(24h) 在非 UTC 时区判断自然日会切错边界

**现象**: 用 `t.Truncate(24*time.Hour)` 判断两个时间是否属于同一自然日，在 Asia/Shanghai 部署环境下，切日边界落在本地 08:00 而非 00:00。表现为：当天 07:59 和 08:01 被认为是两天（放行两次），23:00 操作后次日 00:00-07:59 被错误拒绝。
**根因**: Go 的 `Truncate` 以 UTC 时间零点为基准截断，不感知本地时区。Asia/Shanghai 偏移 +8h，导致本地 08:00 才是 UTC 的 00:00。
**解决**: 用 `t.Date()` 比较年月日（返回值已按 t 的 Location 计算），或构造本地当天 `[startOfDay, nextStartOfDay)` 区间做范围判断。示例：`ay, am, ad := a.Date(); by, bm, bd := b.Date(); return ay==by && am==bm && ad==bd`
**标签**: go, time, timezone, truncate, asia-shanghai, 自然日

## 2026-05-15 - pgx Scan 列数与目标不匹配时静默失效，错误被忽略后结构体字段为零值

**现象**: SELECT 中新增字段后，Scan() 目标列表未同步追加，pgx 返回 scan error；
调用方用 `_` 忽略错误，结构体以零值返回，没有 panic 也没有日志，
业务逻辑基于该字段的判断全部静默失效。
**根因**: pgx 要求 SELECT 列数与 Scan() 目标数严格对应，列数不匹配直接报错；
Go 惯用的"忽略 err"写法掩盖了这一 runtime 错误。
**解决**: SELECT 每新增一列，必须同步在 Scan() 中追加对应的 `&struct.Field`；
涉及业务判断的字段（如权限、状态、开关类），读取后立即用断言或日志验证是否为预期非零值。
**标签**: go, pgx, scan, 零值陷阱, 静默失效, column mismatch

## 2026-05-17 - 多步字符串处理时正则依赖的字符被前置步骤剥光

**现象**: name 归一化函数对 `汉峪金谷互联网大厦a4-3座` 处理后剩下 `汉峪金谷互联网大厦A43座`，期望剩 `汉峪金谷互联网大厦`。
**根因**: 处理顺序"转大写 → 剥标点（含 `-`） → 剥楼栋后缀正则"。楼栋后缀正则中的 `[A-Z][0-9]+-[0-9]+(座|栋)` 依赖连字符匹配 `A4-3座` 这种格式，但 `-` 已被前一步剥光，正则永远 miss。调试时单看正则没问题、单看 trim 没问题，要联动看顺序才发现冲突。
**解决**: 多步字符串处理时，列出每个正则/规则依赖的字符集，确保它们在该步骤运行时还在。本例改为"转大写 → 剥楼栋后缀 → 剥标点"。类似易踩场景：URL 清洗（先剥协议再 split path）、HTML 文本提取（先去标签再去空白）、SQL 标识符规范化、模板渲染前的 escape 顺序。
**标签**: go, regexp, strings, 处理顺序, normalize, 静默失败

## 2026-05-20 - Gin v1.12 默认信任所有代理，c.ClientIP() 可被用户伪造

**现象**: 调用 `c.ClientIP()` 拿到的不是真实客户端 IP，而是用户在请求里自带的 `X-Forwarded-For` 头第一个值。在 IP 定位、限流、审计等依赖真实 IP 的场景，用户能让后端替任意 IP 做操作
**根因**: Gin v1.10+ 默认 `TrustedProxies` 是 `["0.0.0.0/0", "::/0"]`（trust all），`c.ClientIP()` 会从 XFF 链取最左侧 IP；nginx 用 `proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for` 默认行为是追加真实 IP，所以用户带过来的伪造 XFF 会保留在链头并被 Gin 当作客户端 IP 返回
**解决**: 在 `gin.New()` 之后显式调用 `r.SetTrustedProxies([]string{"127.0.0.1"})`（或网关的实际 IP）。这样 Gin 会从右往左在 XFF 链里找第一个非可信代理的 IP，nginx 追加的真实 IP 会被正确识别。配合 nginx 用 `proxy_set_header X-Real-IP $remote_addr` 提供独立头作为兜底
**标签**: go, gin, ClientIP, X-Forwarded-For, SetTrustedProxies, IP 伪造, 安全
