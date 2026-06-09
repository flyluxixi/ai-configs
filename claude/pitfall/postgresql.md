## 2026-06-09 - PostgreSQL CHECK 约束下跨枚举值迁移必须先 DROP 约束再 UPDATE 数据

**现象**: 在事务内对带 CHECK 约束的字段做"跨枚举值迁移"（旧 IN(1,2,3) → 新 IN(0,1,9)），按"UPDATE 数据 → ALTER 约束"顺序执行时，UPDATE 阶段立即报错 `new row for relation "<table>" violates check constraint "<table>_<col>_check"`，整事务回滚。具体复现：`BEGIN; UPDATE city_opening SET status=9 WHERE status=2;` 报错——旧 CHECK 仍是 `IN (1,2,3)`，9 不在集合内被行级立即拒绝。

**根因**: PostgreSQL CHECK 约束是**行级立即检查**，不是延迟到事务尾的；UPDATE 阶段每行新值就被校验。约束变更（DROP / ADD）必须在数据变更之前完成，否则违反旧约束的新值连 UPDATE 都做不到。常见的"先改数据再改约束"思路只适用于"新值仍落在旧 CHECK 集合内"的子集场景，跨集合迁移不适用。

**解决**: 在同一事务内重排顺序——先 DROP 旧约束，再 UPDATE 数据，再 ADD 新约束：

```sql
BEGIN;
ALTER TABLE city_opening DROP CONSTRAINT city_opening_status_check;
UPDATE city_opening SET status = 9 WHERE status = 2;
UPDATE city_opening SET status = 0 WHERE status = 3;
ALTER TABLE city_opening ADD CONSTRAINT city_opening_status_check CHECK (status IN (0, 1, 9));
COMMENT ON COLUMN city_opening.status IS '0=已暂停 1=即将开通 9=已开通';
COMMIT;
```

无约束窗口完全卡在事务内，事务外可见性零，无并发风险。DROP + ADD CHECK 在事务内是原子的，失败可整体回滚。

**标签**: postgresql, check-constraint, enum-migration, schema-migration, alter-table, transaction-ordering
