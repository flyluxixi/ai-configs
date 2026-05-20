---
name: d-pitfall
description: 记录技术踩坑或决策踩坑到个人知识库。用户说"记录这个坑"、"记一下这个坑"、"把这个坑记下来"、"记坑"、"/d-pitfall"时触发。纯聊天、知识问答、非踩坑场景不触发。
---

将当前对话中的踩坑信息整理并追加到 `~/projects/ai-configs/claude/pitfall/<分类>.md`。

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

根据内容推断分类，文件名使用小写连字符：

- Go 相关 → `go.md`
- PostgreSQL 相关 → `postgresql.md`
- PHP / Webman 相关 → `php.md`
- Nginx 相关 → `nginx.md`
- 架构或跨技术栈决策 → `decisions.md`
- 其他 → `general.md`

如果无法确定，询问用户。

**分类文件名安全约束**：只接受上方枚举列表中的固定文件名（`go.md` / `postgresql.md` / `php.md` / `nginx.md` / `decisions.md` / `general.md`）。用户若提议其他名称 → 拒绝，告知用户当前枚举不可自由扩展；如确实需要新分类，先修改 d-pitfall SKILL.md 添加枚举项，而不是在本次会话中临时新建。

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

`<标题>` 来自对话内容，可能含反引号、`$()`、`$VAR` 等 shell 元字符——**绝不**拼进任何 shell 命令字符串。用 Codex 的 `apply_patch` 工具写入临时文件：

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
