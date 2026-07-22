# AI 编程工具链踩坑记录

## 2026-05-30 - Ghostty 1.3.x 渲染 Claude Code CLI 输出停更，需 resize 才刷新

**现象**: 在 Ghostty 终端跑 Claude Code CLI，任务执行中屏幕突然不再有任何输出，像"卡住/暂停"；实际任务已正常执行完，敲键或拖动窗口后输出才一次性显示。多窗格并发跑 claude/codex 时更频繁、越来越严重。
**根因**: Ghostty 已知开放 bug（Discussion #12062，影响 1.3.1 stable，2026-04 报告，未修复；前身 #11001）。Claude Code 的 TUI 同时使用 DEC 2026 同步输出（\x1b[?2026h...l）+ DECSTBM 滚动区域固定状态栏 + 高频增量光标定位，触发 Ghostty Metal 增量渲染不刷新；多后台 agent 并发会持续恶化。非数据丢失、非进程挂起、非机器问题。
**解决**: ① 最可靠：把长跑 claude/codex 的窗格换到 iTerm2（无此 bug）。② 临时救画面：拖动改变窗口大小强制全量重绘，缺失输出即出现（数据都在）。③ 减少并发降低严重度。④ 跟踪 issue #12062，修复后再升级 Ghostty。⚠️ 排查教训：初期误判为双显卡自动切换（gpuswitch=2）卡 Metal，查 issue 后确认主因是同步输出+状态栏渲染冲突，勿凭硬件特征臆断。
**标签**: ghostty, claude-code, 终端渲染, metal, synchronized-output, dec2026, tui, 输出不刷新, macos

## 2026-06-02 - codex/responses 的 image_generation 工具锁定 gpt-image-2，透明背景不可用

**现象**: 复用 Codex 登录态走 chatgpt.com/backend-api/codex/responses 端点的 hosted image_generation 工具生图时，传 background=transparent 后端返回 400 "Transparent background is not supported for this model"；即便在 tool 配置里指定 model=gpt-image-1.5 也被忽略，仍报同样错误。
**根因**: 该内部端点的 hosted image_generation 工具把生图模型锁死为 gpt-image-2（GPT Image 家族当前默认），客户端只能传 size/quality/background，无法切换生图模型；而 gpt-image-2 本身不支持透明背景（codex 二进制提示需改用 gpt-image-1.5）。tool.model 字段在该端点被无视。这是把生图模型选择权交给后端的代价：省事但不可控、不可指定。imgen（复用 codex 登录态的 Node CLI）与 d-image-2 的 codex 后端都受此限制。
**解决**: 需要透明背景时只能走公开 OpenAI Images API + 显式指定 gpt-image-1.5（需独立 OPENAI_API_KEY 计费）；codex 登录态路径放弃透明背景需求。opaque/auto 背景在 codex 后端正常可用。
**标签**: openai, chatgpt, codex, image_generation, gpt-image-2, gpt-image-1.5, 透明背景, responses-api, 锁定模型, 第三方API

## 2026-06-02 - Intel Mac（x86_64 macOS）被新生态底层库抛弃，AI 推理/原生扩展类依赖装不上

**现象**: 在 Intel Mac（x86_64 macOS）装需要 AI 推理或预编译原生扩展的库反复失败：① 给 d-image-2 装 rembg 做本地 AI 抠图——onnxruntime 无 Python 3.14（cp314）wheel，且 macos x86_64 最高停在 1.23.0/cp313（新版只发 arm64）；降到 Python 3.13 装老版 rembg 2.0.69 又卡在 numba→llvmlite 源码编译失败。② 同模式：imgen 依赖的 @ossiana/node-libcurl-darwin-x64 所有版本里打包的都是 arm64 二进制，x64 渠道从未打对，dlopen 报 incompatible architecture。
**根因**: 主流 AI / 原生扩展库（onnxruntime、torch、部分 npm 原生包）正停止为 macOS x86_64 发预编译产物，只保留 arm64（Apple Silicon）+ linux/win；叠加 Python 版本过新（3.14 无 cp314 wheel），x86_64 Intel Mac 成为被抛弃的长尾平台。降版本又会拉到更老、需源码编译的依赖（numba/llvmlite 需 LLVM 工具链），层层失败。
**解决**: ① 动手前先查目标库是否还发 x86_64 macOS wheel（看 PyPI 文件列表 / pip 报错里的 available platforms），不要盲目硬装或层层降版本死磕。② 本地 AI 推理类需求（抠图/分割）改走云端或网页版——如透明 PNG 素材直接用 ChatGPT 网页版（实测能出真 RGBA 透明，免费走订阅）。③ 根治：迁移到 arm64（Apple Silicon）Mac，这类库一行即装。
**标签**: intel-mac, x86_64, macos, onnxruntime, rembg, numba, llvmlite, node-libcurl, wheel, arm64, 预编译, 平台抛弃, python3.14

## 2026-06-02 - codex 端点逆向生图被 OpenAI 反滥用检测，token 主动失效 + codex 登录被 step-up 验证

**现象**: d-image-2 codex 后端（复用 codex 登录态、curl_cffi 伪装 codex_cli_rs 打 chatgpt.com/backend-api/codex/responses 生图）连续生成几次后返回 401 "invalidated oauth token, failing request"；强制用 refresh_token 刷新也 401（refresh 一并被作废）；codex login 重新授权时被要求 step-up 手机号验证，而此时 ChatGPT 网页端仍是登录有效状态。
**根因**: 经 codex/responses 端点的逆向访问（curl_cffi 伪装客户端 + 短时间高频 + 非交互 + quality 全 high）触发 OpenAI 反滥用检测，针对性失效 codex 客户端的 access+refresh token，并对 codex 重新授权加 step-up 手机验证。账号本身未被封（网页版正常），被限制的是 codex 客户端这条通道。关键时序证据：codex 升级 0.136.0 后还成功生图 3 次、第 4 次才失效——是累积异常访问触发风控，不是版本升级导致（初判归因升级是错的）。
**解决**: ① 逆向方案（codex 端点 / 网页版皆然）脆弱且对抗性强，不可依赖做关键流程。② codex 生图后端降级为「能用就用、随时会挂」的低频一次性工具，别高频/批量/全 high 触发风控；验手机号能恢复 codex 登录，但继续逆向会反复被风控、账号风险升级。③ 稳定生图回到网页版手动或官方付费 gpt-image API（--via openai，不依赖逆向、不被风控、顺带解决透明）。④ 关键架构启示：把 prompt 优化层与生图后端解耦——优化产出的英文 prompt 喂任何渠道都成立，价值独立于易失效的逆向后端。
**标签**: codex, 逆向, 反滥用, 风控, oauth, token失效, invalidated, refresh-token, step-up, 手机验证, chatgpt, image_generation, responses-api, 解耦
