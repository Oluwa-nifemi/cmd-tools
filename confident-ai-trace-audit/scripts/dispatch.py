#!/usr/bin/env python3
"""Prepare one analyst brief per unit and track which findings are done.

The main agent spawns one sub-agent per brief (one unit each, never several units per
agent: small models lose focus across units). This script only writes briefs and reports
status; spawning happens in the agent, because only the agent can call its spawn tool.

Usage:
  dispatch.py prepare --audit <audit_dir> --context <context.md> [--units u1,u2]
  dispatch.py status  --audit <audit_dir>
  dispatch.py next    --audit <audit_dir> [--count 8]

Reads:  <audit_dir>/units.json, the skill's references/analyst-brief.md, --context file
Writes: <audit_dir>/briefs/<unit>.md; analysts write <audit_dir>/findings/<unit>.md
"""
import argparse
import json
import os
import re

SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BRIEF_TEMPLATE = os.path.join(SKILL_DIR, "references", "analyst-brief.md")
FINDINGS_TEMPLATE = os.path.join(SKILL_DIR, "assets", "findings-template.md")


def safe_name(value: str) -> str:
    # Must match digest.py so digest, brief, and findings files share one name.
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", value).strip("_")[:80] or "unit"


def load_units(audit: str) -> list:
    path = os.path.join(audit, "units.json")
    if not os.path.exists(path):
        raise SystemExit("units.json missing. Run digest.py first.")
    with open(path) as handle:
        return json.load(handle)


def findings_done(audit: str, unit: str) -> bool:
    path = os.path.join(audit, "findings", f"{safe_name(unit)}.md")
    # An analyst that crashed can leave an empty or stub file; require a summary.
    if not os.path.exists(path):
        return False
    with open(path) as handle:
        return "## Summary" in handle.read()


def prepare(audit: str, context_path: str, only: set) -> None:
    with open(BRIEF_TEMPLATE) as handle:
        template = handle.read()
    with open(FINDINGS_TEMPLATE) as handle:
        findings_template = handle.read()
    with open(context_path) as handle:
        context = handle.read().strip()
    audit_abs = os.path.abspath(audit)
    os.makedirs(os.path.join(audit, "briefs"), exist_ok=True)
    os.makedirs(os.path.join(audit, "findings"), exist_ok=True)
    written = 0
    for unit in load_units(audit):
        if only and unit["unit"] not in only:
            continue
        name = safe_name(unit["unit"])
        brief = (
            template.replace("{{CONTEXT}}", context)
            .replace("{{UNIT}}", unit["unit"])
            .replace("{{LABEL}}", unit.get("label") or "(none)")
            .replace("{{DIGEST}}", os.path.join(audit_abs, unit["file"]))
            .replace("{{METRICS}}", os.path.join(audit_abs, "trace_metrics.csv"))
            .replace("{{FINDINGS}}", os.path.join(audit_abs, "findings", f"{name}.md"))
            .replace("{{FINDINGS_TEMPLATE}}", findings_template.strip())
        )
        with open(os.path.join(audit, "briefs", f"{name}.md"), "w") as out:
            out.write(brief)
        written += 1
    print(f"wrote {written} briefs to {os.path.join(audit_abs, 'briefs')}")


def status(audit: str) -> list:
    pending = []
    done = 0
    for unit in load_units(audit):
        if findings_done(audit, unit["unit"]):
            done += 1
        else:
            pending.append(unit["unit"])
    print(f"findings done {done} / {done + len(pending)}")
    if pending:
        print("pending: " + ", ".join(pending))
    return pending


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    prep = sub.add_parser("prepare")
    prep.add_argument("--audit", required=True)
    prep.add_argument("--context", required=True, help="markdown with audit context, known effects to ignore, focus")
    prep.add_argument("--units", default="", help="comma list to (re)write only these units")
    stat = sub.add_parser("status")
    stat.add_argument("--audit", required=True)
    nxt = sub.add_parser("next")
    nxt.add_argument("--audit", required=True)
    nxt.add_argument("--count", type=int, default=8)
    args = parser.parse_args()

    if args.command == "prepare":
        prepare(args.audit, args.context, {u.strip() for u in args.units.split(",") if u.strip()})
    elif args.command == "status":
        status(args.audit)
    else:
        pending = status(args.audit)
        audit_abs = os.path.abspath(args.audit)
        for unit in pending[: args.count]:
            print(os.path.join(audit_abs, "briefs", f"{safe_name(unit)}.md"))


if __name__ == "__main__":
    main()

