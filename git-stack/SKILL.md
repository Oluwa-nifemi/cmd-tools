---
name: gs
description: Stacked branch workflow tool. Use when the user wants to manage stacked git branches, commit with upstack propagation, navigate branch stacks, or track existing branches into a stack.
user-invocable: false
---

# gs (git-stack)

A CLI tool for managing stacked branches in git, with multi-commit support.

## Inspiration

This is inspired by [Graphite](https://graphite.dev) — a tool for stacked PRs where each branch represents a small, reviewable unit of work stacked on top of another.

The key difference: Graphite treats each branch as a single commit that gets amended with `gt modify`. We don't like that. Branches here can have **multiple commits**. `gs commit` adds a new commit to the current branch and then rebases all branches above it so changes propagate upward through the stack.

## How it works

A **stack** is a chain of branches where each branch knows its parent:

```
main → feat/api → feat/frontend → feat/tests
```

Metadata is stored in `.git/gs/` inside each repo:
- `.git/gs/config` — the trunk branch name (e.g. `main`)
- `.git/gs/branches/` — one file per tracked branch, containing its parent's name

When you commit to a lower branch, all branches above it are automatically rebased onto the new state. This is the core mechanic — changes flow upward.

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

gs ls                            # see the stack tree
gs log                           # see the stack with commit messages
gs push                          # push downstack to remote
```

## Retroactive tracking

Already have branches that form a stack but aren't tracked? Add them in bottom-to-top order:

```bash
gs track feat/api feat/frontend feat/tests
```

Or stack them onto a specific branch:

```bash
gs track feat/logging --onto feat/api
```

To quickly add a single branch on top of wherever you are:

```bash
gs stack feat/logging    # stacks it on your current branch
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
| `gs checkout <branch>` / `gs co` | Passthrough to git checkout |

### Viewing
| Command | Description |
|---------|-------------|
| `gs ls` / `gs list` | Show the stack as a tree with commit counts |
| `gs log` | Show the stack tree with commit hashes and messages |
| `gs diff [branch]` | Diff against parent branch (or a specified branch) |

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
| `gs track <b1> [b2] ... [--onto <branch>]` | Retroactively track existing branches as a stack |
| `gs stack <branch>` | Add a branch on top of the current one |
| `gs restack [--all \| --continue]` | Manually rebase upstack (use after raw git commands) |
| `gs move --onto <branch>` | Reparent current branch onto a different target |
| `gs untrack [branch]` | Remove from gs tracking, keep git branch |
| `gs fold` | Squash-merge current branch into its parent |
| `gs delete [branch]` | Delete branch from stack and git |
| `gs push` | Push from current branch downward through stack to remote |
| `gs push-pr` | Push downstack and create/update draft PRs (each targets its parent branch) |
| `gs pr` | Open the PR for current branch in browser |

## When to use `gs restack`

`gs commit` auto-restacks for you. You only need `gs restack` when you've used raw git commands (`git commit`, `git rebase`, `git amend`, etc.) and need to propagate those changes upward manually.

If a restack hits a conflict, resolve it, stage the files, then run `gs restack --continue`.
