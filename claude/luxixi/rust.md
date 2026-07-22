# Rust 规则

适用范围：Rust 项目。数据库、缓存专项规则分别见 `postgresql.md`、`redis.md`。

## 技术栈与环境

- Rust 版本与 edition 以项目 `Cargo.toml`、`rust-toolchain.toml` 声明为准

生成代码前先读取 `Cargo.toml`、`Cargo.lock` 和项目入口文件，确认 edition、async 运行时（tokio 等）、错误处理选型和项目目录结构。

## 禁止事项

- 禁止在可失败的业务路径使用 `unwrap()` / `expect()`；错误必须用 `Result` + `?` 传播。仅测试代码或不变量确定成立处允许，且 `expect` 信息必须写明该不变量
- 禁止用 `panic!` 表达业务失败；panic 只用于不可恢复的程序缺陷
- 禁止把字符串当错误类型到处传；错误类型必须可判别（可 match），错误处理跟随项目既有选型，不引入第二套方案
- 禁止为绕过借用检查随手 `clone()`；先考虑借用、生命周期或结构调整，确需 clone 时说明代价
- 禁止无理由的 `unsafe`；确需时块尽量小，并用 `// SAFETY:` 注释写明依赖的安全不变量
- 禁止用 `as` 做可能有损的数值转换；用 `try_into` 或显式处理溢出与截断
- 禁止提交带编译警告的代码；clippy 警告必须处理，确需保留时逐条 `#[allow]` 并说明理由
- 禁止硬编码密钥、appid、appsecret、token；统一走环境变量或项目配置规范
- 禁止无说明新增 crate；必须说明理由、维护状态和替代方案，标准库能稳定解决的问题不引入第三方 crate

## async 与并发

- async 运行时以 `Cargo.toml` 为准，禁止在同一项目混用多个运行时
- 禁止在 async 函数中执行阻塞操作（std 阻塞 IO、`std::thread::sleep`、长时间计算）；用运行时的异步等价物或 spawn_blocking 类机制
- 禁止跨 `.await` 持有同步锁（std `MutexGuard`）；跨 await 的共享状态用异步锁或消息传递
- spawn 出去的任务禁止静默丢弃错误；`JoinHandle` 结果必须处理或明确说明可忽略
- channel 优先有界；使用无界 channel 必须说明内存增长边界

## 编码规范

- 遵循 rustfmt 默认风格，提交前通过 `cargo fmt`
- 公开 API（`pub` 项）必须有文档注释；非公开代码不写复述代码含义的注释
- 模块与文件组织跟随项目既有结构，不自行另起风格
- 类型能表达的约束不留给运行时检查：用 newtype、穷举枚举替代魔法值和布尔标志位

## 文档查询

- Rust 语言参考 context7 library ID：`/rust-lang/reference`
- 标准库与第三方 crate API 以 `docs.rs` 对应版本文档为准，crate 版本以项目 `Cargo.lock` 锁定为准
- 不凭记忆假设 crate API、feature flag 或版本间行为差异
