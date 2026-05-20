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

---

## Step 3：查重

推断出分类文件路径后，检查该文件是否存在重复或相似条目：

```bash
grep -i "<标题关键词>" ~/projects/ai-configs/claude/pitfall/<分类>.md 2>/dev/null
```

用标题中的 2-3 个核心关键词搜索，不需要完整匹配。

- **文件不存在或无命中** → 直接进入 Step 4
- **有命中** → 展示匹配到的条目，询问用户：
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

为避免把用户已有的未提交改动（包括目标文件自身的旧改动）混入本次 commit，**写入前必须确保 ai-configs 整个工作区清洁**：

```bash
git -C ~/projects/ai-configs status --porcelain
```

- 输出为空（工作区清洁）→ 进入 Step 5 写入
- 输出非空 → **不写入**，停止并输出：
  ```
  ⚠️ ai-configs 工作区有未提交改动：
  <git status --porcelain 原样输出>
  d-pitfall 不在脏工作区写入，避免污染本次 commit。
  请先回到 ai-configs 仓库处理这些改动后重试。
  ```

仅看"目标文件是否只显示一行 M"判断不够安全——目标文件本来可能就是 M（用户之前手动改过没提交），追加后还是一行 M，会被误判为清洁并把旧改动一起提交。

---

## Step 5：写入文件

用户确认且 Step 4.5 通过后，追加内容到 `~/projects/ai-configs/claude/pitfall/<分类>.md`，条目之间保留一个空行。文件不存在则自动创建。

---

## Step 6：固化到版本控制

Step 4.5 已确保写入前工作区清洁，所以 Step 5 之后工作区只会多出本次写入文件的一行变更，可以直接 commit + push（标准闭环，全局 Git 规范对此设有例外，见 `codex/AGENTS.md` Git 规范章节）。

```bash
git -C ~/projects/ai-configs add claude/pitfall/<分类>.md
git -C ~/projects/ai-configs commit -m "docs(pitfall): <标题>"
git -C ~/projects/ai-configs push
```

- commit 失败（pre-commit hook 拒绝等）→ 输出错误信息，提示用户手动处理；**不** `--amend`、**不** `--no-verify`
- push 失败（远端有新 commit 等）→ 输出错误信息，提示用户手动 pull/合并；**不**强制 push
- 全部成功 → 输出：
  ```
  ✓ 已写入 ~/projects/ai-configs/claude/pitfall/<分类>.md
  ✓ 已 commit + push（hash: <abbreviated>）
  ```
