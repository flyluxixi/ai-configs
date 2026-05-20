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

## Step 5：写入文件

用户确认后，追加内容到 `~/projects/ai-configs/claude/pitfall/<分类>.md`，条目之间保留一个空行。文件不存在则自动创建。

---

## Step 6：固化到版本控制

写入成功后，d-pitfall 必须立即把改动 commit + push 到 ai-configs 仓库，避免遗留为未提交状态。这是 skill 的标准闭环，全局 Git 规范对此设有例外（见 `codex/AGENTS.md` Git 规范章节）。

### 6.1 防护闸：检查工作区清洁度

```bash
git -C ~/projects/ai-configs status --porcelain
```

- 输出**只**包含本次写入文件 `claude/pitfall/<分类>.md` 一行 M 或 ?? → 进入 6.2 自动提交
- 输出含其他文件改动（SKILL.md、AGENTS.md、其他 pitfall 文件、PROJECT_STATUS.md 等）→ **不自动提交**，输出以下提示后结束：
  ```
  ⚠️ ai-configs 工作区还有其他未提交改动，d-pitfall 不自动提交避免误伤。
  本次写入：~/projects/ai-configs/claude/pitfall/<分类>.md
  请稍后回到 ai-configs 仓库手动 commit。
  ```

### 6.2 自动 commit + push

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
