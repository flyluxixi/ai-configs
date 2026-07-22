# SQLite 踩坑记录

## 2026-06-05 - 监控 SQLite WAL 是否被写入要靠 mtime 不能靠 size

**现象**: 轮询 SQLite 的 -wal 文件检测"有没有新写入"，发现 size 一直不变，误判"没变化"，漏掉所有写入事件。
**根因**: SQLite WAL 文件预分配固定大小（如几 MB）、原地循环覆盖写；新数据写进去不改 size，只更新 mtime。靠 size diff 判断变化必然全漏。
**解决**: 用文件 mtime 判断 WAL 是否被写入，不用 size。记录上次 mtime，变化即有写入。注意 mtime 在不同文件系统的精度，必要时结合内容哈希。
**标签**: sqlite, wal, mtime, size, 文件监控, 变化检测, 预分配, 原地写

## 2026-06-05 - SQLite 列 schema 标 TEXT 实存 protobuf 二进制，sqlite3 默认 UTF-8 解码 SELECT 崩溃

**现象**: 读某些 SQLite 库（如微信解密库）`SELECT *` 时抛 `sqlite3.OperationalError: Could not decode to UTF-8 column 'xxx'`，但该列 schema 明明声明为 TEXT。
**根因**: 某些应用（微信等）在 schema 标 TEXT 的列里实际存 protobuf/二进制（常见命名 `*_buf_` / `extra_buffer` / `ext_buffer`）。Python sqlite3 默认 `text_factory=str`，对 TEXT 列一律按 UTF-8 解码，撞到二进制即崩；`SELECT *` 把这些列也取出来就触发。
**解决**: ① 容错解码：`con.text_factory = lambda b: b.decode('utf-8', 'replace')`；② 或 SELECT 只取明文列、避开 `*_buf_`/`extra_buffer` 等二进制列；③ 需要二进制内容时按 BLOB 取出（`con.text_factory = bytes` 或单独取该列）再按 protobuf 解析。
**标签**: sqlite, sqlite3, python, text_factory, protobuf, utf-8, 二进制列, blob, could-not-decode, 微信数据库
