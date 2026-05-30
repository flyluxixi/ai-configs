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

## 2026-05-26 - git checkout -- 含他人未提交修改的文件会一并覆盖

**现象**: working tree 里某个文件同时存在"自己改了一部分 + 别人未提交一部分"时，跑 `git checkout -- <file>` / `git restore --worktree <file>` / `git reset --hard` 撤销自己加的那段，结果把别人的未提交修改也一并覆盖丢失。
**根因**: 这三条命令是**全文件粒度**操作——不区分"哪几行是你改的、哪几行是别人改的"，统一把 working tree 还原到 index（或 HEAD）状态。working tree 覆盖通常无法恢复（没 stash 过 + 没 reflog 痕迹）。
**解决**:
1. **首选**：用 Edit 工具按行精修，只撤掉自己加的那段
2. **备选**：`git stash --keep-index` 暂存 working tree 全部改动，操作 index 后 `git stash pop` 恢复
3. **极端备选**：`git add -p` / `git checkout -p` 选择性操作（交互式，AI 助手在 Bash 里不能跑）
4. **预防**：操作 git 撤销类命令前，**先 `git diff <file>` 确认 working tree 哪些改动是自己的、哪些是别人的**。文件 diff 里有自己不熟的内容时，绝对不能用 `git checkout --` / `git restore` / `git reset --hard`
**标签**: git, working-tree, checkout, restore, reset, user-modifications, ai-collaboration

## 2026-05-26 - 钉钉 v1.0/oauth2/accessToken 接口字段名是 appKey/appSecret，不是 clientId/clientSecret

**现象**: 调用 `POST https://api.dingtalk.com/v1.0/oauth2/accessToken` 传 OAuth2 标准字段 `{"clientId":"...","clientSecret":"...","grantType":"client_credentials"}` 返回 `{"code":"MissingappKey","message":"appKey is mandatory for this action"}`。导致所有依赖 access_token 的钉钉接口（DownloadFile / GetUserDepts / UploadMedia / 用户信息查询）全部静默挂掉
**根因**: 钉钉这个接口路径虽然是 `/oauth2/accessToken`，但实际只识别 `appKey` / `appSecret` 命名，不接受 OAuth2 标准的 `clientId` / `clientSecret`。文档历史曾标注过 clientId/clientSecret（导致沿用），但服务端校验是按 appKey 来的。错误响应里没有 accessToken 字段，应用层简单判断 "accessToken 字段为空" 时会误报为 "empty access token"，掩盖了真实错误
**解决**: 请求体改成 `{"appKey":"<clientId 值>","appSecret":"<clientSecret 值>"}`，去掉 grantType 字段；同时让 fetchToken 失败日志附带 HTTP 状态 + 原始 body，避免下次类似问题靠盲猜
**标签**: 钉钉, dingtalk, oauth2, accesstoken, appkey, clientid, 字段命名误导, 第三方API

## 2026-05-26 - FastGPT v4.14 上传文件 chunkSize 必须配合 chunkSettingMode=custom 才生效

**现象**: 通过 `/api/core/dataset/collection/create/localFile` 上传文件传 `chunkSize: 300`，但 FastGPT 实际切分用了默认 1000 字符——MongoDB `dataset_collections` 元数据显示 `chunkSize: 1000`。导致 2000 字劳动合同只切成 2 个 chunk，RAG 召回退化为"二选一"
**根因**: FastGPT v4.14 `ChunkSettingsSchema`（`packages/global/core/dataset/type.ts`）定义 `chunkSettingMode: "auto" | "custom"`，默认 "auto"；只有 mode = "custom" 时才读 `chunkSize` 字段；auto 模式下用全局默认参数（中文 1000 字符）。chunkSize 单独传不报错但被静默忽略
**解决**: 同时传三个字段才生效：`chunkSettingMode: "custom"` + `chunkSplitMode: "size"`（或 paragraph/char）+ `chunkSize: <value>`。如果想按结构切，传 `chunkSplitter: "<分隔符字符串>"` 作为最高优先匹配。仅传 chunkSize 一个字段，FastGPT 视为"未启用 custom 配置"
**标签**: fastgpt, chunksize, chunking, 配置静默忽略, ChunkSettingsSchema, RAG, 第三方API

## 2026-05-26 - FastGPT RRF 融合分本质是 1/(60+rank) 排名分，不能用作相关性阈值

**现象**: 切到 `searchMode: "mixedRecall"` 后，FastGPT 返回的 score 数组里出现 `rrf` 字段，所有 query 的 Top 1 都是 0.0167、Top 2 都是 0.0164——看起来"分数很低"。把 similarity 阈值设 0.4（按 embedding 量纲思维），FastGPT 把所有候选过滤掉，返回空 list，业务体感"什么都查不到"
**根因**: RRF（Reciprocal Rank Fusion）算法分数 = `1/(60+rank)`，rank 从 0 开始：第 1 名 ≈ 0.0167、第 2 名 ≈ 0.0164、第 5 名 ≈ 0.0154。**整个分布天然在 0.01-0.02 量级**，且跨 query 无差异（强相关查询和"今天天气"无关查询，Top 1 RRF 分数都是 0.0167）。它是排名信号不是相关性信号——按 rrf 排序还会把"两路 rank 中等"的无关 chunk 拉到"单路强命中"的相关 chunk 前面
**解决**: mixedRecall + rerank 模式下，**用 reRank 分（不是 rrf 也不是 embedding）做排序和阈值过滤**：bge-reranker-v2-m3 实测分布——强相关 0.05-0.1+、弱相关 0.01-0.02、无关 <0.005，跨 4 个数量级。0.02 作为阈值是模型自身输出分布决定的天然分界。FastGPT similarity 参数对应的是 RRF 量纲，所以服务端 similarity 设 0（不过滤），过滤放客户端按 reRank 分做
**标签**: fastgpt, rrf, reciprocal-rank-fusion, rerank, mixedrecall, similarity, 阈值, 量纲混淆, 第三方API

## 2026-05-26 - FastGPT searchTest 的 limit 是返回内容的 token 上限，不是 chunk 数

**现象**: 给 `/api/core/dataset/searchTest` 传 `limit: 5` 期望返回 5 条 chunk，实际行为不可预期——有时返回 2-3 条，有时返回更多；调到 `limit: 5000` 才稳定返回足够候选给 rerank 重排
**根因**: FastGPT searchTest 接口的 `limit` 字段语义是"返回内容的总 token 上限"，不是"chunk 数量上限"。传 5 = 限制返回 5 个 token，远远装不下一条 chunk（chunkSize=300 字符 ≈ 200 token），FastGPT 行为退化到默认或截断。文档未明确强调这一点
**解决**: 传 token 数而不是 chunk 数。经验值：希望 rerank 在 10-15 个候选里挑选 → limit=3000；希望更宽召回池 → limit=5000-8000。**单 chunk token ≈ chunkSize 字符 × 0.7**（中文）作为换算参考
**标签**: fastgpt, searchtest, limit, token, chunk, 单位误导, 第三方API

## 2026-05-30 - Ghostty 1.3.x 渲染 Claude Code CLI 输出停更，需 resize 才刷新

**现象**: 在 Ghostty 终端跑 Claude Code CLI，任务执行中屏幕突然不再有任何输出，像"卡住/暂停"；实际任务已正常执行完，敲键或拖动窗口后输出才一次性显示。多窗格并发跑 claude/codex 时更频繁、越来越严重。
**根因**: Ghostty 已知开放 bug（Discussion #12062，影响 1.3.1 stable，2026-04 报告，未修复；前身 #11001）。Claude Code 的 TUI 同时使用 DEC 2026 同步输出（\x1b[?2026h...l）+ DECSTBM 滚动区域固定状态栏 + 高频增量光标定位，触发 Ghostty Metal 增量渲染不刷新；多后台 agent 并发会持续恶化。非数据丢失、非进程挂起、非机器问题。
**解决**: ① 最可靠：把长跑 claude/codex 的窗格换到 iTerm2（无此 bug）。② 临时救画面：拖动改变窗口大小强制全量重绘，缺失输出即出现（数据都在）。③ 减少并发降低严重度。④ 跟踪 issue #12062，修复后再升级 Ghostty。⚠️ 排查教训：初期误判为双显卡自动切换（gpuswitch=2）卡 Metal，查 issue 后确认主因是同步输出+状态栏渲染冲突，勿凭硬件特征臆断。
**标签**: ghostty, claude-code, 终端渲染, metal, synchronized-output, dec2026, tui, 输出不刷新, macos
