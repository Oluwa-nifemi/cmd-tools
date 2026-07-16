# orchestrate-build lead lockdown — install & notes

## Files
- `SKILL.md` — updated skill (pure-router token economy, index/pointer scheme,
  blind-append log, lead-never-reads-reviews, idle-ack gotcha, audit agent,
  guardrails-to-file, plus the PreToolUse hook wired into the frontmatter).
- `lead-lockdown.sh` — the hook script.
- `guardrails.md` — the doer guardrail block, extracted so dispatch prompts point
  at it instead of pasting ~80 tokens per unit.

## Install (per repo)
1. Put `lead-lockdown.sh` at `.claude/orchestrate-build/lead-lockdown.sh` and
   `chmod +x` it. (The frontmatter references `./.claude/orchestrate-build/lead-lockdown.sh`.)
2. Put `guardrails.md` and your `conventions.md` in the same `.claude/orchestrate-build/` folder.
3. Install the updated `SKILL.md` wherever your skills live.

## What the hook does
- Runs ONLY while orchestrate-build is loaded (skill-frontmatter scope) — never in normal sessions.
- LEAD ONLY *by nature*: this PreToolUse hook fires for the main session's tool calls only. Subagent (teammate) tool calls never reach it (verified empirically), so teammates are inherently unrestricted. The `agent_id`/`agent_type` allow-branch in the script is a harmless defensive no-op — current payloads never carry those keys.
- On the lead, blocks: Edit/Write/NotebookEdit, `git diff`, and Reads over
  ORCHESTRATE_MAX_READ_BYTES (default 16000). Allows small reads + git status/add/commit.
- No jq dependency (parses in Python3). Fails closed on write tools if input is unparseable.

## Known caveats (decide if they matter for you)
1. **Commit messages containing the word "diff" get blocked.** The git-diff
   guard is deliberately broad and matches `git ... diff` even when "diff" is
   inside the commit message (e.g. `git commit -m "fix diff rendering"`).
   Workaround: rephrase, or loosen the regex in the script. `git difftool` and
   non-git uses of "diff" are fine.
2. **MAX_READ_BYTES is a guess (16KB).** Confirm your index + a single report
   section fit under it and a full log/reports.md/source file exceeds it. Tune via
   the ORCHESTRATE_MAX_READ_BYTES env var.
3. **Verify skill-frontmatter hooks actually fire in your CC version** before
   relying on the lock. Quick test: load the skill, have the lead try a big read,
   confirm exit-2. (Open unknown from planning — not yet confirmed on your setup.)
4. **The hook only sees Read/Bash/Edit/Write/NotebookEdit** (the frontmatter
   matcher). If the lead has other file-reading tools, add them to the matcher.
