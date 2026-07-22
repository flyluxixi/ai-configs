# 通用踩坑记录

> 本文件只收不匹配任何已有分类的孤例；当同主题条目攒到 2 条时，应新建分类（先改 d-pitfall SKILL.md 枚举）并迁移，不让模糊条目堆积。

## 2026-05-17 - 经纬度 bounding box 漏候选：lng delta 未按 cos(lat) 缩放

**现象**: FindNearby 在济南（lat 36.6°）约定 300m 半径，但东西方向 240-300m 的候选 building 全部漏掉，南北方向 OK。
**根因**: `radiusDeg = radius / 111320` 同时用于 latitude 和 longitude 的 BETWEEN 粗筛。纬度 1° 恒定约 111.32 km；但经度 1° 实际距离是 `111320 * cos(lat)` m，纬度 36.6° 处约 89.3 km，比赤道短 ~20%。同样的 deg 差，东西方向粗筛半径只有 240m。
**解决**: 拆出 `latDelta = radius / 111320`、`lngDelta = radius / (111320 * cos(lat_radians))` 分别传 SQL；极端高纬保护：`cos(lat)` 接近 0 时兜底（如 `< 0.01 时设为 0.01`）避免除零。后续在 SQL 内仍用平面近似公式做精确距离计算和过滤。
**标签**: geo, 经纬度, bounding box, cos, 平面近似距离, 漏候选
