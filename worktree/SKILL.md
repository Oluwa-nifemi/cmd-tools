---
name: wt
description: Git worktree manager. Use when the user wants to create, switch, list, rename, clean up, or push from git worktrees.
user-invocable: false
---

# wt (worktree manager)

A shell function for creating and managing git worktrees with minimal friction. Sourced into your shell (not a standalone script) so it can `cd` into worktrees.

## How it works

`wt` creates worktrees in a configured base directory (`WT_WORKTREES_DIR/<repo-name>/<branch-name>`), hard-links configurable ignored files (`CLAUDE.local.md`, `.env*`, etc.) from the main worktree into each new one, and `cd`s in.

Files are **hard-linked** (same inode), so edits in any worktree are visible everywhere. This is intentional — these are shared config files. Directories in the glob list get **symlinked** (macOS can't hard-link directories).

## Setup

Configuration is via environment variables:

| Variable | Purpose | Default |
|----------|---------|---------|
| `WT_WORKTREES_DIR` | Base directory for all worktrees | Must be set (via `wt install`) |
| `WT_LINK_IGNORED` | Space-separated globs to hard-link from main worktree | `CLAUDE.local.md .env*` |

```bash
# Source it (add to .zshrc)
source /path/to/cmd-tools/worktree/wt

# One-time setup (writes export into ~/.zshrc)
wt install ~/Documents/Programming/worktrees
```

## Commands

| Command | Description |
|---------|-------------|
| `wt create <name> [base]` | Create a worktree for a new branch, link ignored files, cd in. `base` defaults to current branch. |
| `wt c <name> [base]` | Shortcut for `wt create` |
| `wt switch [name]` | Switch to a worktree by branch name. Substring match — `wt switch auth` matches `feat/add-auth`. No argument shows interactive picker (fzf if available, numbered list fallback). Single match jumps directly. |
| `wt list` | List all worktrees (passthrough to `git worktree list`) |
| `wt rename <old> <new>` | Rename a worktree's directory and its branch atomically. Works with branch names containing `/`. |
| `wt clean [name] [--force]` | Remove a worktree and delete its branch. Defaults to current worktree. `--force` skips the uncommitted-changes check. |
| `wt clean --merged` | Remove all worktrees whose branches have been merged. Checks `gh pr view` (squash-merge aware) then falls back to `git branch --merged`. |
| `wt push [remote-branch]` | Push to remote, defaults to same branch name. |
| `wt install <path>` | Set `WT_WORKTREES_DIR`, persist as an export in `~/.zshrc`. |
| `wt --help` / `wt -h` | Show usage. |

## Branch names with slashes

Branch names like `feat/api` create nested directory structures under the worktrees dir. `wt switch`, `wt clean`, and `wt rename` all handle these correctly — the full branch name (including slashes) is preserved.
