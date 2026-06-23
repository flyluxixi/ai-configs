# Vue 3 规则

适用范围：Vue 3 + Vite + Vue Router + Pinia 项目（管理后台等 SPA 场景）。UI 库以项目既有为准；使用 Element Plus 时同时遵守本规则中 Element Plus 相关约束。后端接口、数据库、缓存、Nginx 等规则分别由对应项目或技术栈规则声明。

## 技术栈与环境

- Vue 3 + Vite + Vue Router 4 + Pinia（以项目 `package.json`、lockfile 和 `vite.config.*` 为准）

生成代码前先读取 `package.json`、lockfile、`vite.config.*`、`src/` 目录结构和项目已有页面/组件写法，确认 Vue 版本、路由方案、状态管理方案、包管理器和已使用 UI 库。

## 禁止事项

- 禁止把密钥、私有 token、服务端接口凭证放进客户端代码或 `import.meta.env` 的公开变量
- 禁止在代码中硬编码 API base URL、密钥、环境差异值
- 禁止在组件中堆复杂业务逻辑；复杂逻辑必须拆到 composable 或 service
- 禁止直接解构 `reactive` 对象或 `props` 导致丢失响应性；需解构时必须用 `toRefs` / `toRef`，从 Pinia store 取响应式状态必须用 `storeToRefs`
- 禁止直接修改 `props`；父子通信必须通过 `emits` 或 `v-model`
- 禁止用数组 index 作为动态列表 `v-for` 的 `key`；禁止 `v-if` 与 `v-for` 作用于同一元素
- 禁止绕过项目既有请求封装、鉴权处理、错误处理和响应格式
- 禁止在 composable、插件或全局守卫中制造未清理的副作用、定时器或全局监听
- 禁止无理由新增 UI 框架、状态管理库、路由库或请求库
- 禁止新增第三方包处理项目已有 composable、工具函数或请求封装可解决的问题
- 禁止同一页面重复请求同一数据；需要共享时必须使用 Pinia store 或 composable
- 禁止组件 props / emits 通过深层对象隐式耦合
- 禁止在组件里重复实现项目已有 composable、工具函数或请求封装
- 禁止组件样式引入项目既有 CSS / UI 方案之外的另一套风格
- 禁止直接拼接 HTML 或对不可信内容使用 `v-html`（`v-html` 不经过 Vue 自动转义，等同 XSS 入口）；确需动态渲染时必须说明来源和净化策略
- 禁止在客户端持久化完整敏感 token；认证状态按项目既有安全方案处理
- 禁止手写路由守卫绕过项目既有权限控制逻辑
- 禁止把 `.env`、临时配置、构建产物、调试日志、mock 数据、测试账号提交到代码库

## 目录结构

以项目既有 `src/` 结构为准；无既有结构时采用以下约定：

```
├── src/
│   ├── views/          # 路由级页面组件
│   ├── components/     # 通用复用组件
│   ├── composables/    # 组合式函数
│   ├── stores/         # Pinia store
│   ├── router/         # 路由配置
│   ├── api/            # 接口封装
│   ├── utils/          # 工具函数
│   ├── assets/         # 静态资源
│   └── App.vue
├── vite.config.ts
└── package.json
```

- 禁止在 `views/` 以外挂载路由级页面组件
- 禁止把接口调用、业务逻辑直接写在路由配置文件中

## 路由

- 路由定义必须按项目既有风格组织，不自行另起风格
- 路由守卫只处理鉴权和权限控制，不写业务流程
- 动态路由必须按项目既有权限方案挂载，禁止绕过鉴权逻辑
- 禁止在使用 history 模式时假设静态托管自动回退；必须确认部署侧已配置 SPA fallback（如 OSS / Nginx 将未命中路由回退到 `index.html`）

## 状态管理（Pinia）

- store 只放需要跨组件共享的全局状态；组件内部状态用 `ref` / `reactive`
- store action 必须处理 loading / error 状态，不让调用方自行管理
- 禁止在 store 外直接修改 store 内部状态；状态变更必须通过 action
- 禁止 store 保存请求级临时数据或单组件私有 UI 状态

## Element Plus

- 表单必须使用 `el-form` + `el-form-item` 的校验机制；禁止绕过校验直接提交
- 禁止绕过 Element Plus 已有组件自行实现相同功能
- 涉及大数据量列表时，必须使用虚拟滚动或分页，禁止一次渲染全量数据

## 请求与数据

- 所有异步操作必须处理 loading / error / empty 状态
- 客户端请求必须复用项目已有 API client 或 composable
- 禁止在组件 `setup` 顶层发起未封装的请求；必须处理组件卸载后回调仍执行的竞态，不对已卸载组件继续驱动状态更新

## 文档查询

- 查询 Vue、Vue Router、Pinia、Vite、Element Plus 等 API 时，必须优先使用 context7、官方文档、项目锁定版本文档或源码
- Vue 3 文档 context7 library ID：`/vuejs/vue`
- Vue Router 4 文档 context7 library ID：`/vuejs/router`
- Pinia 文档 context7 library ID：`/vuejs/pinia`
- Vite 文档 context7 library ID：`/vitejs/vite`
- Element Plus 文档 context7 library ID：`/element-plus/element-plus`
- 不凭记忆假设 Vue、Vue Router、Pinia、Vite 或 Element Plus 的具体 API 或行为
