---
name: d-decision
description: 记录项目设计决策到当前项目的 docs/design/<模块>.md，自动 commit + push 固化。在确立设计原则、多方案权衡选定、引入非显然约束、明确"为什么不这样做"等场景触发。用户说"固化这个决策"、"记下这个设计选择"、"记下这个决定"、"/d-decision"时触发。纯聊天、知识问答、非决策场景不触发。
---

将当前对话中的设计决策整理并追加到**当前项目**的 `docs/design/<模块>.md`。

与 d-pitfall（写入 ai-configs 个人知识库）不同——d-decision 写入当前项目仓库，进入项目版本控制；记录的是"为什么这么设计"的业务/技术决策，不是踩坑记录。

---

## Step 0：检查环境

需要确认两件事：处于 git 仓库 + 当前 HEAD 是命名 branch（不是 detached）。

```bash
git rev-parse --show-toplevel 2>/dev/null
git symbolic-ref --quiet --short HEAD 2>/dev/null
```

- 第一条失败（非 git 仓库）→ 停止，提示用户："d-decision 只在 git 仓库内可用，请进入项目根目录后重试。"
- 第二条失败（HEAD 处于 detached 状态：rebase / bisect / checkout 到 commit / 部分 worktree 用法等）→ 停止，提示用户：
  ```
  ⚠️ 当前 HEAD 处于 detached 状态，不在任何命名 branch 上。
  在此状态下 commit 会创建孤立提交（dangling commit），push 也无目标 branch。
  请先 git checkout <branch> 或 git switch <branch> 切到正常 branch 后重试。
  ```

### 工作目录约定

后续每条 Bash 命令必须以下面前缀开头：

```bash
cd "$(git rev-parse --show-toplevel)" || exit 1
```

每次 Bash 调用是独立 shell，变量不跨调用保留——cwd 必须每次显式切换。

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

**必填字段拒答处理**：用户拒绝补充「决定」或「失效条件」（明确回复"算了"、"先这样"、"跳过"或不再响应）→ 停止 skill，**不写入、不提交**；告知用户："必填字段缺失，d-decision 终止。决策记录需要明确'选什么 + 何时失效'才有长期价值；若暂时只想留个备忘，可考虑用 /d-pitfall。"

---

## Step 2：推断模块归属

```bash
cd "$(git rev-parse --show-toplevel)" || exit 1
find docs/design -maxdepth 1 -type f -name '*.md' 2>/dev/null
```

只列出顶层 markdown 文件，避免把子目录、`.gitkeep`、非 md 草稿混进候选。

按以下顺序确定写入文件（**只读已存在文件，不擅自创建新文件**）：

1. **优先复用已有文件**：根据决策内容匹配 `docs/design/` 下已存在的同名/同域文件（如 `auth.md`、`payment.md`）
2. **跨模块架构决策** → `docs/design/architecture.md`（如已存在）
3. **不匹配任何已有文件** → 询问用户：是否新建文件（提供文件名建议，小写连字符），还是归入已有的某个文件；用户明确同意后才创建新文件

按项目 `AGENTS.md` 的"项目文档规范"：文件名一经确定不得自行新增、重命名或拆分。

**模块文件名安全约束**：

- 文件名必须匹配正则 `^[a-z0-9][a-z0-9-]*\.md$`（首字符小写字母或数字，后跟小写字母 / 数字 / 连字符，`.md` 结尾）
- 不允许空格、`/`、`..`、`;`、`$`、`(`、`)`、`` ` ``、`'`、`"`、`\`、控制字符等任何 shell / 路径敏感字符
- 用户提供或已有的文件名若不符合 → **停止 skill**，提示用户重命名后重试，**不擅自规整文件名**
- 后续所有 shell 命令引用文件路径时统一形式：`-- "docs/design/<模块>.md"`（用 `--` 分隔选项与位置参数，用双引号保留路径完整性——前提是文件名已通过正则校验，不含 shell 元字符）

---

## Step 3：查重

**不通过 shell grep 查重**：用户决策标题来自对话上下文，若直接拼到 `grep "<关键词>"` 命令中，shell 会先于 grep 解析双引号内的 `` `...` ``、`$(...)`、`$VAR`，可能触发命令执行或变量展开。

改用执行环境的文件读取工具（Claude Code 的 Read 工具、Codex 的 view/读取等价工具），把 `docs/design/<模块>.md` 全文直接读出，**在模型记忆里判重**——文件内容只通过工具参数传给 OS 读系统调用，不经过 shell 解析。

判重方式：
- 文件不存在 → 直接进入 Step 4
- 文件存在 → 读全文，模型按"标题语义 + 标签命中 + 决策对象相同"三个维度判断是否有重复/相似条目；不要求字面完全匹配
- 文件特别大（> 50KB / > 1000 行）的情况实际罕见；真遇到时分块读，仍不用 grep

判断结果处理：
- 无相似条目 → 进入 Step 4
- 有相似条目 → 展示匹配条目，询问用户：
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

业务项目工作区通常不清洁（用户正在改代码），但写入和 add 之前必须验证以下五件事，否则会污染用户暂存区、把已有/已删除内容卷入本次决策 commit、被 .gitignore 拒绝、或在写完之后才发现 push 不出去：

```bash
cd "$(git rev-parse --show-toplevel)" || exit 1

# 检查 -1：当前 branch 必须有 upstream（写入前就要确定能 push，否则会留下"已写未提交"半完成状态）
git rev-parse --abbrev-ref --symbolic-full-name @{u} 2>/dev/null

# 检查 0：目标文件路径不能被 .gitignore 屏蔽（d-decision 永不用 git add -f 强加）
! git check-ignore -q -- "docs/design/<模块>.md"

# 检查 1：当前 staged 区必须为空（防止 git add 后和别的 staged 文件一起被 commit）
git diff --cached --quiet

# 检查 2：按目标文件的 tracked 状态分支判断
if git ls-files --error-unmatch -- "docs/design/<模块>.md" >/dev/null 2>&1; then
  # tracked → 无论文件当前是否存在，都必须没有 unstaged 改动
  # （覆盖三种异常：tracked 修改、tracked unstaged 删除、tracked + worktree 丢失）
  git diff --quiet -- "docs/design/<模块>.md"
else
  # untracked → 不能是已存在的草稿
  test ! -f "docs/design/<模块>.md"
fi
```

- 全部通过 → 进入 Step 5 写入
- 检查 -1 失败（无 upstream）→ **不写入，也不 add**，停止并输出：
  ```
  ⚠️ 当前 branch <branch> 没有 upstream 配置，git push 会失败。
  d-decision 不擅自指定远端，也不自动 git push -u 设置 upstream。
  请先手动跑一次 git push -u origin <branch> 建立 upstream，然后重新触发 /d-decision。
  ```
- 检查 0 失败（路径被 .gitignore 屏蔽）→ **不写入，也不 add**，停止并输出：
  ```
  ⚠️ docs/design/<模块>.md 被 .gitignore 屏蔽，无法通过 git 正常跟踪。
  d-decision 永不使用 git add -f 强加 ignored 文件。
  请先调整 .gitignore（删除相应规则），或为决策文档使用其他不被忽略的目录后重试。
  ```
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

Step 4.5 已确保 upstream 存在、路径未被 ignore、staged 区为空、目标文件无旧 unstaged 改动；Step 5 已写入；本步骤完成 add + commit + push（标准闭环，全局 Git 规范对此设有例外，见 `codex/AGENTS.md` Git 规范章节）。

### 6.1 用 `Write` 工具生成 commit message 文件

`<标题>` 来自对话内容，可能含反引号、`$()`、`$VAR` 等 shell 元字符——**绝不**拼进任何 shell 命令字符串。用 Codex 的 `apply_patch` 工具写入临时文件：

- 路径：`/tmp/d-decision-msg.<unix 时间戳>.txt`
- 内容：`docs(design): <标题>` 加末尾换行

### 6.2 add + commit + push（**单次 Bash 调用，逐条门禁**）

```bash
cd "$(git rev-parse --show-toplevel)" || exit 1
git add -- "docs/design/<模块>.md" || exit 1
git commit -F "/tmp/d-decision-msg.<unix 时间戳>.txt" || exit 1
rm -f "/tmp/d-decision-msg.<unix 时间戳>.txt"
git push
```

- `rm` 只在 commit 成功后执行——commit 失败时临时文件保留，用户可 `git commit -F <file>` 手动重跑
- **不绕过 git 默认保护**：不 `add -A` / `add .` / `add -f`，不 `--amend` / `--no-verify`，不 `push --force` / `--force-with-lease` / `-u`
- 全部成功 → 输出 `✓ 已 commit + push（hash: <abbreviated>）；工作区其他未提交改动保持不变`
