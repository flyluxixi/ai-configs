# FastGPT 踩坑记录

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
