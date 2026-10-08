---
name: confident-ai-trace-audit
description: Audit a set of Confident AI traces end to end. Fetch the traces, measure latency, tokens and scores with scripts, split per-unit analysis across one sub-agent per unit, count the patterns they find across every trace, verify suspected bugs, rank fixes, and optionally hand off a presentation. Use when the user asks to analyse Confident AI traces, compare two modes, versions or prompts on the same questions, find why an agent is slow, expensive or wrong, or find odd model behaviour in traces.
---

# Confident AI trace audit

Turn a set of Confident AI traces into fair numbers, per-unit findings, counted patterns,
and ranked fixes. Optionally end with a deck.

Scripts do the counting. Sub-agents explain what happened. Never ship a number that a
sub-agent estimated.

The person only gives a trace source and a short prompt. You, the agent, decide everything
else: groups, units, which tools only format, which tools hide waits, profile.py, and
custom counters. Do not hand configuration back to the person.

## Start

Work out each item below from the prompt, the sheet, and the traces. Do not ask about an
item you can infer. Write every inferred choice under "Assumptions" in the notes. Ask only
when a wrong guess would change the result and the data cannot settle it (for example
which group is the baseline when nothing says so). If the person said not to ask, never ask.

1. **Trace source.** A sheet or CSV of trace ids, a list of Confident uuids, or "recent
   traces of agent X". Sheet ids are often OTel ids; the fetch script handles that.
2. **Comparison.** Read groups and run numbers from the sheet's column names. Default: one
   group per mode or version column set; the older or "without" group is the baseline.
3. **Analysis unit.** Default: one question with all its runs from every group.
4. **Focus.** Default: latency, tokens, correctness, and tool use. Treat effects the prompt
   calls known as already measured.
5. **Deliverable.** Default: notes only. Make a deck only when asked.
6. **Data approval.** Downloading full traces can expose prompts and data. Go ahead if the
   prompt or standing instructions approve it; otherwise ask. Store them under `/tmp` or
   a gitignored `local/` folder only.

Then create the audit folder, for example `local/<topic>-trace-audit/` in the
current repo (or `/tmp/<topic>-trace-audit/`). Copy
`assets/notes-template.md` to `research-notes.md` there and keep it updated after every phase.

## Phase 1: Manifest and fetch

Read [references/fetching.md](references/fetching.md).

1. Write `manifest.csv`: one row per trace with `trace_id,unit,group,run,score,label`.
   Only `trace_id` is required. Build it from the sheet with a short script.
2. Run `scripts/fetch.py --audit <dir>` with network escalation.
3. **Gate:** the fetch report shows every trace fetched. Retry missing ids with the other
   key or a wider `--since`. If ids are still missing, list them in the notes and in the
   final report. Do not silently drop units.

## Phase 2: Measure

Read [references/metrics.md](references/metrics.md).

1. Run `scripts/compact.py`, then `scripts/survey.py`, then `scripts/metrics.py`. If
   the survey flags a tool with "possible infra wait", or the prompt names one, pass it to
   metrics.py as `--wait-tool`.
2. Cross-check against any numbers the person already has (eval sheet, Confident report).
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
2. Write `<dir>/profile.py` yourself from `assets/profile_template.py`. Base it on
   `survey.json`, the digests, and the findings:
   - `PRESENTATION_TOOLS`: tools that only link, chart, or format. Survey hint: "possible
     presentation tool". Confirm from the tool's input and output.
   - `tools_in_call`: override it for tools flagged "may run tools unlogged". Read a few
     sample inputs, then parse them (the template has a Python code example).
   - Check it: re-run `scripts/patterns.py` and spot-check five events against the digest.
   Then run `scripts/patterns.py`; it loads the profile.
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
