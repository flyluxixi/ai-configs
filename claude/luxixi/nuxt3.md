# Nuxt 3 规则

适用范围：Nuxt 3 项目。后端接口、数据库、缓存、Nginx 等规则分别由对应项目或技术栈规则声明。

## 技术栈与环境

- Nuxt 3（以项目 `package.json`、lockfile 和 `nuxt.config.*` 为准）

生成代码前先读取 `package.json`、lockfile、`nuxt.config.*`、目录结构和项目已有页面/组件写法，确认 Nuxt 版本、渲染模式、包管理器和已使用模块。

## Nuxt 平台能力

遇到以下情况，必须在回复中说明为什么无法使用 Nuxt / Vue / Nitro 既有能力，不得静默绕开：

- 打算手写路由、布局或页面加载逻辑，而不是使用 Nuxt 目录约定
- 打算绕过 `runtimeConfig` 处理运行时配置
- 打算在页面组件里堆业务流程，而不是拆到 composable / service / server route
- 打算在客户端重复请求本可由 SSR / `useAsyncData` / `useFetch` 处理的数据

## 禁止事项

- 禁止把密钥、私有 token、服务端接口凭证放进客户端代码、`public` runtimeConfig 或 `import.meta.env`
- 禁止在 SSR 代码中直接访问 `window`、`document`、`localStorage`、`navigator` 等浏览器对象；必须限定在客户端生命周期或 `.client` 文件
- 禁止在组件顶层制造请求副作用、定时器或全局监听且不清理
- 禁止在页面组件中堆复杂业务逻辑；复杂逻辑应拆到 composable、service 或 server route
- 禁止直接拼接 HTML 或使用不可信内容渲染 HTML；确需渲染时必须说明来源和转义/净化策略
- 禁止绕过项目既有请求封装、鉴权处理、错误处理和响应格式
- 禁止在客户端持久化完整敏感 token；认证状态按项目既有安全方案处理
- 禁止无理由新增 Nuxt module、UI 框架、状态管理库或请求库
- 禁止忽略 hydration mismatch、SSR-only / client-only 差异和首屏性能问题
- 禁止用 `<ClientOnly>`、关闭 SSR 或强制客户端渲染来掩盖本应修复的 SSR 问题
- 禁止在 route middleware、plugin、composable 中制造无限重定向、重复请求或全局副作用
- 禁止 server route 不校验输入、不处理异常或把服务端错误细节直接返回给客户端
- 禁止把 `.env`、临时配置、构建产物、调试日志、mock 数据、测试账号提交到代码库

## 页面与组件

- 组件 props / emits 必须语义清晰，避免通过深层对象隐式耦合
- 不在组件里重复实现项目已有 composable、工具函数或请求封装
- 组件样式优先遵循项目既有 CSS / UI 方案，不自行引入另一套风格

## 数据获取与状态

- SSR 首屏数据优先使用 Nuxt 数据获取机制，并处理 pending / error / empty 状态
- 客户端交互请求复用项目已有 API client 或 composable
- 避免同一页面重复请求同一数据；需要共享时使用 composable 或项目既有状态方案
- 涉及鉴权、用户信息、租户、权限等状态时，必须考虑刷新、过期和服务端渲染一致性

## 运行时配置

- 私有配置只能放在服务端可见配置中，不能暴露到客户端
- 公开配置必须明确是可暴露信息，命名和读取方式遵循项目已有约定
- 不在代码中硬编码 API base URL、密钥、环境差异值

## Server / Nitro

- server route 只处理必要的服务端逻辑；复杂业务应拆到独立 service
- 服务端调用外部接口必须有超时、错误处理和必要日志上下文
- 不在 server route 中保存请求级状态到全局变量

## 文档查询

- 查询 Nuxt、Vue、Nitro、Pinia、UI 模块等 API 时，优先使用官方文档、项目锁定版本文档或源码
- 不凭记忆假设 Nuxt API、模块配置、渲染模式或运行时行为
