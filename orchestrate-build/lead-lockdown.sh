#!/usr/bin/env bash
# lead-lockdown.sh — PreToolUse hook for the orchestrate-build skill.
#
# Enforces "the orchestrator is a pure router." Declared in the orchestrate-build
# skill frontmatter, so it is auto-scoped to orchestration and never runs in
# normal sessions.
#
# LEAD ONLY — by nature: this PreToolUse hook fires for the MAIN session's tool
# calls only. Subagent (teammate) tool calls do NOT reach it at all (verified
# empirically), so teammates are inherently unrestricted — the skill relies on
# that, not on per-call detection. The agent_id/agent_type allow below is just a
# harmless defensive no-op: current payloads never carry those keys, but if a
# future Claude Code ever DID run this hook for subagents with an agent marker,
# it keeps them unblocked rather than misclassifying them as the lead.
#
# Blocks on lead:  large Reads, `git diff`, Edit/Write/NotebookEdit.
# Allows on lead:  small Reads, git status/add/commit, everything else.
#
# Exit 0 = allow, exit 2 = block (stderr shown to the model). No jq needed.
# Fails CLOSED on write tools if the payload is unparseable; open otherwise.

# Read the hook JSON from stdin into an env var, then hand it to Python.
HOOK_JSON="$(cat)"
export HOOK_JSON
export ORCHESTRATE_MAX_READ_BYTES="${ORCHESTRATE_MAX_READ_BYTES:-12288}"

python3 <<'PY'
import os, sys, json, re

data = os.environ.get("HOOK_JSON", "")
max_bytes = int(os.environ.get("ORCHESTRATE_MAX_READ_BYTES", "12288"))

def allow(): sys.exit(0)
def block(msg): print(msg, file=sys.stderr); sys.exit(2)

try:
    obj = json.loads(data)
except Exception:
    if re.search(r'"tool_name"\s*:\s*"(Edit|Write|NotebookEdit)"', data):
        block("orchestrate-build: unparseable hook input for a write tool; blocking to stay safe.")
    allow()

tool = obj.get("tool_name", "")

# Defensive no-op (see header): if a payload ever carries an agent marker,
# treat it as a teammate and allow. Current payloads never do — the hook is
# lead-only by nature — so this simply never fires today.
if obj.get("agent_id") or obj.get("agent_type"):
    allow()

# ---- LEAD ----
ti = obj.get("tool_input", {}) or {}

if tool in ("Edit", "Write", "NotebookEdit"):
    wpath = ti.get("file_path") or ti.get("path") or ""
    wnorm = os.path.expanduser(wpath).replace("\\", "/")
    wbase = os.path.basename(wnorm)
    home = os.path.expanduser("~").replace("\\", "/")

    # The lead MAY write its own bookkeeping / memory / config — none of which
    # is production code. Everything legit lives under .claude / ~/.claude, the
    # build folder, or is a top-level instructions/skill file.
    lead_writable = (
        wnorm.startswith(home + "/.claude/")   # global: auto-memory (MEMORY.md), user config
        or "/.claude/" in wnorm                # project: skills, guardrails, conventions
        or wnorm.startswith(".claude/")
        or "/local/" in wnorm                  # build folder: orchestrator log + index
        or wnorm.startswith("local/")
        or wbase in ("CLAUDE.md", "SKILL.md", "MEMORY.md", "index.md",
                     "orchestrator-log.md", "guardrails.md", "conventions.md")
        or "orchestrator-log" in wbase
    )
    # But never let "bookkeeping" be a backdoor into the code tree: if the path
    # is clearly a source dir, block regardless.
    in_code_tree = any(
        seg in wnorm.split("/") for seg in ("libs", "src", "tests", "test", "app", "cmd", "pkg", "internal")
    )
    if lead_writable and not in_code_tree:
        allow()
    block("orchestrate-build: the orchestrator does not write production code. It may write only its own log/index/memory/skill files (.claude, the build folder). Dispatch a doer for code edits.")

if tool == "Read":
    path = ti.get("file_path") or ti.get("path") or ""
    base = os.path.basename(path)
    # Path rule is primary: the orchestrator is a pure router and must never
    # read reports or the log — those are teammate-write / audit-read only,
    # regardless of size (a normal report is ~14-16KB, right at any size gate).
    # Reports are named per-unit-per-role in practice (pb-review.md, pb-doer.md,
    # <unit>-<role>.md) and/or live under a reports/ dir, so match on the role
    # suffix and the dir, not just a literal "reports.md".
    ALLOW_READ_BASENAMES = {"index.md", "conventions.md", "guardrails.md"}
    if base in ALLOW_READ_BASENAMES:
        allow()

    norm = path.replace("\\", "/")
    is_report = (
        base == "reports.md"
        or re.search(r'-(review|doer|reviewer)\.md$', base) is not None
        or "/reports/" in norm
        or norm.startswith("reports/")
    )
    is_log = "orchestrator-log" in base
    if is_report or is_log:
        kind = "the log" if is_log else "a report/review"
        block(f"orchestrate-build: the orchestrator does not read {kind} ('{base}'). These are teammate-write / audit-read only. Route to the doer via the section pointer, or spawn an audit agent post-run — do not read it yourself.")

    # Catch-all size cap for anything else (accidental huge reads). Generous —
    # this is a backstop, not the primary gate. Reports/log are already handled
    # above by path, so this won't false-block a normal report.
    if path and os.path.isfile(path):
        try:
            size = os.path.getsize(path)
        except OSError:
            allow()
        if size > max_bytes:
            block(f"orchestrate-build: '{path}' is {size}B (> {max_bytes}B). The orchestrator reads only the index/pointers. Route this to a teammate — do not read a large file whole.")
    allow()

if tool == "Bash":
    cmd = ti.get("command", "") or ""
    if re.search(r'(^|[;&|]|\s)git\s+([^;&|]*\s)?diff(\s|$)', cmd):
        block("orchestrate-build: the orchestrator does not run 'git diff'. Use 'git status --short' for commit prep, or route a diff spot-check to a teammate.")
    allow()

allow()
PY
