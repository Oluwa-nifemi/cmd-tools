---
name: cw
description: Watch a GitHub Actions run by repo + workflow name. Resolves the latest run of a named workflow on the current (or given) branch and tails it via `gh run watch`.
user-invocable: false
---

# cw (CI watch)

A standalone bash script that wraps `gh run watch` with workflow-name resolution. Given a repo alias (or an inferred repo) and a workflow-name substring, it finds the latest run on the target branch and tails it, then sends a macOS notification on completion.

## How it works

1. Resolves the repo: from a `CW_REPO_ALIASES` entry, an explicit `owner/repo`, or `gh repo view` in the current git directory.
2. Resolves the workflow: case-insensitive substring match against `gh workflow list`. If multiple match, prints them and exits non-zero.
3. Resolves the branch: `-b <branch>` flag, or current git branch.
4. Fetches the latest run for that workflow + branch via `gh run list`.
5. Tails it via `gh run watch --exit-status` and notifies via `terminal-notifier`.

It also accepts a full GitHub Actions run URL or a bare numeric run ID for backward compatibility.

## Setup

```bash
# Add to PATH
export PATH="$HOME/Documents/work/cmd-tools/ciwatch:$PATH"

# Configure repo aliases (space-separated alias:owner/repo pairs)
export CW_REPO_ALIASES="api:myorg/api front:myorg/web py:myorg/monorepo"
```

## Usage

```bash
cw py ai_agents              # latest run of workflow matching "ai_agents" in py alias on current branch
cw api deploy -b main        # latest "deploy" workflow run on main
cw front ci                  # latest CI Checks run on current branch in front alias
cw                           # (inside a git repo) requires action arg, infers repo
cw https://github.com/.../runs/123   # legacy: watch by URL
cw 12345                     # legacy: watch by run id (repo inferred from cwd)
```

## Requirements

- `gh` (authenticated)
- `jq`
- `terminal-notifier` (macOS)
