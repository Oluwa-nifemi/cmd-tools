# CLAUDE.md

Guidance for Claude Code when working in this repo.

## Repository overview

Personal command-line tools, each in its own subdirectory:
- `ciwatch/cw` — watch GitHub Actions runs by workflow name; supports `--bg` (default), `--fg`, `--get`, `--status`
- `git-stack/gs` — stacked-branch git workflow
- `worktrees/wt` — git worktree manager

Each tool is a single-file shell script. Iterate incrementally; no build step.

## Commit + push policy (overrides global rule)

After completing a self-contained change the user asked for in this repo, commit and push it as part of the same turn. Do not leave changes uncommitted or unpushed waiting for a follow-up request. This overrides the global "never commit without asking" rule for this repo only — the user has explicitly opted in here because work is small, scoped, and lives on `main`.

Exceptions where you still ask first:
- Work-in-progress changes the user is mid-iteration on (you can tell from context: they're still tweaking, the change isn't tested, etc.)
- Anything destructive (force push, history rewrite, branch deletion)
- Changes that touch files unrelated to the request

When committing, follow the existing commit style (short imperative subject, no Co-Authored-By trailer, no Claude Code footer).
