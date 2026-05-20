# 通用踩坑记录

## 2026-05-14 - OSS V1 签名 + STS：x-oss-security-token 必须同时出现在请求头和 StringToSign 中

**现象**: OSS 返回 403 SignatureDoesNotMatch 或 403 AccessDenied，使用 STS 临时凭证签名时发生
**根因**: OSS V1 签名规范要求，使用 STS 临时凭证时 x-oss-security-token 必须：① 作为请求头发送；② 同时出现在 StringToSign 的 CanonicalizedOSSHeaders 段（按字母序）。缺少任意一处，OSS 签名验证失败
**解决**: StringToSign 中加入 `x-oss-security-token:{token}\n`（紧接在 Date 行之后，/ 资源路径之前），同时 `req.Header.Set("x-oss-security-token", token)`
**标签**: oss, sts, v1签名, security-token, 403, 阿里云

## 2026-05-17 - Commit 引用一致性：main.go/DI 文件引用了未 commit 的方法导致服务器构建失败

**现象**: 本地 build 通过，commit + push 后服务器 git pull 构建失败：`main.go:163 listingHandler.MarkRented undefined`。
**根因**: 本地 `main.go` 改动里包含了之前会话遗留的路由注册（引用 `listing_handler.go` 的新方法），但 `listing_handler.go` 仍是 modified 未 commit 状态。`git add main.go` 时只看修改文件没看引用关系，把"路由声明"commit 了，"方法实现"留在工作区。本地 build 正常因为本地工作区是完整的，远端 pull 拿到的是不一致的快照。
**解决**: commit 前对 staged 文件做引用一致性自检——`git diff --staged` 看实际改动；特别检查路由注册（main.go）、DI 注入、struct 字段、方法调用等"声明 vs 实现"分离位置。涉及多文件协同改动时确认所有引用方和被引用方一起 staged，或拆成多个原子 commit。
**标签**: git, commit, staged, 服务器部署, 构建失败, 引用一致性

## 2026-05-17 - 经纬度 bounding box 漏候选：lng delta 未按 cos(lat) 缩放

**现象**: FindNearby 在济南（lat 36.6°）约定 300m 半径，但东西方向 240-300m 的候选 building 全部漏掉，南北方向 OK。
**根因**: `radiusDeg = radius / 111320` 同时用于 latitude 和 longitude 的 BETWEEN 粗筛。纬度 1° 恒定约 111.32 km；但经度 1° 实际距离是 `111320 * cos(lat)` m，纬度 36.6° 处约 89.3 km，比赤道短 ~20%。同样的 deg 差，东西方向粗筛半径只有 240m。
**解决**: 拆出 `latDelta = radius / 111320`、`lngDelta = radius / (111320 * cos(lat_radians))` 分别传 SQL；极端高纬保护：`cos(lat)` 接近 0 时兜底（如 `< 0.01 时设为 0.01`）避免除零。后续在 SQL 内仍用平面近似公式做精确距离计算和过滤。
**标签**: geo, 经纬度, bounding box, cos, 平面近似距离, 漏候选

## 2026-05-20 - 腾讯地图 adcode 字段类型在不同接口位置不一致

**现象**: 用 string 定义腾讯 `geocoder/v1?get_poi=1` 响应中 `result.pois[].ad_info.adcode` 字段时，`json.Unmarshal` 直接报错 `cannot unmarshal number into Go string`，整个附近搜索远程结果丢失
**根因**: 腾讯地图同一字段在不同接口/位置返回类型不一致：① `place/v1/search` `data[].ad_info.adcode` 是 number；② `place/v1/suggestion` `data[].adcode` 是 number；③ `geocoder/v1` 主结果 `result.ad_info.adcode` 是 string；④ `geocoder/v1?get_poi=1` 子项 `result.pois[].ad_info.adcode` 是 number。仅凭某一处对照定义 struct，切换接口时会翻车
**解决**: 定义自定义类型 `flexAdCode string`，实现 `UnmarshalJSON` 同时兼容 JSON 字符串和 JSON 数字，统一存为 string；涉及第三方 API 整数 ID 类字段建议预防性用此类自定义类型
**标签**: 腾讯地图, json, unmarshal, adcode, 类型兼容, 第三方API

## 2026-05-20 - 腾讯地图 POI 类接口的入参/限制差异巨大，选错接口配额秒爆或半径被截断

**现象**: 用 `place/v1/search?boundary=nearby(lat,lng,radius)` 做附近搜索，配额 2000/key/日很快用完；提高 radius 到 2000m，腾讯静默截断到 1000m 上限不报错；keyword 字段官方文档标注必填，传空可能直接 status≠0；切到 `geocoder/v1?get_poi=1` 又发现没有 category filter，路标/餐饮等噪音 POI 都返回
**根因**: 腾讯 POI 类接口看似都做"找附近的 POI"，实际语义和限制差异巨大：
- `place/v1/search` 是"区域内全量搜索"，配额 2000/日，半径 ≤1000m，keyword 必填
- `place/v1/suggestion` 是"边输边补全"，配额 30 万/日，无 location 模式（不支持 boundary=nearby）
- `geocoder/v1?get_poi=1&poi_options=...` 是"逆地址解析顺手返回 POI"，配额 300 万/日，半径 ≤5000m，但无 category filter
- `location/v1/ip` 是"IP 推 IP 城市"，无坐标输入

各接口的配额、半径、参数、过滤能力完全不一样，混用同一个"附近搜索"概念会踩坑
**解决**: 选型前确认每个接口的：① 配额（per-key/日 + QPS）；② 必填参数与默认值；③ 半径上限；④ 是否支持 category/business filter；⑤ 返回排序是否符合预期。drop pin 选址用 geocoder（配额/半径优势）；as-you-type 关键词补全用 suggestion（配额优势）；place_search 留作兼容兜底；IP 定位独立用 location 接口。每个接口在 service 层独立 quota counter，不抢额度
**标签**: 腾讯地图, POI, place_search, suggestion, geocoder, IP定位, 接口选型, 配额, 第三方API
