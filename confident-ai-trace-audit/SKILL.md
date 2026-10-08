---
name: confident-ai-trace-audit
description: Audit a set of Confident AI traces end to end. Fetch the traces, measure latency, tokens and scores with scripts, split per-unit analysis across one sub-agent per unit, count the patterns they find across every trace, verify suspected bugs, rank fixes, and optionally hand off a presentation. Use when the user asks to analyse Confident AI traces, compare two modes, versions or prompts on the same questions, find why an agent is slow, expensive or wrong, or find odd model behaviour in traces.
---

# Confident AI trace audit

Turn a set of Confident AI traces into fair numbers, per-unit findings, counted patterns,
and ranked fixes. Optionally end with a deck.

Scripts do the counting. Sub-agents explain what happened. Never ship a number that a
sub-agent estimated.

## Start

Ask only what the user has not already answered. If the user said not to ask, pick a
reasonable default for each open item, write it under "Assumptions" in the notes, and go on.

1. **Trace source.** A sheet or CSV of trace ids, a list of Confident uuids, or "recent
   traces of agent X". Sheet ids are often OTel ids; the fetch script handles that.
2. **Comparison.** One set, or groups to compare (modes, versions, prompts). Which group is
   the baseline? Are run numbers aligned across groups?
3. **Analysis unit.** What one sub-agent reads: usually one question with all its runs
   from every group. Can also be one trace or one session.
4. **Focus.** Latency, tokens, cost, correctness, tool use, or all. Any known effects to
   ignore (for example infra queueing already measured)?
5. **Deliverable.** Notes only, notes plus a deck, or a one-page summary.
6. **Data approval.** Downloading full traces can expose prompts and data. Confirm, and
   store them under `/tmp` or a gitignored `local/` folder only.

Then create the audit folder, for example `local/<topic>-trace-audit/` in the
current repo (or `/tmp/<topic>-trace-audit/`). Copy
`assets/notes-template.md` to `research-notes.md` there and keep it updated after every phase.

## Phase 1: Manifest and fetch

Read [references/fetching.md](references/fetching.md).

1. Write `manifest.csv`: one row per trace with `trace_id,unit,group,run,score,label`.
   Only `trace_id` is required. Build it from the user's sheet with a short script.
2. Run `scripts/fetch.py --audit <dir>` with network escalation.
3. **Gate:** the fetch report shows every trace fetched. Report missing and ambiguous ids to
   the user before continuing. Do not silently drop units.

## Phase 2: Measure

Read [references/metrics.md](references/metrics.md).

1. Run `scripts/compact.py`, then `scripts/metrics.py`. Pass `--wait-tool` when one
   tool's first call holds an infra wait (for example a sandbox or cold start).
2. Cross-check against any numbers the user already has (eval sheet, Confident report).
   `unit_metrics.csv` and the printed per-unit medians are the numbers to compare.
3. **Gate:** totals match within a stated tolerance, or the difference is explained (for
   example duplicate LLM spans). Fix or drop units that metrics.py warns are missing
   from a group. Write the fair metrics into `research-notes.md`.

## Phase 3: Analyse, one sub-agent per unit

Read [references/analyst-brief.md](references/analyst-brief.md) and
[references/patterns.md](references/patterns.md).

1. Run `scripts/digest.py`.
2. Write `context.md` in the audit folder: what the groups are, what is already measured
   and must be ignored, and the focus. Keep it under 40 lines.
3. Run `scripts/dispatch.py prepare --audit <dir> --context <dir>/context.md`.
4. Spawn one sub-agent per brief file. One unit per agent, never several.
   - Model: a mid-size model or better. Record which model ran.
   - Start each agent fresh (no forked history) with a short message: "Read the brief at
     <path> and follow it exactly. Only write the findings file it names."
   - Run up to the platform's concurrency limit. Use `dispatch.py next` to get the next batch.
   - Wait for agents without interrupting them. Re-dispatch only units whose findings file
     is missing or has no `## Summary`.
5. **Gate:** `dispatch.py status` shows every unit done.

## Phase 4: Aggregate and count

1. Read every findings file. Merge similar patterns under one name.
2. Copy `assets/profile_template.py` to `<dir>/profile.py` and edit it for this agent:
   list the presentation tools, and override `tools_in_call` if a tool runs other tools
   without logging them as spans. Then run `scripts/patterns.py`; it loads the profile.
   Without a profile it treats every tool call as itself and skips presentation patterns.
3. For each analyst pattern without a built-in count, write a small counting script in the
   audit folder and run it on every trace. Record events, traces affected, and model seconds.
   Start from `assets/counter_template.py` and edit `matches()`.
4. **Gate:** every pattern in the notes has a count from a script, or is marked
   "hypothesis, n traces seen".

## Phase 5: Verify and propose fixes

Read [references/fixes.md](references/fixes.md).

1. For each suspected bug, check the code or render the prompt locally before calling it a
   bug. Trace data can be truncated.
2. Rank fixes by measured cost. Mark each as `proposed`, `agreed` (user confirmed), or
   `potential` (needs more data).
3. Do not change product code. Fixes are proposals unless the user asks for an
   implementation.

## Phase 6: Deliver

1. Finish `research-notes.md`: fair metrics, patterns with counts, counterpoints, ranked
   fixes, open questions, method.
2. If the user wants a deck, read [references/deck.md](references/deck.md), write
   `presentation-brief.md`, and use `$presentation`.
3. Report the audit folder path, the headline numbers, and the top fixes.

## Rules

- Numbers come from scripts. State the n behind every claim.
- Use medians of per-unit medians. Never compare groups on different units.
- Separate facts, inferences, and proposals in every output.
- Never print API keys. Never commit raw traces.
- When the user corrects a finding, update the notes and the deck, and say which numbers
  changed.
