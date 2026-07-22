# Docker 规则

适用范围：Dockerfile 编写、docker compose 编排、容器运行与排障。

## 禁止事项

- 禁止基础镜像使用 `latest` 或省略 tag；必须固定到明确版本
- 禁止把密钥、token、证书写进镜像层，包括用 build ARG 传敏感值（会留在镜像历史中）；运行时通过环境变量或挂载注入
- 禁止业务数据落在容器可写层；必须挂载 volume 或 bind mount
- 禁止日志写容器内文件；统一输出到 stdout / stderr 由日志驱动收集
- 禁止无 `.dockerignore` 直接构建，避免把 `.git`、`node_modules`、`.env` 打进构建上下文
- 禁止生产容器以 root 运行业务进程，除非有明确理由并说明
- 禁止把 `docker exec` 进容器改状态当作修复手段；改动必须落到镜像 / compose 配置再重建，否则重启即丢

## Compose 编排

- 不同 compose 文件启动的容器默认网络隔离、互不可见；跨 compose 通信必须显式声明目标网络并标记 `external: true`，同时在 service 的 `networks` 中加入
- `depends_on` 只能引用同一 compose 文件内的 service，跨文件引用静默无效；且默认只控制启动顺序、不等待就绪，就绪依赖用 healthcheck + `condition: service_healthy` 或应用层连接重试
- service 应配置 healthcheck，除非该镜像无合适探测方式并说明
- 生产 compose 必须设置 restart 策略与资源限制（memory / cpu）
- 环境差异（端口、密钥、副本数）通过 `.env` 或 override 文件注入，compose 主文件保持环境无关

## 镜像构建

- 多阶段构建分离编译与运行环境，运行镜像只含产物和运行时依赖
- 层顺序按变化频率组织：依赖安装在前、源码拷贝在后，最大化构建缓存命中
- 构建可复现：锁定依赖版本，不在构建时拉取不带版本约束的依赖

## 文档查询

- Docker 文档 context7 library ID：`/websites/docker`；Compose 专项：`/docker/compose`
- 查询 Dockerfile 指令、compose 字段、网络与存储驱动行为时，必须先用 context7 或官方文档确认，不凭记忆假设
