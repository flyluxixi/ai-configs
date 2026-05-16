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
