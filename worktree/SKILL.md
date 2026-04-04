---
name: wt
description: Git worktree manager. Use when the user wants to create, list, clean up, or push from git worktrees.
user-invocable: false
---

# wt (worktree manager)

A shell function for creating and managing git worktrees with minimal friction.

## How it works

`wt` creates worktrees in a configured base directory (`WT_WORKTREES_DIR/<repo-name>/`), copies over `.env` files and `CLAUDE.local.md` from the main repo, and `cd`s into the new worktree.

Since it needs to change your shell's directory, it's a sourced shell function (not a standalone script).

## Setup

```bash
# Source it (add to .zshrc)
source /path/to/graphite/worktree/wt

# Set your worktrees directory (writes directly into the source file)
wt --install ~/Documents/Programming/worktrees
```

## Commands

| Command | Description |
|---------|-------------|
| `wt <name> [base-branch]` | Create a worktree, copy .env files, and cd into it |
| `wt --list` | List all worktrees |
| `wt --clean [--force]` | Remove current worktree and delete its branch |
| `wt --push [remote-branch]` | Push to remote (defaults to same branch name) |
| `wt --install <path>` | Set the base directory for worktrees (self-modifying) |
