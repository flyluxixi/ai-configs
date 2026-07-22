---
name: d-pitfall
description: 记录技术踩坑或决策踩坑到个人知识库。显式触发：用户说"记录这个坑"、"记一下这个坑"、"把这个坑记下来"、"记坑"、"/d-pitfall"。主动提议触发：会话中刚解决一个根因非显然的问题（多次尝试才定位 / 推翻最初假设 / 修法反直觉或与文档、版本预期不符）时，用一句话提议记录，用户同意后才执行，每会话最多提议一次。一眼可见的普通小 bug、纯聊天、知识问答不触发。
---

将当前对话中的踩坑信息整理并追加到 `~/projects/ai-configs/claude/pitfall/<分类>.md`。

---

## 触发方式

- **显式触发**：用户说"记坑"等关键词或 `/d-pitfall` → 直接进入 Step 1。
- **主动提议**（模型侦测）：一段排查刚收尾，且满足以下任一特征——① 多次尝试才定位根因；② 根因推翻了最初假设；③ 修法反直觉、文档未记载或与版本预期不符；④ 明显有未来复用价值。此时**只用一句话提议**（如：「这个坑值得记入 pitfall 吗？」），不预生成内容、不进入流程；用户同意后才进入 Step 1。
- **防骚扰**：每个会话最多主动提议一次；用户拒绝或未回应后本会话不再提议。一眼可见的普通小 bug 不提议。

---

## Step 1：提取信息

从当前对话上下文中提取以下内容：

- **标题**：一句话描述问题
- **现象**：触发问题的表象或报错
- **根因**：为什么会发生
- **解决**：如何解决
- **标签**：关键词（逗号分隔）

如果上下文信息不足，逐项询问用户补全。

---

## Step 2：推断分类

根据内容推断分类，按「撞到哪个技术对象的坑就进哪个文件」优先匹配：

- Go 相关 → `go.md`
- PostgreSQL 相关 → `postgresql.md`
- Redis / 缓存架构（TTL、多层缓存、key 设计、队列）→ `redis.md`
- SQLite 相关 → `sqlite.md`
- Python 语言 / 运行时 → `python.md`
- Docker / 容器相关 → `docker.md`
- Nginx 相关 → `nginx.md`
- Git 工作流（commit / 分支 / 撤销 / 协作）→ `git.md`
- Shell / 服务器运维操作（权限、部署、系统命令事故）→ `shell.md`
- **前端**（uni-app / 微信小程序 / CSS / 样式 / 布局 / 组件 / 输入等，**即便是通用 CSS / 浏览器机制，只要在前端场景踩到就归这**）→ `mp-weixin.md`
- 外部服务 API 集成（地图 / 支付 / IM / 云厂商 OSS 等接口的字段、配额、签名怪癖）→ `third-party-api.md`
- FastGPT 相关 → `fastgpt.md`
- Open WebUI / AI 界面工具（模型配置、工具服务器、系统提示注入等）→ `open-webui.md`
- AI 编程工具链（Claude Code / Codex CLI、终端渲染、逆向通道、本机 AI 环境与依赖）→ `ai-tooling.md`
- 架构或跨技术栈决策方法论 → `decisions.md`
- 以上都不匹配的孤例 → `general.md`

> 分类边界（避免分错）：
> - 产品专属文件优先于泛化分类：FastGPT / Open WebUI 的接口坑进各自专属文件，不进 `third-party-api.md`
> - 前端的坑——哪怕是通用 CSS / 浏览器机制（如 margin collapse）——一律进 `mp-weixin.md`，不要因为"机制通用"就丢进 `general.md`
> - 用某语言写的第三方 API 集成坑看坑的归属：坑在对方接口语义（字段类型、配额、签名）→ `third-party-api.md`；坑在语言 / 框架本身 → 对应语言文件
> - `general.md` 是最后手段，只收不匹配任何分类的孤例；当其中同主题条目攒到 2 条时，应提议新建分类（先修改本 SKILL.md 枚举，再迁移条目），不让模糊条目继续堆积

如果无法确定，询问用户。

**分类文件名安全约束**：只接受上方枚举列表中的固定文件名（`go.md` / `postgresql.md` / `redis.md` / `sqlite.md` / `python.md` / `docker.md` / `nginx.md` / `git.md` / `shell.md` / `mp-weixin.md` / `third-party-api.md` / `fastgpt.md` / `open-webui.md` / `ai-tooling.md` / `decisions.md` / `general.md`）。用户若提议其他名称 → 拒绝，告知用户当前枚举不可自由扩展；如确实需要新分类，先修改 d-pitfall SKILL.md 添加枚举项，而不是在本次会话中临时新建。

---

## Step 3：查重

**不通过 shell grep 查重**：标题关键词来自对话内容，若拼到 `grep "<关键词>"` 命令中，shell 会先解析双引号内的 `` `..` ``、`$(..)`、`$VAR`，可能触发命令执行；同时 grep 正则元字符也会引发意外匹配。

改用执行环境的文件读取工具（Claude Code 的 `Read` 工具、Codex 的 `view` 或等价文件读取工具）读取 `~/projects/ai-configs/claude/pitfall/<分类>.md` 全文，**在模型记忆里判重**——文件内容只通过工具参数传给 OS 读系统调用，跳过 shell 解析。

判重方式：
- 文件不存在 → 直接进入 Step 4
- 文件存在 → 读全文，按"标题语义 + 标签命中 + 现象/根因相似"判断；不要求字面完全匹配
- 文件过大（> 50KB）罕见，真遇到分块读

判断结果处理：
- 无相似条目 → 进入 Step 4
- 有相似条目 → 展示匹配条目，询问用户：
  1. **跳过**：已有记录，无需重复
  2. **补充**：在已有条目末尾追加新信息（如新的解决方案或补充说明）
  3. **新条目**：场景不同，作为独立条目写入

---

## Step 4：格式化并预览

整理为以下格式后展示给用户确认：

```markdown
## YYYY-MM-DD - <标题>

**现象**: <现象>
**根因**: <根因>
**解决**: <解决>
**标签**: <标签>
```

展示预览后，在请求确认前必须附加以下提示：

> ⚠️ 确认写入前，请检查以上内容不含密钥、token、数据库连接串、内网地址、请求体或其他敏感数据。此文件将进入版本控制，git 历史难以清除。

---

## Step 4.5：写入前预检查

**写入前必须确保 ai-configs 整个工作区清洁**——这是最初真实事故的根因（用户在项目 X 跑 d-pitfall，写入完未提交残留为 M，下次回 ai-configs 才发现）：

```bash
git -C ~/projects/ai-configs status --porcelain
```

- 输出为空 → 进入 Step 5
- 输出非空 → **不写入**，提示：
  ```
  ⚠️ ai-configs 工作区有未提交改动：
  <git status --porcelain 原样输出>
  请先回到 ai-configs 仓库处理这些改动后重试。
  ```

detached HEAD / upstream / .gitignore 等异常不前置拦截，留到 Step 6 commit / push 失败时由 git 自身报错并提示用户手动处理。

---

## Step 5：写入文件

用户确认且 Step 4.5 通过后，追加内容到 `~/projects/ai-configs/claude/pitfall/<分类>.md`，条目之间保留一个空行。文件不存在则自动创建。

---

## Step 6：固化到版本控制

### 6.1 用 `Write` 工具生成 commit message 文件

`<标题>` 来自对话内容，可能含反引号、`$()`、`$VAR` 等 shell 元字符——**绝不**拼进任何 shell 命令字符串。用 Claude Code 的 `Write` 工具（Codex 用 `apply_patch`）写入临时文件：

- 路径：`/tmp/d-pitfall-msg.<unix 时间戳>.txt`
- 内容：`docs(pitfall): <标题>` 加末尾换行

### 6.2 add + commit + push（**单次 Bash 调用，逐条门禁**）

```bash
git -C ~/projects/ai-configs add -- "claude/pitfall/<分类>.md" || exit 1
git -C ~/projects/ai-configs commit -F "/tmp/d-pitfall-msg.<unix 时间戳>.txt" || exit 1
rm -f "/tmp/d-pitfall-msg.<unix 时间戳>.txt"
git -C ~/projects/ai-configs push
```

- `rm` 只在 commit 成功后执行——commit 失败时临时文件保留，用户可手动 `git commit -F <file>` 重跑
- **不绕过 git 默认保护**：不 `add -A` / `add .` / `add -f`，不 `--amend` / `--no-verify`，不 `push --force` / `--force-with-lease` / `-u`
- 全部成功 → 输出 `✓ 已写入 + commit + push（hash: <abbreviated>）`
