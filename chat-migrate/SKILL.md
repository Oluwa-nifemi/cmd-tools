---
name: cm
description: Copy a Claude Code chat session from the current project dir into another project's dir, rewriting embedded absolute paths. Use when the user wants to duplicate, move, or migrate a chat between working directories.
user-invocable: false
---

# cm (chat-migrate)

Copies a Claude Code session JSONL from the current project's session dir into the target project's session dir, rewriting the embedded absolute paths so the chat resumes cleanly in the new location.

## Why it exists

Claude Code stores per-project sessions under `~/.claude/projects/<abs-path-with-slashes-as-dashes>/<session-id>.jsonl` and embeds the absolute project path inside the JSONL. So a session can't simply be opened from a different cwd — the file has to live in the right project dir *and* its embedded paths have to match.

The logic is lifted from `wt clean`'s `_wt_migrate_threads` helper but generalized: any two project dirs, not just worktree→main.

## Usage

```bash
cm list [N|all]                   # list sessions in cwd's project dir, newest first (default 10)
cm <id-or-title> <target-path>    # duplicate the chat into target's project dir
cm <id-or-title> <target-path> --move   # same, but delete the source after a successful copy
```

Default is **duplicate** — the original is untouched. `--move` only deletes after the copy + path-rewrite succeed.

## How matching works

The `<id-or-title>` argument is resolved in three passes; first hit wins:

1. **Session-id prefix** — e.g. `070503f3` matches `070503f3-0334-4cf3-bf2c-70e946af93c1`
2. **Exact custom-title** — titles set via Claude's `/rename` are stored inline as `{"type":"custom-title","customTitle":"…"}` entries; the latest wins
3. **Title substring**

Ambiguous matches refuse to act and list the candidates so you can narrow.

`cm list` shows the title for renamed sessions and a first-user-message preview for untitled ones — pick the id from there if needed.

## Safety choices

- **Refuses to overwrite** an existing destination file (paranoia against corrupted half-copies)
- **Target path must already exist** as a directory — won't conjure arbitrary project dirs
- **Refuses same-path** source/target
- **`--move` deletes only after** the copy succeeds

## Install

```bash
source /path/to/cmd-tools/chat-migrate/cm
```

(Already wired into `~/.zshrc` on this machine.)
