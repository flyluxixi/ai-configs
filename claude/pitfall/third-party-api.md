# 第三方服务 API 集成踩坑记录

## 2026-05-14 - OSS V1 签名 + STS：x-oss-security-token 必须同时出现在请求头和 StringToSign 中

**现象**: OSS 返回 403 SignatureDoesNotMatch 或 403 AccessDenied，使用 STS 临时凭证签名时发生
**根因**: OSS V1 签名规范要求，使用 STS 临时凭证时 x-oss-security-token 必须：① 作为请求头发送；② 同时出现在 StringToSign 的 CanonicalizedOSSHeaders 段（按字母序）。缺少任意一处，OSS 签名验证失败
**解决**: StringToSign 中加入 `x-oss-security-token:{token}\n`（紧接在 Date 行之后，/ 资源路径之前），同时 `req.Header.Set("x-oss-security-token", token)`
**标签**: oss, sts, v1签名, security-token, 403, 阿里云

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

## 2026-05-26 - 钉钉 v1.0/oauth2/accessToken 接口字段名是 appKey/appSecret，不是 clientId/clientSecret

**现象**: 调用 `POST https://api.dingtalk.com/v1.0/oauth2/accessToken` 传 OAuth2 标准字段 `{"clientId":"...","clientSecret":"...","grantType":"client_credentials"}` 返回 `{"code":"MissingappKey","message":"appKey is mandatory for this action"}`。导致所有依赖 access_token 的钉钉接口（DownloadFile / GetUserDepts / UploadMedia / 用户信息查询）全部静默挂掉
**根因**: 钉钉这个接口路径虽然是 `/oauth2/accessToken`，但实际只识别 `appKey` / `appSecret` 命名，不接受 OAuth2 标准的 `clientId` / `clientSecret`。文档历史曾标注过 clientId/clientSecret（导致沿用），但服务端校验是按 appKey 来的。错误响应里没有 accessToken 字段，应用层简单判断 "accessToken 字段为空" 时会误报为 "empty access token"，掩盖了真实错误
**解决**: 请求体改成 `{"appKey":"<clientId 值>","appSecret":"<clientSecret 值>"}`，去掉 grantType 字段；同时让 fetchToken 失败日志附带 HTTP 状态 + 原始 body，避免下次类似问题靠盲猜
**标签**: 钉钉, dingtalk, oauth2, accesstoken, appkey, clientid, 字段命名误导, 第三方API
