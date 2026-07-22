# SQLite 规则

适用范围：嵌入式 / 本地工具场景使用 SQLite，以及读取第三方应用的 SQLite 库文件。服务端主数据库规则见 `postgresql.md`，不在本文件范围。

## 使用边界

- SQLite 适用于单机、低并发写、嵌入式与本地工具场景；多实例共享写、高并发写场景必须改用 PostgreSQL 并说明理由
- 禁止把 SQLite 库文件放在网络文件系统（NFS / SMB）上多进程共享；文件锁在网络文件系统上不可靠

## 并发与事务

- 写入方开启 WAL 模式（`PRAGMA journal_mode=WAL`）提升读写并发，除非场景明确单进程独占
- 连接必须设置 busy_timeout，禁止遇锁即抛错
- 批量写入必须包在显式事务里，禁止逐条自动提交
- 外键约束默认关闭；依赖外键时每个连接执行 `PRAGMA foreign_keys=ON`

## 类型与数据

- SQLite 列类型是类型亲和（type affinity）不是强制约束；禁止假设列内容与 schema 声明类型一致
- 读第三方应用库（如微信）时，schema 标 TEXT 的列可能实存 protobuf / 二进制（常见命名 `*_buf_`、`extra_buffer`）；Python sqlite3 需容错解码（`text_factory`）或按 BLOB 取出，禁止对未知 schema 直接 `SELECT *`

## 文件与运维

- 监控 SQLite 是否有新写入用 `-wal` 文件的 mtime，禁止用 size：WAL 默认在约 1000 页（4MB）触发 checkpoint 后从头覆盖复用，size 通常停在高水位不再变化，写入只更新 mtime
- 长驻读连接场景警惕 checkpoint 饥饿：并发读事务不断档会让 checkpoint 无法完成、WAL 文件无限增长；必须留出读间隙、设置 `PRAGMA journal_size_limit` 或手动 checkpoint 收敛
- 对正在被写入的库禁止直接 `cp` 主文件备份——`-wal` / `-shm` 未落盘会拿到不一致快照；备份用 backup API 或 `VACUUM INTO`
- `-wal`、`-shm` 文件必须与主库文件一起迁移 / 删除，禁止单独清理

## 文档查询

- SQLite 文档 context7 library ID：`/websites/devdocs_io_sqlite`（官方文档镜像）
- 查询 PRAGMA、锁行为、WAL 细节、类型与日期函数时，必须先用 context7 或 sqlite.org 官方文档确认，不凭记忆假设
