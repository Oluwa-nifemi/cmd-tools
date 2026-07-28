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

## Agent-created worktrees (Codex)

`wt` also manages worktrees it didn't create. Codex puts its worktrees at
`WT_WORKTREES_DIR/codex/<4-hex-session-id>/<repo-name>` — the repo name is the
*last* component, the middle segment is an opaque id, and the worktree is often
left on a **detached HEAD** with no branch name at all. The old name-derivation
(strip the `WT_WORKTREES_DIR/<repo>/` prefix) produced full absolute paths as
"names", which made `wt switch` unusable.

Discovery now goes through a single scanner (`_wt_scan`) that labels every
linked worktree regardless of who made it:

| Worktree kind | Label shown |
|---|---|
| Created by `wt` | Relative name under `WT_WORKTREES_DIR/<repo>/` (= branch name) |
| Codex, with a known thread | The **Codex thread title** — e.g. `Fix Token Limit` |
| Codex, no thread found | Branch name, else `detached@<short-sha>` |

Codex titles come from joining two files Codex already maintains: each rollout
JSONL's first line carries `cwd` + `session_id`, and `~/.codex/session_index.jsonl`
maps `session_id` → the thread name shown in the app. The lookup reads only the
first line of each rollout (`rg -m1`), so it stays ~60ms even over a 1&nbsp;GB
sessions directory, and degrades silently to branch/sha labels if `rg` or the
Codex dirs are absent. When a worktree dir has been reused by several sessions,
the newest session's title wins.

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
| `wt create` | With no name, prompts for the worktree/branch name and base branch (base defaults to the current branch). Empty name aborts. |
| `wt c <name> [base]` | Shortcut for `wt create` |
| `wt switch [name\|number]` | Switch to a worktree. Substring match against **label, branch, and Codex session id** — `wt switch auth`, `wt switch AI-1557`, and `wt switch 2d54` all work, as does a Codex thread title (`wt switch "Fix Token"`). A bare number picks that row from `wt list`. No argument shows the interactive picker. Single match jumps directly. |
| `wt main` | Jump back to the main worktree. |
| `wt list` | Numbered, column-headed table of all linked worktrees: `NAME`, `BRANCH`, `SOURCE` (`codex <id>` / `external`), `STATUS`. The numbers are what `wt switch <number>` takes. |
| `wt rename <old> <new>` | Rename a worktree's directory and its branch atomically. Works with branch names containing `/`. |
| `wt clean [name] [--force]` | Remove a worktree and delete its branch. Defaults to current worktree. `name` is resolved with the same fuzzy match as `switch` (so it works on Codex worktrees too) and refuses to act on an ambiguous match. Detached worktrees are removed without a branch delete. `--force` skips the uncommitted-changes check. |
| `wt clean --merged` | Remove all worktrees whose branches have been merged. Checks `gh pr view` (squash-merge aware) then falls back to `git branch --merged`. |
| `wt push [remote-branch]` | Push to remote, defaults to same branch name. |
| `wt install <path>` | Set `WT_WORKTREES_DIR`, persist as an export in `~/.zshrc`. |
| `wt --help` / `wt -h` | Show usage. |

## `wt list` table

Columns are headed, so no cell needs a legend to interpret:

| Column | Meaning |
|---|---|
| `NAME` | What to type: Codex thread title, or the branch/dir name |
| `BRANCH` | The checked-out branch. `-` means *same as NAME*; `(detached)` means no branch |
| `SOURCE` | `codex <id>` for a Codex worktree, `external` for another non-`wt` one, blank for `wt`'s own |
| `STATUS` | `uncommitted` when tracked files have changes. Untracked files don't count — build output would otherwise flag every worktree |

Two rendering rules, both learned from the table reading badly:

- **No blank cells.** An earlier version blanked `BRANCH` whenever it equalled the
  name — true for every `wt`-created worktree — so most rows were a name followed
  by a stretch of whitespace and the table looked half-empty. Identical branches
  now collapse to `-`, which reads as "same as NAME" rather than "missing".
- **Widths measured, columns dropped.** Column widths come from the rows actually
  being shown (headers included), and a column that is empty for every row is
  omitted entirely — a repo with no agent worktrees shows just `NAME` and
  `BRANCH`, with no empty `SOURCE`/`STATUS` headers. The footer legend likewise
  only explains notation that's on screen.

## Tab completion

`wt install` automatically installs zsh tab completion:
- Completes subcommands (`create`, `switch`, `main`, `rename`, etc.)
- Completes worktree names for `switch`, `rename`, and `clean` — driven by the
  same `_wt_scan` the commands use, so Codex worktrees and thread titles are
  offered too, annotated with their branch/origin
- `clean` also completes `--force` and `--merged`

Completion offers **every spelling the command accepts**, as three groups:
the label (Codex thread title or branch), the branch name when it differs from
the label, the Codex session id, and the row number from `wt list`. This matters
because zsh completion matches candidates by *prefix* — offering only labels
meant `wt switch 26<TAB>` completed nothing even though `wt switch 26fe` worked,
since `26fe` doesn't appear in the label `Clojure Agent Sol`. Titles containing
spaces are escaped automatically.

The picker (`wt switch` with no unique match) uses `fzf` when available, with a
preview pane showing recent commits and dirty files for the highlighted
worktree; otherwise it falls back to the numbered list.

## Branch names with slashes

Branch names like `feat/api` create nested directory structures under the worktrees dir. `wt switch`, `wt clean`, and `wt rename` all handle these correctly — the full branch name (including slashes) is preserved.

## Usage from Claude Code

`wt` is a shell function, not in Claude's PATH — but it can be sourced directly in a Bash tool call:

```bash
source /Users/Oluwanifemi/Documents/work/cmd-tools/worktree/wt && wt create feat/my-branch
```

The `cd` at the end of `wt create` has no effect on Claude's working directory (subshell), but the worktree is created correctly at `WT_WORKTREES_DIR/<repo-name>/<branch-name>`. The `CLAUDE.local.md` glob error is harmless when the file doesn't exist.
