# CLAUDE.md

Guidance for Claude Code when working in this repo.

## Repository overview

Personal command-line tools, each in its own subdirectory:
- `chat-migrate/cm` — copy/resume Claude Code chat sessions across project dirs; includes Zed/ACP session listing and tab-completion
- `ciwatch/cw` — watch GitHub Actions runs by workflow name; supports `--bg` (default), `--fg`, `--get`, `--status`
- `git-stack/gs` — stacked-branch git workflow
- `worktrees/wt` — git worktree manager
- `orchestrate/` — multi-mode orchestration skill, including the do → review → test pipeline for large builds, symlinked into `~/.claude/skills/orchestrate`
- `presentation/` — Claude Code skill: renders self-contained HTML decks/one-pagers, symlinked into `~/.claude/skills/presentation`
- `research/` — Claude Code skill: deep-dive research mode with living markdown doc, symlinked into `~/.claude/skills/research`

Most tools are single-file shell scripts; the three skill directories above are Claude Code skills (SKILL.md + supporting scripts/templates) rather than standalone CLIs. Iterate incrementally; no build step.

## Commenting rule

These scripts have to survive being picked up by a future-me (or future-Claude) months later, with no surrounding conversation. **Every non-obvious block needs a comment explaining the *why*, not just the *what*.** In particular:

- **Magic strings & regex patterns** — say where they come from. If you grep for `"entrypoint":"sdk-ts"`, note that it's how Claude Code tags SDK-launched (Zed/ACP) sessions in the JSONL.
- **Filter / skip rules** — say what's being filtered and why it's noise. A line like `_cm_is_noise "$file" && continue` is meaningless without the upstream helper explaining each category.
- **External behaviors being relied on** — e.g. "`exec` replaces the process so `claude --resume` returns control to the parent shell on exit." Future readers won't know which behaviors are load-bearing without it.
- **Workarounds for upstream quirks** — if you're routing around a Claude Code, zsh, or git behavior, name the quirk. Otherwise it looks like over-engineering and someone will "simplify" it back into a bug.
- **Deliberate duplications** — if the same pattern appears in two places because scoping prevents sharing (e.g. a function defined inside `cm()` not reachable from a completion function), say so explicitly, and leave a "keep in sync with X" pointer.

Default to comments that read like a colleague's hand-off note, not auto-generated doc. Prose is fine; aim for short paragraphs that say what surprised you while writing the code. Skip comments for genuinely self-evident lines — but err on the side of explaining when in doubt.

## Commit + push policy (overrides global rule)

After completing a self-contained change the user asked for in this repo, commit and push it as part of the same turn. Do not leave changes uncommitted or unpushed waiting for a follow-up request. This overrides the global "never commit without asking" rule for this repo only — the user has explicitly opted in here because work is small, scoped, and lives on `main`.

Exceptions where you still ask first:
- Work-in-progress changes the user is mid-iteration on (you can tell from context: they're still tweaking, the change isn't tested, etc.)
- Anything destructive (force push, history rewrite, branch deletion)
- Changes that touch files unrelated to the request

When committing, follow the existing commit style (short imperative subject, no Co-Authored-By trailer, no Claude Code footer).
