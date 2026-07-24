---
name: wt
description: Git worktree manager. Use when the user wants to create, switch, list, rename, clean up, or push from git worktrees.
user-invocable: false
---

# wt (worktree manager)

A shell function for creating and managing git worktrees with minimal friction. Sourced into your shell (not a standalone script) so it can `cd` into worktrees.

## How it works

`wt` creates worktrees in a configured base directory (`WT_WORKTREES_DIR/<repo-name>/<branch-name>`), hard-links configurable ignored files (`CLAUDE.md`, `CLAUDE.local.md`, `.env*`, etc.) from the main worktree into each new one, and `cd`s in.

Files are **hard-linked** (same inode), so edits in any worktree are visible everywhere. This is intentional — these are shared config files. Directories in the glob list get **symlinked** (macOS can't hard-link directories).

## Setup

Configuration is via environment variables:

| Variable | Purpose | Default |
|----------|---------|---------|
| `WT_WORKTREES_DIR` | Base directory for all worktrees | Must be set (via `wt install`) |
| `WT_LINK_IGNORED` | Space-separated globs to hard-link from main worktree | `CLAUDE.md CLAUDE.local.md .claude .env* .rtk` |

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

## Tab completion

`wt install` automatically installs zsh tab completion:
- Completes subcommands (`create`, `switch`, `rename`, etc.)
- Completes worktree names for `switch`, `rename`, and `clean`
- `clean` also completes `--force` and `--merged`

## Branch names with slashes

Branch names like `feat/api` create nested directory structures under the worktrees dir. `wt switch`, `wt clean`, and `wt rename` all handle these correctly — the full branch name (including slashes) is preserved.

## Usage from Claude Code

`wt` is a shell function, not in Claude's PATH — but it can be sourced directly in a Bash tool call:

```bash
source /Users/Oluwanifemi/Documents/work/cmd-tools/worktree/wt && wt create feat/my-branch
```

The `cd` at the end of `wt create` has no effect on Claude's working directory (subshell), but the worktree is created correctly at `WT_WORKTREES_DIR/<repo-name>/<branch-name>`. The `CLAUDE.local.md` glob error is harmless when the file doesn't exist.
