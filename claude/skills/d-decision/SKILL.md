---
name: d-decision
description: 记录项目设计决策到当前项目的 docs/design/<模块>.md，自动 commit + push 固化。在确立设计原则、多方案权衡选定、引入非显然约束、明确"为什么不这样做"等场景触发。用户说"固化这个决策"、"记下这个设计选择"、"记下这个决定"、"/d-decision"时触发。纯聊天、知识问答、非决策场景不触发。
---

将当前对话中的设计决策整理并追加到**当前项目**的 `docs/design/<模块>.md`。

与 d-pitfall（写入 ai-configs 个人知识库）不同——d-decision 写入当前项目仓库，进入项目版本控制；记录的是"为什么这么设计"的业务/技术决策，不是踩坑记录。

---

## Step 0：检查环境

```bash
git rev-parse --show-toplevel 2>/dev/null
```

- 命令成功返回项目根目录 → 继续，后续所有路径以该根为基准
- 命令失败（非 git 仓库）→ 停止，提示用户："d-decision 只在 git 仓库内可用，请进入项目根目录后重试。"

---

## Step 1：提取信息

从当前对话上下文中提取以下内容：

- **标题**：一句话描述决策
- **背景**：为什么需要做这个决策（约束、触发原因、当前问题）
- **候选方案**：考虑过的方案（至少 2 个，包括"不做"也是候选）
- **权衡**：每个方案的优劣
- **决定**：选哪个，理由
- **失效条件**：什么情况下这个决策需要被重新评估
- **标签**：关键词（逗号分隔）

**「决定」和「失效条件」必填**——它们是决策固化的核心价值。其他字段信息不足时逐项询问用户补全。

---

## Step 2：推断模块归属

```bash
ls docs/design/ 2>/dev/null
```

按以下顺序确定写入文件（**只读已存在文件，不擅自创建新文件**）：

1. **优先复用已有文件**：根据决策内容匹配 `docs/design/` 下已存在的同名/同域文件（如 `auth.md`、`payment.md`）
2. **跨模块架构决策** → `docs/design/architecture.md`（如已存在）
3. **不匹配任何已有文件** → 询问用户：是否新建文件（提供文件名建议，小写连字符），还是归入已有的某个文件；用户明确同意后才创建新文件

按项目 `CLAUDE.md` 的"项目文档规范"：文件名一经确定不得自行新增、重命名或拆分。

---

## Step 3：查重

```bash
grep -i "<标题关键词>" docs/design/<模块>.md 2>/dev/null
```

用标题中的 2-3 个核心关键词搜索，不需要完整匹配。

- **文件不存在或无命中** → 直接进入 Step 4
- **有命中** → 展示匹配条目，询问用户：
  1. **跳过**：已有决策，无需重复
  2. **更新（推荐）**：原决策已变化，把原条目标记为「已废弃 YYYY-MM-DD，理由：<新决策原因>」并追加新决策（保留历史可追溯，不删除原内容）
  3. **新条目**：场景不同，作为独立决策写入
  4. **补充**：在原条目末尾追加新信息（如新发现的失效条件、新的权衡因素）

---

## Step 4：格式化并预览

整理为以下格式后展示给用户确认：

```markdown
## YYYY-MM-DD - <标题>

**背景**: <背景>

**候选方案**:
- 方案 A: <描述>
- 方案 B: <描述>

**权衡**:
- A: <优势> / <劣势>
- B: <优势> / <劣势>

**决定**: <选哪个，理由>

**失效条件**: <什么情况下需要重新评估这个决策>

**标签**: <标签>
```

展示预览后，在请求确认前必须附加以下提示：

> ⚠️ 确认写入前，请检查以上内容不含密钥、token、数据库连接串、内网地址、请求体、具体业务数据或其他敏感信息。此文件将进入项目版本控制，git 历史难以清除。

---

## Step 4.5：写入前预检查

业务项目工作区通常不清洁（用户正在改代码），但写入和 add 之前必须验证以下三件事，否则会污染用户暂存区或把已有/已删除内容卷入本次决策 commit：

```bash
# 检查 1：当前 staged 区必须为空（防止 git add 后和别的 staged 文件一起被 commit）
git diff --cached --quiet

# 检查 2：按目标文件的 tracked 状态分支判断
if git ls-files --error-unmatch docs/design/<模块>.md >/dev/null 2>&1; then
  # tracked → 无论文件当前是否存在，都必须没有 unstaged 改动
  # （覆盖三种异常：tracked 修改、tracked unstaged 删除、tracked + worktree 丢失）
  git diff --quiet -- docs/design/<模块>.md
else
  # untracked → 不能是已存在的草稿
  test ! -f docs/design/<模块>.md
fi
```

> **不要用 `test -f` 做前置**：`test -f` 在文件不存在时会短路跳过后续检查；当文件是 tracked 但被 unstaged 删除（worktree 里看不到、git 视角是 `D` 状态）时，`test -f` 为假，diff 检查被跳过，Step 5 会按"新建"创建并 add，把"删除 + 重建"作为一个变更卷入 commit。必须先用 `git ls-files` 定 tracked 状态，再走 diff 检查。

- 全部通过 → 进入 Step 5 写入
- 检查 1 失败（暂存区非空）→ **不写入，也不 add**，停止并输出：
  ```
  ⚠️ 当前 staged 区已有改动：
  <git diff --cached --name-only 输出>
  d-decision 不在脏暂存区操作，避免和其他 staged 文件一起被提交。
  请先 git commit 已 staged 的改动，或 git reset 取消暂存，再重试。
  ```
- 检查 2 失败（tracked 文件有 unstaged 改动 / 删除 / worktree 丢失）→ **不写入，也不 add**，停止并输出：
  ```
  ⚠️ docs/design/<模块>.md 是已跟踪文件，但存在未提交状态（修改 / 删除 / worktree 丢失）。
  d-decision 不会把它和本次操作一起提交。
  请先处理该文件状态（git commit / git stash / git restore / git checkout --）后重试。
  ```
- 检查 2 失败（untracked 已存在文件）→ **不写入，也不 add**，停止并输出：
  ```
  ⚠️ docs/design/<模块>.md 已存在但未被 git 跟踪（untracked）。
  d-decision 不会自动把 untracked 文件的现有内容卷入本次 commit。
  请先决定该文件的归属：
  - 想保留现有内容 → 手动 git add + commit 这份文件后再重试
  - 不想保留 → 删除该文件后再触发 d-decision（Step 2 会按"新建文件"流程询问你）
  ```

写入和 add **都在 Step 4.5 之后才发生**——预检查失败时绝对不能 `git add` 任何文件，否则会留下污染。

---

## Step 5：写入文件

Step 4.5 通过后，追加内容到项目根目录下的 `docs/design/<模块>.md`，条目之间保留一个空行。

- 文件已存在 → 在末尾追加，保留原有内容
- 文件不存在 → **仅当 Step 2 已获得用户明确同意新建时**才创建（含父目录 `docs/design/`）；未获同意时 Step 2 应已停止，不会进入 Step 5

---

## Step 6：固化到版本控制

Step 4.5 已确保 staged 区为空、目标文件无旧 unstaged 改动；Step 5 写入后只需直接 add + commit + push 即可（标准闭环，全局 Git 规范对此设有例外，见 `claude/CLAUDE.md` Git 规范章节）。

```bash
git add docs/design/<模块>.md
git commit -m "docs(design): <标题>"
git push
```

- 不得使用 `git add -A` 或 `git add .`
- commit 失败（pre-commit hook 拒绝等）→ 输出错误信息，提示用户手动处理；**不** `--amend`、**不** `--no-verify`
- push 失败（远端有新 commit、无远端 / 无权限等）→ 输出错误信息，提示用户手动 pull/合并；**不**强制 push
- 全部成功 → 输出：
  ```
  ✓ 已写入 docs/design/<模块>.md
  ✓ 已 commit + push（hash: <abbreviated>）
  工作区其他未提交改动保持不变。
  ```
