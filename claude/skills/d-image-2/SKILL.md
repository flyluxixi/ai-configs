---
name: d-image-2
description: 生成图片并保存到指定路径。默认复用本机 Codex CLI 登录态（免单独 API key 计费），也可走 OpenAI Images API 的 gpt-image-2。用户提到 d-image-2、gpt-image-2、生成图片、画图、改图、生成素材、保存图片到文件时使用。
---

# d-image-2

使用本 skill 目录下的 `scripts/generate_image.py` 生成图片。脚本有两个后端，用 `--via` 切换：

- `--via codex`（**默认**）：复用本机 Codex CLI 的 ChatGPT 登录态（`~/.codex/auth.json`），打 ChatGPT 后端的 `image_generation` 工具，**免单独 API key 计费**。支持文生图、图生图。需要 `curl_cffi` 依赖。
- `--via openai`：走公开 OpenAI Images API，显式 `gpt-image-2`，纯标准库，需要环境变量 `OPENAI_API_KEY`。仅文生图。

不要改用会话或 CLI 内置的图像生成工具（除非用户明确要求）——本 skill 的目标是走可控、可审计、模型显式的脚本后端。

> ⚠️ codex 后端依赖逆向得来的 ChatGPT 内部端点 + Codex 的 OAuth client_id，属非官方用法：OpenAI 调整端点/版本下限/模型时随时可能失效，且用订阅登录态驱动自动化端点踩 ToS，账号有风险。需要稳定契约时改用 `--via openai`。

## 工作流

1. 确认用户给出了图片描述和保存路径。缺少保存路径时先询问；不要自行保存到不明确的位置。
2. 选后端：默认 `codex`（复用登录态、能图生图）；用户要求稳定契约或显式提到 API key 时用 `--via openai`。
3. 默认 `1024x1024`、`high`。用户指定尺寸、质量、背景时按用户要求传参。
4. 鉴权：`codex` 后端自动读 `~/.codex/auth.json` 并按需刷新 token，无需用户提供任何密钥；`openai` 后端只从环境变量 `OPENAI_API_KEY` 读取密钥，不要把密钥写进命令、代码或 prompt。
5. 运行脚本生成图片。Shell 命令使用 `rtk` 前缀；输出路径不在当前沙箱可写范围时，按工具权限规则申请写入授权。
6. 默认不覆盖已有文件。只有用户明确要求覆盖时才传 `--overwrite`。
7. 完成后报告保存路径；如果未实际联网生成，不得说图片已生成。

## 依赖

`--via codex` 需要 `curl_cffi`（Python 版 libcurl-impersonate，过 Cloudflare TLS 指纹检测）：

```bash
rtk pip3 install curl_cffi
```

`--via openai` 仅用 Python 标准库，无需额外依赖。

## 命令模板

文生图（默认 codex 后端）：

```bash
rtk python3 <skill-dir>/scripts/generate_image.py \
  --prompt "图片描述" \
  --output "/absolute/or/relative/output.png"
```

图生图（仅 codex 后端，`--image` 可重复，1~5 张）：

```bash
rtk python3 <skill-dir>/scripts/generate_image.py \
  --prompt "把这张图改成黄昏色调" \
  --image "/path/to/input.png" \
  --output "/path/to/output.png"
```

走稳定契约的 OpenAI Images API：

```bash
rtk python3 <skill-dir>/scripts/generate_image.py \
  --via openai \
  --prompt "图片描述" \
  --output "/path/to/output.png"
```

## 参数说明

通用：

```bash
--via codex|openai     # 后端，默认 codex
--size 1536x1024       # 或 auto；codex 默认 1024x1024
--quality high         # low|medium|high|auto
--overwrite            # 覆盖已有文件
--timeout 600          # HTTP 超时秒数
```

仅 `--via codex`：

```bash
--image PATH              # 图生图输入，可重复（1~5 张）
--background opaque       # transparent|opaque|auto
--model gpt-5.5           # 编排模型，默认读 ~/.codex/config.toml 的 model
--codex-home DIR          # codex 目录，默认 $CODEX_HOME 或 ~/.codex
```

> ⚠️ `--background transparent` 当前在 codex 后端**不可用**：该端点的 hosted 图像工具锁定 `gpt-image-2`，而 gpt-image-2 不支持透明背景（实测返回 `400 Transparent background is not supported`），且无法切换生图模型。需要透明背景时只能走公开 Images API + 显式 `gpt-image-1.5`（本脚本 openai 后端写死 gpt-image-2，暂不覆盖此场景）。`opaque` / `auto` 正常可用。

仅 `--via openai`：

```bash
--format png           # png|jpeg|webp
--compression 80       # 0~100，仅 jpeg/webp 有效
```

尺寸约束（两后端一致，`gpt-image-2` 规则）：边长为 16 的倍数、最大边不超过 3840px、长短边比例不超过 3:1、总像素在 655,360~8,294,400 之间，`auto` 除外。脚本会做本地校验。

## 后端机制要点

- **编排模型 vs 生图模型**：`--model`（默认读 codex 配置，如 `gpt-5.5`）只负责读懂 prompt、决定调用图像工具；真正画图的是后端 hosted `image_generation` 工具（GPT Image 系列，当前默认 `gpt-image-2`）。
- **自愈动态值**：`codex` 后端的 `User-Agent` 版本号实时读 `codex --version`，编排模型实时读 `config.toml`，自动跟随本机 codex，无需手动改。
- **写死的稳定常量**：`client_id`、`/codex/responses` 端点、`originator`、OAuth 刷新端点集中在脚本顶部，各自失效条件见代码注释。后端策略变化时才需要手动更新。

## 脚本路径

优先使用当前加载的 skill 目录下脚本。如果需要从源仓库运行，路径为：

```text
/Users/luxixi/projects/ai-configs/claude/skills/d-image-2/scripts/generate_image.py
```
