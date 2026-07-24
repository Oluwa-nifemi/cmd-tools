---
name: gs
description: Stacked branch workflow tool. Use when the user wants to manage stacked git branches, commit with upstack propagation, navigate branch stacks, or track existing branches into a stack.
user-invocable: true
---

# gs (git-stack)

A CLI tool for managing stacked branches in git, with multi-commit support.

## Inspiration

Inspired by [Graphite](https://graphite.dev). The key difference: Graphite treats each branch as a single commit amended via `gt modify`. We don't like that — branches here can have **multiple commits**. `gs commit` adds a new commit and rebases all upstack branches so changes propagate upward.

## How it works

A **stack** is a chain of branches where each branch knows its parent:

```
main → feat/api → feat/frontend → feat/tests
```

Metadata lives in `.git/gs/`:
- `.git/gs/config` — trunk branch name (e.g. `main`)
- `.git/gs/branches/` — one file per tracked branch, containing its parent's name

## Typical workflow

```bash
gs init                          # set up in a repo (auto-detects main/master)

gs create feat/api -m "initial"  # new branch stacked on current
# ... make changes ...
gs commit -m "add endpoint"      # commit (multiple commits per branch!)
gs commit -m "add validation"    # another commit on the same branch

gs create feat/frontend          # stack another branch on top
# ... work on frontend ...
gs commit -m "add ui"

gs down                          # go back to feat/api
# ... fix something ...
gs commit -m "fix endpoint"      # feat/frontend auto-rebases on top

gs ls                            # see the stack tree with PR status
gs land                          # merge the bottom PR into trunk
gs sync                          # pull trunk, drop merged branches, restack
```

## Commands

### Setup
| Command | Description |
|---------|-------------|
| `gs init [--trunk <branch>]` | Initialize gs in current repo |

### Working
| Command | Description |
|---------|-------------|
| `gs create <name> [-m msg]` | Create a new branch stacked on current |
| `gs commit [-a] [-m msg]` | Commit and auto-restack all upstack branches |
| `gs rename <new-name>` | Rename the current branch and update tracking |
| `gs checkout <branch>` / `gs co` | Passthrough to git checkout |

### Viewing
| Command | Description |
|---------|-------------|
| `gs ls` / `gs list` | Show the stack tree with commit counts, PR status, and dirty state |
| `gs log` | Show the stack tree with commit hashes, messages, PR status, and dirty state |
| `gs diff [branch]` | Diff against parent branch (or a specified branch) |

PR status badges: `[open]`, `[merged]`, `[closed]`. Dirty branches show a `*` next to the name.

### Navigation
| Command | Description |
|---------|-------------|
| `gs up [N]` | Move up to child branch (prompts if multiple children) |
| `gs down [N]` | Move down to parent branch |
| `gs top` | Jump to topmost branch in current stack path |
| `gs bottom` | Jump to bottommost branch (nearest to trunk) |

### Stack management
| Command | Description |
|---------|-------------|
| `gs track <b1> [b2] ... [--onto <branch>]` | Track existing branches as a stack and auto-restack them |
| `gs stack <branch>` | Add a branch on top of the current one |
| `gs restack [--all] [--autostash] [--continue]` | Manually rebase upstack (use after raw git commands). `--autostash` stashes/restores a dirty working tree around the rebase chain |
| `gs move --onto <branch>` | Reparent current branch onto a different target |
| `gs insert <name> --between <parent> <child>` | Splice a new branch between an existing parent and child (validates `<child>` is currently stacked on `<parent>`) |
| `gs split <commit> <new-name>` | Split branch at a commit — rest becomes a new child branch |
| `gs fold` | Squash-merge current branch into its parent and clean up |
| `gs land [branch] [--squash\|--merge\|--rebase]` | Merge the bottommost PR into trunk (checks approval), pull, reparent children, delete branch |
| `gs delete [branch]` | Delete branch from stack and git, reparent children |
| `gs untrack [branch]` | Remove from gs tracking, keep git branch |

### Remote
| Command | Description |
|---------|-------------|
| `gs push [--all]` | Push from current branch downward through stack to remote (`--all` = every tracked branch, BFS from trunk) |
| `gs push-pr` | Push downstack and create/update draft PRs (titles from first commit message) |
| `gs pr` | Open the PR for current branch in browser |
| `gs sync` | Pull trunk, detect merged branches (squash-merge aware), reparent children, restack |

### Global flags
| Flag | Description |
|------|-------------|
| `gs --dry-run <command>` / `gs -n <command>` | Preview what would happen without changing anything. Works with `sync`, `land`, `fold`, `delete`. |

## When to use `gs restack`

`gs commit` auto-restacks for you. Use `gs restack` when you've used raw git commands (`git commit`, `git rebase`, `git amend`, etc.) and need to propagate changes manually.

If a restack hits a conflict, resolve it, stage the files, then run `gs restack --continue`. This now correctly processes all siblings of the conflicted branch, not just the resolved one.

## Tab completion

Zsh completion is available via `_gs` in the repo. To install:

```bash
cp git-stack/_gs ~/.zsh/completions/_gs
```

Completes subcommands, tracked branch names, flags (`--all`, `--autostash`, `--continue`, `--squash`, etc.), and commit hashes for `gs split`.

## Sharp edges

- **Scripting raw `git branch -f` after a rebase.** If you script branch updates yourself (e.g. `git rebase --onto X Y` followed by `git branch -f <branch> HEAD`), the `branch -f` is redundant and fails with `cannot force update the branch '<name>' used by worktree at <path>` for whichever branch is currently checked out — the rebase already moved that branch's ref in place. Drop the `branch -f` for the checked-out branch.
- **Reshaping a file mid-stack can silently duplicate content.** If an earlier branch in the stack renames, splits, or moves sections out of a file (e.g. `docs/x.md` → `docs/x/a.md` + `docs/x/b.md`), a later branch's commit that still patches the *old* file can apply its diff against whichever file now matches the surrounding context — landing content in the wrong place instead of failing. `gs restack` doesn't detect this (git's patch application is doing the locally "correct" thing). After reorganizing a file's shape partway through a stack, diff the final state of that file across all descendant branches to confirm nothing landed twice.

## Squash-merge handling

When a branch is squash-merged into trunk, its original commits have new SHAs. `gs sync` and `gs land` snapshot the merged branch's tip before deletion and rebase children with `--onto <parent> <merged_tip>`, so only the child's own commits are carried forward — no conflicts or duplicates.
