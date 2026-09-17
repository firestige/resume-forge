---
name: git-commit
description: 'Use for git commit and push workflow in this workspace. Apply when checking changed files, staging only task-related changes, writing commit messages to a temp file, committing with git commit -F, and pushing after confirmation.'
argument-hint: 'Repository path, staged scope, and commit purpose'
user-invocable: true
disable-model-invocation: false
---

# Git Commit

## When to Use
- 需要在当前仓库提交修改。
- 需要检查哪些改动属于本次任务，避免把无关文件混入提交。
- 需要按仓库约束使用终端里的 `git` / `gh` CLI，而不是其他 MCP git 服务。
- 需要用临时文件组织 commit message，再通过 `git commit -F` 提交。

## Goal
- 提交边界清晰。
- commit message 结构稳定、可复用。
- 推送动作在用户明确需要时再执行。

## 强制规则

- **禁止**使用任何 MCP git 服务（`mcp_gitkraken_*`）执行提交/推送操作
- **必须**使用 `run_in_terminal` 直接调用 `git` / `gh` CLI
- **必须**将 commit message 写入临时文件，然后用 `git commit -F <file>` 提交，禁止用 `-m "..."` 传递多行消息（shell 会截断或误解义）

## 完整工作流

### Step 1 — 确认变更范围

```bash
cd <repo-root>
git status --short
git diff --stat HEAD
```

### Step 2 — 暂存文件

```bash
# 精确暂存（推荐）：
git add <file1> <file2> ...

# 或全量暂存（仅当所有变更均属本次任务时）：
git add -A
```

### Step 3 — 写 commit message 到临时文件

使用 `create_file` 工具写入 `/tmp/<slug>-commit-msg.txt`。

格式（Conventional Commits）：
```
<type>(<scope>): <title line, ≤72 chars>

<body: 每条变更一行，以 "- " 开头>

<footer: 关联 issue / breaking change 说明（可选）>
```

常用 type：`feat` `fix` `refactor` `test` `chore` `docs` `build`

示例：
```
feat(jobs): add example-tech backend variant

- analysis: extract JD keywords and register two open risks
- variant: reorder projects and override skills narrative
- status: move current_stage to applied

Build: make job JOB=2026-01-example-tech-backend
```

### Step 4 — 提交

```bash
git commit -F /tmp/<slug>-commit-msg.txt
```

验证：
```bash
git log --oneline -3
```

### Step 5 — 推送（可选，需用户确认）

```bash
git push origin main
```

或用 GitHub CLI：
```bash
gh repo view --web   # 打开仓库页面确认
gh pr create --fill  # 若在 feature branch 上
```

---

## 错误处理

| 问题 | 解决 |
|------|------|
| shell 残留 dquote> 状态 | 新开 terminal 或 `Ctrl-C`；再重新 `git add` + `git commit -F` |
| commit message 文件已存在 | 用 `replace_string_in_file` 覆盖，或用不同 slug |
| `git add` 后发现遗漏文件 | `git add <file>` 追加暂存，再 `git commit -F` |
| 需要修改最后一次 commit | `git add <fixup-file> && git commit --amend -F /tmp/<slug>-commit-msg.txt` |

---

## 禁止事项

```bash
# ❌ 禁止：多行 -m（shell 截断风险）
git commit -m "feat: xxx
K3: ...
K4: ..."

# ❌ 禁止：MCP 调用
mcp_gitkraken_git_add_or_commit(...)
mcp_gitkraken_git_push(...)

# ❌ 禁止：未确认 status 直接 git add -A（可能混入无关文件）
```

## 注意事项

- commit message 临时文件路径用 `/tmp/<sprint-or-feature-slug>-commit-msg.txt`，避免不同任务冲突
- 每次提交前先 `git status --short` 核对暂存区，不混入构建产物（`build/`、`*.o`、`Pods/`）
- 若 `.gitignore` 未覆盖某类产物，先修 `.gitignore` 再提交
