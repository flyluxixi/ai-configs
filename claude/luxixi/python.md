# Python 规则

适用范围：Python 项目通用约束。数据库、缓存、Web Server 的专项规则分别见 `postgresql.md`、`redis.md`、`nginx.md`；Web 框架（Django / FastAPI / Flask 等）专项约束按项目实际另行声明。

## 技术栈与环境

生成代码前必须先读取 `pyproject.toml`、`requirements*.txt` / `poetry.lock` / `uv.lock`、`.python-version` 或 `setup.cfg`，确认 Python 版本、依赖管理工具、已使用的框架/库和项目目录结构，不凭默认假设。

## 禁止事项

- 禁止用可变对象（`list` / `dict` / `set`）作为函数默认参数；需要默认集合时用 `None` 哨兵并在函数体内创建
- 禁止裸 `except:` 或 `except Exception` 后吞掉异常不处理；必须捕获具体异常类型并处理、记录或重新抛出
- 禁止用 `assert` 做生产环境的输入校验或安全检查；`python -O` 会移除 assert，校验必须用显式判断加抛错
- 禁止用 `print` 输出业务日志；必须使用 `logging`
- 禁止直接拼接 SQL；所有查询必须参数化绑定，涉及数据库规则同时遵守 `postgresql.md`
- 禁止对不可信输入使用 `eval` / `exec` / `pickle.loads` / `yaml.load`（须用 `yaml.safe_load`）
- 禁止 `subprocess` / `os.system` 用 `shell=True` 拼接用户输入；必须传参数列表并校验输入
- 禁止硬编码密钥、appid、appsecret、token；统一走环境变量或项目配置规范
- 禁止在日志中输出密码、密钥、完整 token、验证码等敏感信息
- 禁止用全局可变变量保存请求级状态、当前用户、trace id、租户 id 等上下文
- 禁止外部 HTTP / 网络调用不设置超时（`requests` / `httpx` 等必须显式 `timeout`）
- 禁止在 `async` 协程中调用阻塞式同步 IO（同步 DB 驱动、`time.sleep`、阻塞文件/网络）；必须用异步库或 `run_in_executor`
- 禁止在循环中逐条执行本可批量完成的 DB / IO 操作；改用批量查询、批量写入或向量化处理
- 禁止 `from module import *`
- 禁止打开文本文件不指定编码；必须显式传 `encoding`，项目自有文本文件默认 `utf-8`，外部输入按协议、元数据、用户声明或检测结果确定编码，并明确 `errors` 错误处理策略
- 禁止手动拼接路径字符串处理跨平台路径；必须用 `pathlib` 或 `os.path`
- 禁止忽略函数返回的错误状态或丢弃需要处理的返回值
- 禁止无说明新增第三方依赖；必须说明理由、替代方案、运行影响和回滚方式
- 禁止新增第三方包处理标准库或项目已有封装可稳定解决的问题
- 禁止全局直接执行有副作用的代码；可执行逻辑放入 `if __name__ == "__main__":` 或显式入口函数

## 必须事项

- 必须使用虚拟环境（venv / poetry / uv 等，以项目既有工具为准）隔离依赖，不污染系统 Python
- 必须约束依赖版本，不提交无上限的浮动版本：应用 / 服务必须提交 lock 文件或固定部署依赖；可复用库必须声明合理的兼容版本范围，避免无上限或过窄 pin
- 公共函数、方法签名和模块级变量必须有类型注解
- 必须用项目既有 formatter / linter（black / ruff / isort 等）的规则，不自创风格
- 文件、socket、锁、数据库连接、事务等资源必须用 `with` 上下文管理器或等价机制确保释放
- 异常必须区分类型并定义可判断的业务异常类，禁止只靠异常信息字符串匹配判断
- 涉及金额或状态变更的操作必须有幂等性保护
- 所有用户输入必须验证和过滤，输出到 HTML 的内容必须转义
- 时间处理必须使用带时区的 `datetime`（aware），禁止用 naive datetime 表示绝对时间点
- 后台任务 / 异步任务必须定义幂等 key、重试策略、超时和失败处理
- 修改公共函数、类、接口签名时必须同步检查调用方和测试覆盖

## 文档查询

- 查询 Python 标准库时使用 `docs.python.org` 当前版本文档或本机源码
- 查询第三方库 API、配置或版本迁移时，必须先使用 context7、官方文档或项目锁定版本，不凭记忆假设
