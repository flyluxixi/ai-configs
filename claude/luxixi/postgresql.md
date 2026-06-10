# PostgreSQL 规则

适用范围：PostgreSQL schema、迁移、查询、索引、事务、性能排查，以及业务代码中生成或调用 PostgreSQL 查询的场景。

## PostgreSQL 平台能力

必须优先使用以下平台特性，不得静默绕开：

| 应该用 | 不该绕开 |
|---|---|
| CTE | 应用层多轮拼装中间结果 |
| 窗口函数 | 应用层手动排名、分组计数 |
| JSONB | 字符串存 JSON 后应用层解析 |
| upsert（`ON CONFLICT`） | 先查再插导致竞态 |
| 全文搜索 | 应用层模糊过滤 |
| 事务 | 多表写入靠应用层补偿 |

## 禁止事项

- 禁止字符串拼接 SQL；所有查询必须参数绑定
- 禁止按单条记录循环执行查询或写入；改用批量查询、`IN`、JOIN、CTE、窗口函数、批量写入或 upsert。数据迁移允许按批次循环执行，但必须有批次上限、进度边界和失败后可恢复方案
- 禁止先查再插实现唯一写入；必须使用唯一约束 + `ON CONFLICT`
- 禁止在应用层分页、聚合、排序或去重；必须让 SQL 一次返回结果
- 禁止用多次查询组装数据；必须使用 CTE / 窗口函数一次返回
- 禁止无事务地执行多表一致性写入、金额变更、库存扣减、状态流转等操作
- 禁止在事务内执行 HTTP、Redis、文件 IO 等不可控外部调用
- 禁止迁移脚本不可重复执行；迁移必须幂等或由迁移框架保证只执行一次
- 禁止无索引地对大表做模糊查询、排序、过滤或 JOIN
- 禁止为了"可能会用到"盲目加索引；新增索引必须对应明确查询
- 禁止新增重复索引；禁止无查询依据地单独新增低选择性索引，低选择性字段建索引必须说明组合方式、过滤条件或执行计划收益
- 禁止忽略慢查询、锁等待、执行计划异常或表膨胀问题
- 禁止使用 `SELECT *`；查询字段必须明确列出
- 禁止应用层逐条查询可批量读取的数据；必须使用集合查询
- 禁止大偏移分页不评估 keyset pagination
- 禁止软删除逻辑不一致或长期不清理孤儿记录

## 类型选型与建模

- 禁止使用数据库 ENUM 类型；改用 SMALLINT + CHECK（理由：ENUM 增删值需 `ALTER TYPE`、无法删除已有值、取值顺序固定难调整、跨库迁移困难）
- 类型选择按数据本质：永远只有"是/否"的字段（含 NULL=未知）用 **BOOLEAN**；真枚举（≥3 个值或业务上可能扩到 ≥3 档）用 SMALLINT + CHECK 约束限制取值范围。不要为了"将来可能扩档"先把布尔伪装成 SMALLINT 0/1——BOOLEAN 占 1 字节比 SMALLINT 2 字节更紧凑，未来真要扩档时改类型也是常规迁移
- 金额、价格、精确小数必须精确表示，禁止用 `FLOAT` / `DOUBLE PRECISION` / `REAL`——二进制浮点无法精确表示十进制小数，会导致对账偏移和累计误差。两种合法方案任选其一并在项目内统一：
  - `NUMERIC` / `DECIMAL` 存原始单位（推荐默认，语义直观、SQL 内可控舍入、天然支持多币种与高精度）
  - `BIGINT` 存最小货币单位（如分），须全栈文档化单位、显式定义除法 / 分摊的舍入策略；多币种场景须按币种处理最小单位（日元乘 1、第纳尔乘 1000）
- 汇率、需要 4 位以上小数的单价一律用 `NUMERIC`，不用整数缩放（整数缩放对高精度小数要乘 `10^n`，单位约定易错）
- 变长字符串按是否有明确长度上限选型：业务上有明确且相对稳定的长度上限（手机号、身份证号、固定位编码、`name` / `title` 等）→ 用 `VARCHAR(n)`，让 schema 直接自文档化业务约束；无明确上限（正文、备注、富文本、外部不可控来源）→ 用 `TEXT`。不要为了"统一"把所有列都改成 `TEXT + CHECK (char_length(col) <= N)`。前提事实：PG 里 `TEXT` 与 `VARCHAR(n)` 底层同一种存储、读写性能完全相同（与 MySQL 不同，`VARCHAR(n)` 不更快也不更省），所以选型只看可维护性与可读性——有稳定上限时 `VARCHAR(n)` 的自文档化优于额外写一条 CHECK。唯一 `TEXT + CHECK` 真正占优的场景是长度上限会反复**缩小**：`ALTER ... TYPE VARCHAR(n)` 缩小 `n` 要全表重写并长持 `ACCESS EXCLUSIVE` 锁，而调整 CHECK 可用 `DROP CONSTRAINT` + `ADD CONSTRAINT ... NOT VALID` + `VALIDATE CONSTRAINT`（`VALIDATE` 仅持 `SHARE UPDATE EXCLUSIVE`，不阻塞读写）避免长锁；**放宽**上限或 `VARCHAR(n)` ↔ `TEXT` 互转是 binary coercible，两种方式都只动元数据、不重写表，无差异
- `CHECK` 约束的纳入判据是**约束的变更频率 + 误伤代价**，不是「格式 vs 业务」这条伪分界（很多看似"格式"的规则其实含业务假设）。只放变更频率极低、误伤代价极小的约束：长度（`char_length(col) = 11`）、字符集 / 纯数字（`col ~ '^\d+$'`）、大小写、非空非空白等真正中立的格式兜底；不放随业务 / 监管高频变化、误伤即线上事故的取值规则（手机号段 `^1[3-9]\d{9}$`、行政区划码、银行卡 BIN、邮箱域名白名单等）。原因：高频取值规则固化进 `CHECK` 每次变更都要 `DROP/ADD CONSTRAINT` 迁移且历史数据可能卡 `VALIDATE`；严格约束误伤合法新值 = 注册 / 下单直接失败的线上事故，代价远高于「格式合法但取值存疑」放进库后由应用层再拦一道。这类高频严格校验放应用层（可配置、可热更新、可随监管同步），数据库这层宁松勿误伤。判据按稳定性分级，不按"格式还是业务"：手机号兜底用 `mobile ~ '^1\d{10}$'`（"1 开头 11 位"也是弱业务假设，但几十年不变、误伤风险极小，可入 `CHECK`），而第二位号段 `[3-9]` 受携号转网 / 虚商扩号段 / 新放号段高频冲击，必须排除——同属号码约束，分界只在变更频率，不在它是不是"纯格式"
- 禁止用单一 `xxx_at TIMESTAMPTZ` 字段表达可变 / 可撤销 / 多阶段状态；订单的 `paid` / `shipped` / `cancelled` / `refunded`、审核的 `approved` / `rejected`、任何会回退或有部分完成态的流程，必须用 `SMALLINT + CHECK 约束` 状态机字段表达当前状态，并按需配套 `xxx_at TIMESTAMPTZ` 审计时间字段
- 只有业务规则明确禁止反向操作的事件（如事务 `committed`、法律意义上 `signed`）才允许用 `xxx_at TIMESTAMPTZ NULL` 表达"是否+何时"；`published` / `archived` / `deleted` 默认视为可撤销（可下架、可恢复、软删除可恢复），除非迁移说明写明不可撤销依据，否则必须用状态字段表达
- 禁止使用 `is_xxx` / `has_xxx` / `can_xxx` / `include_xxx` 布尔字段表达上述状态规则约束的状态语义；这类字段必须按上述状态规则改用状态机字段或 `xxx_at TIMESTAMPTZ`
- 二元状态用布尔还是状态机的判据：同时满足"无需审计状态变更时间"且"业务上永远只有两态"才用布尔（如 `is_active` / `is_public`，不关心何时激活、不会衍生第三态）；只要需要记录状态变更时间（`xxx_at`）或可能扩出中间态（`draft` / `scheduled` / `archived` 等），即使当前只有两态也必须用 `SMALLINT + CHECK` 状态机（如 `published` 通常配 `published_at` 且可能衍生草稿态 → 用 `status`，而非 `is_published`）。判据只看业务本质（是否需审计时间 + 是否多态），不看字段名是否含"发布 / 公开 / 上线"语义——同是"公开发布"含义，两态且不记时间的用布尔（`is_public`），需 `published_at` 或会长草稿 / 定时态的用 `status`

## 命名规范

- 表名、字段名、索引名、约束名必须统一使用 snake_case；禁止使用 camelCase 或 PascalCase
- 主键字段必须命名为 `id`
- 外键字段必须命名为 `{被引用表单数形式}_id`；禁止使用其他格式
- 普通索引必须命名为 `idx_{表名}_{字段名}`，多字段以下划线拼接；禁止随意命名索引
- 唯一索引必须命名为 `uk_{表名}_{字段名}`；禁止随意命名唯一索引（历史遗留的 `uniq_` 前缀视为合规，不主动重命名；新建索引一律用 `uk_`，需重命名时必须提供完整迁移计划）
- 布尔类型字段必须用语义前缀，按"动作 vs 拥有 vs 属性 vs 包含"分四种选其一（**统一的是语义规则，不是统一前缀**）。这是有意识的 trade-off：前缀本身是规则的一部分，牺牲少量英文里更自然的纯形容词写法（如 `available` / `archived`）换取浏览 schema 时一眼看出字段语义类别和机械可校验性，不接受"`active` 比 `is_active` 更自然"这类反例：
  - `is_` 静态属性 / 当前状态："这个**是不是** X"（`is_default` / `is_active` / `is_public`）
  - `has_` 拥有 / 具备："**有没有** X"（可数实体；`has_avatar` / `has_central_ac` / `has_rent_free`）
  - `can_` 能力 / 许可："**允不允许** X"（动作动词；`can_register_company` / `can_split` / `can_invoice`）；动作动词优先用 `can_xxx`，形容词 / 名词态归 `is_xxxable` 或 `is_xxx`（"是否允许开发票" → `can_invoice` ✅；"是否可开票" → `is_invoiceable` 亦可）
  - `include_` 包含 / 打包："**包不包含** X"（X 是子项；`include_property_fee` / `include_tax`）

  禁止使用 `allow_` / `enable_` 等其他前缀（与 `can_` 同义重复）；禁止使用无语义前缀的布尔字段名
- 布尔字段仅用于布尔语义场景（静态属性 / 拥有 / 许可 / 包含）；布尔 vs 状态机 vs `xxx_at` 事件时间戳的完整判据以「类型选型与建模」中的状态规则条目为准，此处不重复展开，两处表述如有出入以「类型选型与建模」为准
- 状态字段命名：表只有单一主生命周期时用 `status`；表内存在多个独立状态域（如订单的支付 / 履约 / 退款 / 审核）时必须用业务域限定名（如 `payment_status` / `shipment_status` / `refund_status` / `review_status`），这类业务域限定名不受"字段名重复所在表名"约束
- 禁止字段名长度超过 30 字符；接近上限（> 25 字符）必须先穷举优化手段：① 字段名是否重复了表名 ② 是否能用允许的缩写 ③ 是否可拆分为多个字段 ④ 字段是否放错了表。穷举后仍超过 30 字符的，才允许在迁移说明中写明业务必要性
- 禁止布尔字段名包含超过 2 段业务词；剔除 `is_` / `has_` / `can_` / `include_` 前缀后按下划线分段计数（反例：`is_deal_cooperation_committed` 剔除前缀后为 `deal / cooperation / committed` 共 3 段）
- 禁止自创字段名缩写；允许的缩写白名单按类别列出，业务词（如 `addr` / `amt` / `qty` / `desc` / `info` / `num`）一律写全：
  - 标识：`id` / `uuid` / `sku`
  - 网络：`url` / `uri` / `ip` / `cidr` / `mac` / `dns`
  - 协议：`http` / `https` / `tcp` / `udp` / `ssh` / `ftp` / `smtp`
  - 数据格式：`json` / `xml` / `csv` / `yaml` / `html`
  - 认证：`jwt` / `oauth` / `otp` / `mfa` / `sso`
  - 时间：`utc` / `tz` / `ttl`
  - 行业：`sql` / `api` / `iso` / `cdn`

  白名单中的缩写仅允许作为完整字段名的一部分，不允许单独作为字段名（例：`mfa_enabled_at` ✅、`jwt_expires_at` ✅、`mfa` 单独作字段名 ❌）；认证凭证 / 密钥 / token 内容不得因缩写白名单的存在而直接落入普通业务字段，应按密钥管理规范单独建模
- 时间戳字段必须命名为 `created_at`、`updated_at`，软删除时间戳必须命名为 `deleted_at`；所有时间戳列类型必须为 `TIMESTAMPTZ`，禁止使用无时区的 `TIMESTAMP`（无时区类型不记录偏移，跨时区写入 / 读取产生歧义）
- 禁止使用 PostgreSQL 关键字或高冲突通用词作为表名或字段名（如 `user`、`order`、`type`、`value`）；是否属于保留字必须以项目锁定 PostgreSQL 版本的官方关键字表为准
- 禁止同一数据库内混用不同命名风格

## 事务规范

- 多表写入、金额、库存、状态流转、幂等记录写入必须有明确事务边界
- 事务内只放数据库一致性相关操作，禁止长事务
- 事务失败必须回滚，不能留下半写状态
- 并发更新同一业务对象时，必须说明使用的并发控制方式（唯一约束、行锁、乐观锁、upsert 等）
- 使用行锁时必须说明锁定范围，禁止扩大锁粒度

## 索引规范

- 查询条件、JOIN key、排序字段、唯一性约束必须评估是否需要索引
- 新增索引必须说明服务的查询或约束
- 大表新增索引必须考虑锁表和线上写入影响，必要时使用 `CREATE INDEX CONCURRENTLY`
- 使用 `CREATE INDEX CONCURRENTLY` 时必须确认迁移框架不会把该语句包在事务块内；若迁移框架默认启用事务，必须关闭该迁移事务或拆分为独立迁移，并检查失败后残留的 `INVALID` 索引
- 分区表新增索引不得假设可直接在父表上并发创建；必须按项目锁定 PostgreSQL 版本确认支持方式，必要时逐分区并发创建后再附加到父索引
- JSONB 查询必须评估合适的 GIN / 表达式索引

## 性能诊断

- SQL 性能问题必须先看 `EXPLAIN (ANALYZE, BUFFERS)`，不凭感觉改 SQL 或加索引
- 必须关注是否出现不合理顺序扫描、排序、临时文件、回表、Nested Loop、Hash Join 或锁等待
- 优化前必须确认数据量级、选择性、现有索引和实际查询参数
- ORM / QueryBuilder 生成的 SQL 必须按真实 SQL 审查

### 常用诊断查询

```sql
-- 找未建索引的外键（检查完整前缀，支持复合 FK）
-- 注意：要求索引前缀与 FK 列顺序完全一致；列顺序不同但同样可用的复合索引会被误报为缺索引，结果需人工复核
SELECT c.conrelid::regclass AS table_name,
       c.conname AS fk_name,
       array_to_string(ARRAY(
         SELECT a.attname FROM pg_attribute a
         WHERE a.attrelid = c.conrelid AND a.attnum = ANY(c.conkey)
         ORDER BY array_position(c.conkey, a.attnum)
       ), ', ') AS fk_columns
FROM pg_constraint c
WHERE c.contype = 'f'
  AND NOT EXISTS (
    SELECT 1 FROM pg_index i
    WHERE i.indrelid = c.conrelid
      AND i.indpred IS NULL
      AND (i.indkey::int2[])[1:array_length(c.conkey,1)] = c.conkey
  );

-- 慢查询（需启用 pg_stat_statements 扩展）
SELECT query, mean_exec_time, calls
FROM pg_stat_statements
WHERE mean_exec_time > 100
ORDER BY mean_exec_time DESC;

-- 死元组积压检查（不能单独等同于表膨胀）
SELECT relname, n_dead_tup, last_vacuum
FROM pg_stat_user_tables
WHERE n_dead_tup > 1000
ORDER BY n_dead_tup DESC;
```

## 迁移与数据维护

- schema 迁移必须可审查、可回滚或有明确补救方案
- 数据迁移必须分批执行，禁止长事务和大表长时间锁定
- 新增约束前必须确认历史数据满足约束
- 删除字段、表或索引前必须确认调用方和历史任务不再依赖

## 文档查询

- PostgreSQL 通用文档 context7 library ID：`/websites/postgresql`
- 项目锁定 PostgreSQL 主版本时，优先使用对应版本文档；context7 搜索到的版本 ID 包括 `/websites/postgresql_14`、`/websites/postgresql_16`、`/websites/postgresql_17`、`/websites/postgresql_18`
- 查询 PostgreSQL 特性、函数、索引类型、锁机制或迁移方案时，必须使用 PostgreSQL 官方文档或项目锁定版本文档
- 不凭记忆假设 PostgreSQL 版本特性、函数行为或锁语义
