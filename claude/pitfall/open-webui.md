# Open WebUI 踩坑记录

## 2026-07-01 - Open WebUI wrapper 模型（id≠base_model_id）不向下游 API 传工具定义，工具调用失效

**现象**: 在 model 表里创建 wrapper 模型（id=xiaohongshu-assistant, base_model_id=deepseek-v4-pro）并注入系统提示后，LLM 调用了幻觉出来的工具名（如 mcp__xhs-mcp__check_login_status），全部返回空，最终放弃并报告"工具不可用"
**根因**: Open WebUI 的 wrapper 模型（id≠base_model_id）在构建下游 API 请求时不包含工具服务器的工具定义；LLM 没收到工具列表，只能靠训练记忆猜工具名，猜出来的名字在注册表里找不到，返回空
**解决**: 注入系统提示不要用 wrapper（id≠base_model_id），改用 preset（id==base_model_id）——在 model 表里为原生模型创建同 id 条目并填 params.system；Open WebUI 把它当"带默认参数的原生模型"处理，工具路径不受影响。等价于管理界面 Admin Panel → Models → 编辑目标模型 → System Prompt 字段
**标签**: open-webui, model-wrapper, preset, tool-server, 工具调用失效, system-prompt, 系统提示注入

## 2026-07-01 - LLM 复述工具返回的 Markdown 图片而非原样输出，导致内嵌图片消失

**现象**: FastAPI 工具返回 `![小红书登录二维码](url)` 字符串，LLM 收到后输出"二维码已生成！📱"并给出文字步骤，回复正文里没有图片 Markdown，Open WebUI 无法渲染图片
**根因**: LLM 倾向于"理解后复述"工具结果而非原样输出；Markdown 图片语法对模型而言是"内容描述"，会被概括成文字说明
**解决**: 通过 model preset 注入系统提示明确约束：「当工具返回含 ![描述](url) 的 Markdown 时，必须将图片代码原样复制到回复正文，不得替换为文字描述」；同时在工具的 description 字段注明"返回值是需要原样嵌入回复的 Markdown"，双重约束
**标签**: open-webui, llm, tool-result, markdown-image, 工具结果复述, 系统提示, deepseek
