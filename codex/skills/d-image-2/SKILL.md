---
name: d-image-2
description: 使用 OpenAI Images API 的 gpt-image-2 生成图片并保存到指定路径。用户提到 d-image-2、gpt-image-2、生成图片、画图、生成素材、保存图片到文件时使用。
---

# d-image-2

使用本 skill 目录下的 `scripts/generate_image.py` 调用 OpenAI Images API。不要改用会话内置的 `image_gen` 工具，因为该工具不暴露底层模型，无法确认一定是 `gpt-image-2`。

## 工作流

1. 确认用户给出了图片描述和保存路径。缺少保存路径时先询问；不要自行保存到不明确的位置。
2. 默认使用 `gpt-image-2`、`1024x1024`、`high`、`png`。用户指定尺寸、质量或格式时按用户要求传参。
3. 只从环境变量 `OPENAI_API_KEY` 读取密钥；不要要求用户把密钥写进命令、代码或 prompt。
4. 运行脚本生成图片。Shell 命令使用 `rtk` 前缀；输出路径不在当前沙箱可写范围时，按工具权限规则申请写入授权。
5. 默认不覆盖已有文件。只有用户明确要求覆盖时才传 `--overwrite`。
6. 完成后报告保存路径；如果未实际联网生成，不得说图片已生成。

## 命令模板

```bash
rtk python3 <skill-dir>/scripts/generate_image.py \
  --prompt "图片描述" \
  --output "/absolute/or/relative/output.png"
```

常用可选参数：

```bash
--size 1536x1024
--quality high
--format png
--overwrite
```

`gpt-image-2` 的尺寸必须满足 OpenAI Images API 约束：边长为 16 的倍数、最大边不超过 3840px、长短边比例不超过 3:1、总像素在有效范围内。脚本会做本地校验。

## 脚本路径

优先使用当前加载的 skill 目录下脚本。如果需要从源仓库运行，路径为：

```text
/Users/luxixi/projects/ai-configs/codex/skills/d-image-2/scripts/generate_image.py
```
