# Docker 踩坑记录

## 2026-05-16 - 跨 compose 文件的容器默认网络隔离，需显式声明 external network

**现象**: library-gateway 容器无法访问 fastgpt-pg / fastgpt-redis / fastgpt-app，连接超时或 DNS 解析失败。
**根因**: Docker Compose 默认为每个 compose 文件创建独立网络，不同 compose 文件启动的容器彼此隔离，即使在同一宿主机也无法直接通信。
**解决**: 在需要访问其他 compose 文件容器的 compose 里显式声明目标网络，并标记 `external: true`：
```yaml
networks:
  fastgpt_app:
    external: true
  fastgpt_data:
    external: true
```
同时在 service 的 `networks` 字段列出需要加入的网络。
**标签**: docker, compose, network, external, 跨项目容器通信

---

## 2026-05-16 - `depends_on` 不能跨 compose 文件，写了静默无效

**现象**: 在 library-gateway 的 compose 文件里写 `depends_on: fastgpt-pg`，容器启动顺序没有任何影响，也不报错。
**根因**: `depends_on` 只能引用同一 compose 文件内定义的 service，跨文件依赖 Docker 不识别，既不报错也不生效。
**解决**: 跨 compose 文件的启动顺序依赖只能靠应用层重试（如数据库连接重试），或通过 shell 脚本手动控制启动顺序，不能依赖 `depends_on`。
**标签**: docker, compose, depends_on, 跨项目, 静默无效
