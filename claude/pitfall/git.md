# Git 踩坑记录

## 2026-05-17 - Commit 引用一致性：main.go/DI 文件引用了未 commit 的方法导致服务器构建失败

**现象**: 本地 build 通过，commit + push 后服务器 git pull 构建失败：`main.go:163 listingHandler.MarkRented undefined`。
**根因**: 本地 `main.go` 改动里包含了之前会话遗留的路由注册（引用 `listing_handler.go` 的新方法），但 `listing_handler.go` 仍是 modified 未 commit 状态。`git add main.go` 时只看修改文件没看引用关系，把"路由声明"commit 了，"方法实现"留在工作区。本地 build 正常因为本地工作区是完整的，远端 pull 拿到的是不一致的快照。
**解决**: commit 前对 staged 文件做引用一致性自检——`git diff --staged` 看实际改动；特别检查路由注册（main.go）、DI 注入、struct 字段、方法调用等"声明 vs 实现"分离位置。涉及多文件协同改动时确认所有引用方和被引用方一起 staged，或拆成多个原子 commit。
**标签**: git, commit, staged, 服务器部署, 构建失败, 引用一致性

## 2026-05-26 - git checkout -- 含他人未提交修改的文件会一并覆盖

**现象**: working tree 里某个文件同时存在"自己改了一部分 + 别人未提交一部分"时，跑 `git checkout -- <file>` / `git restore --worktree <file>` / `git reset --hard` 撤销自己加的那段，结果把别人的未提交修改也一并覆盖丢失。
**根因**: 这三条命令是**全文件粒度**操作——不区分"哪几行是你改的、哪几行是别人改的"，统一把 working tree 还原到 index（或 HEAD）状态。working tree 覆盖通常无法恢复（没 stash 过 + 没 reflog 痕迹）。
**解决**:
1. **首选**：用 Edit 工具按行精修，只撤掉自己加的那段
2. **备选**：`git stash --keep-index` 暂存 working tree 全部改动，操作 index 后 `git stash pop` 恢复
3. **极端备选**：`git add -p` / `git checkout -p` 选择性操作（交互式，AI 助手在 Bash 里不能跑）
4. **预防**：操作 git 撤销类命令前，**先 `git diff <file>` 确认 working tree 哪些改动是自己的、哪些是别人的**。文件 diff 里有自己不熟的内容时，绝对不能用 `git checkout --` / `git restore` / `git reset --hard`
**标签**: git, working-tree, checkout, restore, reset, user-modifications, ai-collaboration
