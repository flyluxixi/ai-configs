# Flutter 规则

适用范围：Flutter 项目。后端接口、数据库、缓存、Nginx 等规则分别由对应项目或技术栈规则声明。

## 技术栈与环境

- Flutter / Dart（以项目 `pubspec.yaml`、`pubspec.lock` 和平台目录为准）

生成代码前先读取 `pubspec.yaml`、`pubspec.lock`、目录结构和项目已有页面/组件/状态管理写法，确认 Flutter / Dart 版本、状态管理方案、路由方案和已使用插件。

## 禁止事项

- 禁止硬编码密钥、appid、appsecret、token、API base URL；按项目配置和构建环境管理
- 禁止在客户端保存完整敏感 token，除非项目已有安全存储方案并明确要求
- 禁止把密码、密钥、完整 token、验证码等敏感信息输出到日志
- 禁止在 `build()` 中发起网络请求、写本地存储、启动定时器或执行重副作用
- 禁止未释放 `TextEditingController`、`ScrollController`、`AnimationController`、`StreamSubscription`、timer 等资源
- 禁止在异步回调后不检查 `mounted` 就调用 `setState` 或使用 `context`
- 禁止长期保存 `BuildContext`、跨页面复用失效 context，或在页面销毁后继续驱动 UI
- 禁止在 UI 层直接拼接复杂业务流程、鉴权逻辑或接口协议细节
- 禁止绕过项目既有 API client、错误处理、鉴权处理和响应模型
- 禁止绕过项目既有状态管理、路由、网络层或本地存储封装
- 禁止新增第三方库处理 Flutter / Dart 标准能力或项目已有封装能解决的问题
- 禁止无说明新增状态管理库、路由库、网络库、UI 框架或插件；必须说明理由、替代方案、平台配置影响和回滚方式
- 禁止忽略 Android / iOS 权限、平台配置、签名、包名、bundle id 等发布影响
- 禁止用未约束的动态 Map 在多层之间传递核心业务数据；请求/响应模型必须类型化
- 禁止把平台目录、Gradle、Podfile、manifest、Info.plist 改成一次性本机可用状态
- 禁止提交临时调试日志、mock 数据、测试账号或本机生成的构建产物
- 禁止用全局变量保存页面状态、登录态、用户信息或请求上下文
- 禁止在 widget 中堆业务流程；复杂逻辑必须拆到 state / controller / service / repository
- 禁止 widget 参数通过过深的动态 Map 或隐式耦合对象传递
- 禁止重复实现项目已有 widget、工具函数、主题、网络封装或状态封装
- 禁止布局不考虑不同屏幕尺寸、横竖屏、键盘遮挡和安全区
- 禁止列表分页、下拉刷新、筛选、搜索出现重复请求或状态错乱

## 状态与数据流

- 异步数据必须处理 loading / error / empty / success 状态
- 用户信息、权限、登录态等状态必须考虑刷新、过期、退出登录和多端一致性

## 网络与本地存储

- 网络请求必须有超时、错误处理和可理解的用户反馈
- 本地缓存和持久化数据必须有版本、过期或清理策略
- 涉及离线缓存、重试、幂等提交时，必须说明冲突处理方式

## 平台与发布

- 新增插件前必须确认 Android / iOS 配置影响，包括权限、manifest、Info.plist、Gradle、Podfile
- 构建配置、环境变量、渠道配置按项目既有方式维护，不新增并行方案

## 文档查询

- 查询 Flutter、Dart 或第三方插件 API 时，必须优先使用 context7、官方文档、项目锁定版本文档或源码
- Flutter 文档 context7 library ID：`/websites/flutter_dev`
- Flutter API 文档 context7 library ID：`/websites/api_flutter_dev`
- Dart 文档 context7 library ID：`/websites/dart_dev`
- 查询第三方 Flutter / Dart 插件时，先按包名搜索 context7；context7 未收录时使用 pub.dev、项目锁定版本文档或源码
- 不凭记忆假设插件 API、平台行为、权限要求或发布配置
