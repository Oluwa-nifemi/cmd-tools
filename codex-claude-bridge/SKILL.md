---
name: codex-claude-bridge
description: Bridge repo-local Claude guidance and compatible skills into Codex by creating safe AGENTS.md links from existing CLAUDE.md files, linking compatible .claude/skills into Codex skills, logging a manifest, and performing an agent semantic verification pass. Use when asked to make a workspace or repo Codex-ready from Claude files, sync Claude instructions/skills for Codex, audit or apply CLAUDE.md to AGENTS.md symlinks, or verify a Claude-to-Codex migration. Global memory bridging is a separate one-time maintenance mode via --global-memory, not part of normal repo bridging.
---

# Codex Claude Bridge

Use this skill to make a repo or workspace Codex-ready from existing Claude guidance and compatible Claude skills.

The bundled script handles deterministic filesystem work. The agent handles semantic judgment after the script runs.

## Workflow

1. Identify the scan root. Default to the current workspace root unless the user gives a narrower repo path.
2. Run a dry run first.
3. Review the proposed actions and conflicts.
4. Apply only if the user has asked you to proceed with changes.
5. Run verify.
6. Perform an agent semantic verification pass from the manifest and filesystem.

## Script

Use:

```bash
python3 <skill-dir>/scripts/codex_claude_bridge.py --root <path> --dry-run
python3 <skill-dir>/scripts/codex_claude_bridge.py --root <path> --apply
python3 <skill-dir>/scripts/codex_claude_bridge.py --root <path> --verify
```

Add `--json` when another tool or subagent should consume the output.

Default behavior:

- Create `AGENTS.md -> CLAUDE.md` only when a directory has `CLAUDE.md` and no `AGENTS.md`.
- Do not create the reverse `CLAUDE.md -> AGENTS.md`.
- Never overwrite existing real files or symlinks.
- Prune common generated/vendor paths and `worktrees` by default.
- Write `.codex/claude-bridge-manifest.json` per repo in apply mode.
- Plan or create symlinks from compatible repo-local `.claude/skills/<name>` folders into repo-local `.agents/skills/<name>` by default.
- Flag skills as `needs-adaptation` instead of linking when `SKILL.md` appears to depend on Claude-only runtime surfaces.

Use `--include-worktrees` only when the user explicitly wants generated worktrees handled too.

Use `--absolute-links` only when the user prefers personal-machine absolute links over portable relative links.

Use `--no-bridge-skills` only when the user wants guidance files bridged without exposing compatible Claude skills to Codex.

Use `--codex-skills-dir <path>` when testing or when Codex skills should be linked somewhere other than repo-local `.agents/skills`.

Use `--global-memory` only for explicit one-time personal setup or repair of `~/.codex/AGENTS.md -> ~/.claude/CLAUDE.md`. Do not include it in routine repo bridging examples or normal repo skill syncs.

## Agent semantic verification

After `--apply`, do not stop at “the script succeeded.” Verify semantics:

- Read each written `.codex/claude-bridge-manifest.json`.
- Inspect every `conflict` action where both `CLAUDE.md` and `AGENTS.md` exist.
- Spot-check a representative sample of created links with `ls -l` or `readlink`.
- Check whether any linked `CLAUDE.md` contains Claude-only concepts that Codex may not honor, especially hooks, agents, commands, MCP assumptions, permissions, or model names.
- Check repo-local `.claude/skills`, `.claude/hooks`, `.claude/agents`, and `.claude/commands` separately. Confirm each linked skill is genuinely Codex-compatible, and inspect every `needs-adaptation` skill.
- Report whether each Claude-only or incompatible case is safe as a symlink, should become an adapted real `AGENTS.md`, or should remain Claude-only.

## Global guidance

This is not part of normal repo bridging. Codex supports personal global guidance at `~/.codex/AGENTS.md`; `--global-memory` is a one-time setup/repair mode for that global file. For this user, keep one global source of truth:

- `~/.claude/CLAUDE.md` is the canonical global guidance file.
- `~/.codex/AGENTS.md` should be a symlink to `~/.claude/CLAUDE.md`.

Do not rely on Claude-style `@file.md` includes inside `AGENTS.md`; Codex may treat them as plain text. If useful memory-index items exist in `~/.claude/MEMORY.md`, merge the useful summary into `~/.claude/CLAUDE.md` instead of pointing Codex at `MEMORY.md`.

If `~/.codex/AGENTS.md` already exists as a generated real file, the script should back it up and replace it with the symlink. If it exists as a symlink to some other target, treat that as a conflict and report it.

## Completion report

Return:

- Dry-run summary: planned links, conflicts, existing links, global-memory status.
- Apply summary: created links, manifests written, skipped items.
- Verify summary: remaining Claude-only files, semantic conflicts, Claude-only automation, skill links, and skills needing adaptation.
- Exact paths to any manifests and the bridge script.
