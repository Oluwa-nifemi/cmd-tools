#!/usr/bin/env python3
"""Bridge Claude guidance files and compatible skills into Codex.

This script is intentionally conservative:
- It only creates AGENTS.md -> CLAUDE.md links for directories that have
  CLAUDE.md and no AGENTS.md.
- It links compatible repo-local Claude skills into repo-local .agents/skills.
- It never overwrites a real file or an existing symlink.
- It writes a manifest only in apply mode.
- Verify mode re-scans the tree and reports unresolved Claude-only guidance,
  conflicts, Claude-only automation, skill bridge status, and global-memory status.
"""

from __future__ import annotations

import argparse
import json
import os
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable


DEFAULT_PRUNE_NAMES = {
    ".git",
    "node_modules",
    "target",
    ".venv",
    "venv",
    "__pycache__",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    "dist",
    "build",
}

DEFAULT_PRUNE_PATH_PARTS = {
    "worktrees",
    "file-history",
    "plugins/cache",
    "tmp",
}


CLAUDE_ONLY_SKILL_MARKERS = {
    ".claude/hooks",
    ".claude/agents",
    ".claude/commands",
    "claude code",
    "claude-code",
    "claude.ai/code",
    "claude-specific",
    "claude-only",
    "hooks/",
}


@dataclass
class Action:
    action: str
    status: str
    directory: str
    source: str | None = None
    target: str | None = None
    reason: str | None = None


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def is_under(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False


def should_prune(path: Path, root: Path, include_worktrees: bool) -> bool:
    if path.name in DEFAULT_PRUNE_NAMES:
        return True
    rel_parts = path.relative_to(root).parts if is_under(path, root) else path.parts
    if include_worktrees:
        return any(part in DEFAULT_PRUNE_PATH_PARTS - {"worktrees"} for part in rel_parts)
    return any(part in DEFAULT_PRUNE_PATH_PARTS for part in rel_parts)


def iter_dirs(root: Path, include_worktrees: bool) -> Iterable[Path]:
    for current, dirs, _files in os.walk(root, followlinks=False):
        current_path = Path(current)
        dirs[:] = [
            d
            for d in dirs
            if not should_prune(current_path / d, root, include_worktrees)
        ]
        yield current_path


def find_repo_root(directory: Path, scan_root: Path) -> Path:
    current = directory
    while True:
        if (current / ".git").exists():
            return current
        if current == scan_root or current.parent == current:
            break
        current = current.parent
    try:
        rel = directory.relative_to(scan_root)
        first = rel.parts[0] if rel.parts else "."
        return scan_root if first == "." else scan_root / first
    except ValueError:
        return scan_root


def find_git_repo_root_or_scan_root(directory: Path, scan_root: Path) -> Path:
    current = directory
    while True:
        if (current / ".git").exists():
            return current
        if current == scan_root or current.parent == current:
            return scan_root
        current = current.parent


def link_target_for(agents: Path, claude: Path, absolute: bool) -> str:
    if absolute:
        return str(claude)
    return os.path.relpath(claude, start=agents.parent)


def symlink_target_for(target: Path, source: Path, absolute: bool) -> str:
    if absolute:
        return str(source)
    return os.path.relpath(source, start=target.parent)


def scan(root: Path, include_worktrees: bool, absolute_links: bool) -> tuple[list[Action], dict[str, list[Action]]]:
    actions: list[Action] = []
    per_repo: dict[str, list[Action]] = {}

    for directory in iter_dirs(root, include_worktrees):
        claude = directory / "CLAUDE.md"
        agents = directory / "AGENTS.md"
        has_claude = claude.exists() or claude.is_symlink()
        has_agents = agents.exists() or agents.is_symlink()

        if has_claude and not has_agents:
            action = Action(
                action="create-symlink",
                status="planned",
                directory=str(directory),
                source=str(claude),
                target=str(agents),
                reason=f"create {agents.name} -> {link_target_for(agents, claude, absolute_links)}",
            )
        elif has_claude and has_agents:
            if agents.is_symlink():
                action = Action(
                    action="skip",
                    status="already-linked",
                    directory=str(directory),
                    source=str(claude),
                    target=str(agents),
                    reason=f"AGENTS.md already symlinked to {os.readlink(agents)}",
                )
            else:
                action = Action(
                    action="skip",
                    status="conflict",
                    directory=str(directory),
                    source=str(claude),
                    target=str(agents),
                    reason="CLAUDE.md and real AGENTS.md both exist; inspect semantically",
                )
        else:
            continue

        actions.append(action)
        repo = find_repo_root(directory, root)
        per_repo.setdefault(str(repo), []).append(action)

    return actions, per_repo


def skill_compatibility_reason(skill_dir: Path) -> str | None:
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.exists():
        return "missing SKILL.md"
    try:
        text = skill_md.read_text(encoding="utf-8").lower()
    except UnicodeDecodeError:
        return "SKILL.md is not valid UTF-8"

    matched_markers = sorted(marker for marker in CLAUDE_ONLY_SKILL_MARKERS if marker in text)
    if matched_markers:
        return f"mentions Claude-only runtime surface(s): {', '.join(matched_markers)}"
    return None


def iter_claude_skills(root: Path, include_worktrees: bool) -> Iterable[Path]:
    for directory in iter_dirs(root, include_worktrees):
        skills_dir = directory / ".claude" / "skills"
        if not skills_dir.is_dir():
            continue
        for child in sorted(skills_dir.iterdir()):
            if child.is_dir():
                yield child


def scan_skills(
    root: Path,
    include_worktrees: bool,
    absolute_links: bool,
    codex_skills_dir: Path,
) -> tuple[list[Action], dict[str, list[Action]]]:
    actions: list[Action] = []
    per_repo: dict[str, list[Action]] = {}

    for skill_dir in iter_claude_skills(root, include_worktrees):
        skill_name = skill_dir.name
        target = codex_skills_dir / skill_name
        incompatible_reason = skill_compatibility_reason(skill_dir)
        repo = find_git_repo_root_or_scan_root(skill_dir, root)

        if incompatible_reason:
            action = Action(
                action="skip-skill",
                status="needs-adaptation",
                directory=str(skill_dir),
                source=str(skill_dir),
                target=str(target),
                reason=incompatible_reason,
            )
        elif target.is_symlink():
            target_path = target.readlink()
            resolved_target = target_path if target_path.is_absolute() else (target.parent / target_path).resolve()
            if resolved_target.resolve() == skill_dir.resolve():
                action = Action(
                    action="create-skill-symlink",
                    status="already-linked",
                    directory=str(skill_dir),
                    source=str(skill_dir),
                    target=str(target),
                    reason=f"Codex skill already symlinked to {target_path}",
                )
            else:
                action = Action(
                    action="create-skill-symlink",
                    status="conflict",
                    directory=str(skill_dir),
                    source=str(skill_dir),
                    target=str(target),
                    reason=f"Codex skill name already symlinks elsewhere: {target_path}",
                )
        elif target.exists():
            action = Action(
                action="create-skill-symlink",
                status="conflict",
                directory=str(skill_dir),
                source=str(skill_dir),
                target=str(target),
                reason="Codex skill target already exists and is not a symlink",
            )
        else:
            action = Action(
                action="create-skill-symlink",
                status="planned",
                directory=str(skill_dir),
                source=str(skill_dir),
                target=str(target),
                reason=f"create Codex skill {target} -> {symlink_target_for(target, skill_dir, absolute_links)}",
            )

        actions.append(action)
        per_repo.setdefault(str(repo), []).append(action)

    return actions, per_repo


def global_memory_action(home: Path) -> Action:
    codex_agents = home / ".codex" / "AGENTS.md"
    claude_md = home / ".claude" / "CLAUDE.md"

    if not claude_md.exists():
        return Action(
            action="global-memory",
            status="skipped",
            directory=str(codex_agents.parent),
            target=str(codex_agents),
            reason="no ~/.claude/CLAUDE.md found",
        )
    if codex_agents.is_symlink():
        target = codex_agents.readlink()
        target_path = target if target.is_absolute() else (codex_agents.parent / target).resolve()
        if target_path.resolve() == claude_md.resolve():
            return Action(
                action="global-memory",
                status="exists",
                directory=str(codex_agents.parent),
                source=str(claude_md),
                target=str(codex_agents),
                reason="~/.codex/AGENTS.md already symlinks to ~/.claude/CLAUDE.md",
            )
        return Action(
            action="global-memory",
            status="conflict",
            directory=str(codex_agents.parent),
            source=str(claude_md),
            target=str(codex_agents),
            reason=f"~/.codex/AGENTS.md symlinks elsewhere: {target}",
        )
    if codex_agents.exists():
        return Action(
            action="global-memory",
            status="planned",
            directory=str(codex_agents.parent),
            source=str(claude_md),
            target=str(codex_agents),
            reason="replace generated ~/.codex/AGENTS.md file with symlink to ~/.claude/CLAUDE.md",
        )
    return Action(
        action="global-memory",
        status="planned",
        directory=str(codex_agents.parent),
        source=str(claude_md),
        target=str(codex_agents),
        reason="create ~/.codex/AGENTS.md symlink to ~/.claude/CLAUDE.md",
    )


def write_global_memory(home: Path) -> Action:
    action = global_memory_action(home)
    if action.status != "planned":
        return action
    codex_dir = home / ".codex"
    codex_dir.mkdir(parents=True, exist_ok=True)
    source = Path(action.source or "")
    target = Path(action.target or "")
    if target.exists() and not target.is_symlink():
        backup = target.with_name(f"{target.name}.codex-claude-bridge-backup")
        backup.write_bytes(target.read_bytes())
        target.unlink()
    target.symlink_to(source)
    action.status = "created"
    return action


def apply_actions(actions: list[Action], absolute_links: bool) -> list[Action]:
    applied: list[Action] = []
    for action in actions:
        if action.action not in {"create-symlink", "create-skill-symlink"} or action.status != "planned":
            applied.append(action)
            continue
        source = Path(action.source or "")
        target = Path(action.target or "")
        if target.exists() or target.is_symlink():
            action.status = "skipped"
            action.reason = "target appeared before apply; not overwriting"
            applied.append(action)
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        if action.action == "create-symlink":
            link_target = link_target_for(target, source, absolute_links)
        else:
            link_target = symlink_target_for(target, source, absolute_links)
        target.symlink_to(link_target)
        action.status = "created"
        applied.append(action)
    return applied


def write_manifests(per_repo: dict[str, list[Action]], root: Path, mode: str) -> list[str]:
    written: list[str] = []
    for repo_str, repo_actions in per_repo.items():
        repo = Path(repo_str)
        if not is_under(repo, root) and repo != root:
            continue
        manifest_dir = repo / ".codex"
        manifest_dir.mkdir(parents=True, exist_ok=True)
        manifest = manifest_dir / "claude-bridge-manifest.json"
        payload = {
            "generated_at": utc_now(),
            "mode": mode,
            "repo": str(repo),
            "actions": [asdict(action) for action in repo_actions],
        }
        manifest.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        written.append(str(manifest))
    return written


def claude_only_surfaces(root: Path, include_worktrees: bool) -> list[str]:
    patterns = [
        ".claude/hooks",
        ".claude/agents",
        ".claude/commands",
        ".claude/skills",
    ]
    found: list[str] = []
    for directory in iter_dirs(root, include_worktrees):
        text = str(directory)
        if any(pattern in text for pattern in patterns):
            found.append(text)
    return sorted(set(found))


def build_report(
    root: Path,
    mode: str,
    actions: list[Action],
    manifests: list[str],
    global_action: Action | None,
    include_worktrees: bool,
) -> dict:
    planned = [a for a in actions if a.status == "planned"]
    created = [a for a in actions if a.status == "created"]
    conflicts = [a for a in actions if a.status == "conflict"]
    already = [a for a in actions if a.status == "already-linked"]
    skill_actions = [a for a in actions if "skill" in a.action]
    needs_adaptation = [a for a in actions if a.status == "needs-adaptation"]
    return {
        "generated_at": utc_now(),
        "mode": mode,
        "root": str(root),
        "summary": {
            "planned": len(planned),
            "created": len(created),
            "conflicts": len(conflicts),
            "already_linked": len(already),
            "manifests_written": len(manifests),
            "claude_only_surfaces": len(claude_only_surfaces(root, include_worktrees)),
            "skill_actions": len(skill_actions),
            "skills_needing_adaptation": len(needs_adaptation),
        },
        "global_memory": asdict(global_action) if global_action else None,
        "manifests": manifests,
        "actions": [asdict(action) for action in actions],
    }


def action_label(action: Action, root: Path) -> str:
    """Return a compact, human-facing label for a bridge action.

    The JSON output keeps full paths for automation. The default CLI output is
    for a person at a terminal, so prefer skill names and repo-relative paths
    over repeating long absolute paths on every line.
    """
    if action.action == "create-skill-symlink":
        return Path(action.source or action.directory).name

    directory = Path(action.directory)
    try:
        relative_directory = directory.relative_to(root)
    except ValueError:
        return str(directory)
    return "." if str(relative_directory) == "." else str(relative_directory)


def print_action_group(title: str, actions: list[Action], root: Path) -> None:
    if not actions:
        return
    print(f"{title}:")
    for action in actions:
        label = action_label(action, root)
        if action.status == "needs-adaptation" and action.reason:
            print(f"  - {label} — {action.reason}")
        elif action.status == "conflict" and action.reason:
            print(f"  - {label} — {action.reason}")
        else:
            print(f"  - {label}")


def print_human_report(report: dict, root: Path) -> None:
    summary = report["summary"]
    mode = report["mode"]
    repo_name = root.name
    actions = [Action(**action) for action in report["actions"]]

    created = [action for action in actions if action.status == "created"]
    planned = [action for action in actions if action.status == "planned"]
    conflicts = [action for action in actions if action.status == "conflict"]
    needs_adaptation = [action for action in actions if action.status == "needs-adaptation"]

    guidance_actions = [
        action
        for action in created + planned
        if action.action == "create-symlink"
    ]
    skill_actions = [
        action
        for action in created + planned
        if action.action == "create-skill-symlink"
    ]

    print(f"codex-claude-bridge {mode}: {repo_name}")
    print(
        "summary: "
        f"{summary['created']} created, "
        f"{summary['planned']} planned, "
        f"{summary['conflicts']} conflicts, "
        f"{summary['already_linked']} already linked, "
        f"{summary['skills_needing_adaptation']} skills need adaptation"
    )

    if report["global_memory"]:
        global_action = Action(**report["global_memory"])
        print(f"global memory: {global_action.status} — {global_action.reason}")

    print_action_group("guidance links", guidance_actions, root)
    print_action_group("skill links", skill_actions, root)
    print_action_group("skills needing adaptation", needs_adaptation, root)
    print_action_group("conflicts", conflicts, root)

    if report["manifests"]:
        print("manifest:")
        for manifest in report["manifests"]:
            print(f"  {manifest}")

    if (
        not guidance_actions
        and not skill_actions
        and not needs_adaptation
        and not conflicts
        and not report["manifests"]
    ):
        print("nothing to do")


def main() -> int:
    parser = argparse.ArgumentParser(description="Bridge Claude guidance and compatible skills into Codex.")
    parser.add_argument("--root", default=os.getcwd(), help="Workspace or repo root to scan.")
    parser.add_argument("--dry-run", action="store_true", help="Print proposed changes without writing.")
    parser.add_argument("--apply", action="store_true", help="Create safe symlinks and write manifests.")
    parser.add_argument("--verify", action="store_true", help="Re-scan and print verification report.")
    parser.add_argument("--include-worktrees", action="store_true", help="Include worktrees directories in the scan.")
    parser.add_argument("--absolute-links", action="store_true", help="Use absolute symlink targets instead of relative targets.")
    parser.add_argument("--global-memory", action="store_true", help="Include ~/.codex/AGENTS.md global memory note planning/apply.")
    parser.add_argument("--no-bridge-skills", action="store_true", help="Do not link compatible repo-local .claude/skills into Codex skills.")
    parser.add_argument("--codex-skills-dir", help="Codex skills directory to link compatible Claude skills into. Defaults to <root>/.agents/skills.")
    parser.add_argument("--json", action="store_true", help="Emit JSON only.")
    args = parser.parse_args()

    selected_modes = [args.dry_run, args.apply, args.verify]
    if sum(bool(x) for x in selected_modes) != 1:
        parser.error("Choose exactly one of --dry-run, --apply, or --verify.")

    root = Path(args.root).expanduser().resolve()
    if not root.exists():
        parser.error(f"root does not exist: {root}")

    actions, per_repo = scan(root, args.include_worktrees, args.absolute_links)
    if not args.no_bridge_skills:
        codex_skills_dir = (
            Path(args.codex_skills_dir).expanduser().resolve()
            if args.codex_skills_dir
            else root / ".agents" / "skills"
        )
        skill_actions, skill_per_repo = scan_skills(
            root,
            args.include_worktrees,
            args.absolute_links,
            codex_skills_dir,
        )
        actions.extend(skill_actions)
        for repo, repo_actions in skill_per_repo.items():
            per_repo.setdefault(repo, []).extend(repo_actions)
    manifests: list[str] = []
    global_action: Action | None = None

    if args.global_memory:
        global_action = global_memory_action(Path.home())

    mode = "dry-run"
    if args.apply:
        mode = "apply"
        actions = apply_actions(actions, args.absolute_links)
        if args.global_memory:
            global_action = write_global_memory(Path.home())
        # Refresh per-repo statuses after apply for accurate manifests.
        by_directory_and_target = {(a.directory, a.target): a for a in actions}
        for repo_actions in per_repo.values():
            for index, action in enumerate(repo_actions):
                repo_actions[index] = by_directory_and_target.get((action.directory, action.target), action)
        manifests = write_manifests(per_repo, root, mode)
    elif args.verify:
        mode = "verify"

    report = build_report(root, mode, actions, manifests, global_action, args.include_worktrees)

    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print_human_report(report, root)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
