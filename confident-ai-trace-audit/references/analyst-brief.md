# Trace analysis brief: unit {{UNIT}}

You analyse ONE unit of an AI agent trace audit. Your job is to explain where time, tokens,
and model calls went, and to flag odd or wasteful model behaviour with evidence.

## Audit context

{{CONTEXT}}

## Your unit

- Unit: {{UNIT}}
- Label: {{LABEL}}
- Digest (your main input): {{DIGEST}}
- Per-trace metrics: {{METRICS}} (filter rows by unit)
- Write your findings to: {{FINDINGS}}

## Context-budget rules

- Read the digest only. Never open files under `raw/` or `compact/`; they are huge.
- The digest can be large. Read it in parts with `sed -n` or `rg`.
- Do not read other units' digests.

## What to look for

Look for these, plus anything else odd:

1. **Wasted turns.** A model call that only formats, links, re-prints, or checks data it
   already had.
2. **Split work.** Several calls in a row that did not depend on each other's results.
3. **Discovery chains.** One probe per turn (list, then describe, then fetch) before the
   answer data arrives.
4. **Errors and retries.** Bad arguments, limits exceeded, missing names. What did the
   retry cost?
5. **Ignored instructions.** The model does something its prompt or tool docs say not to,
   or misses guidance it should have had.
6. **Oversized outputs.** Tool results or printed output much bigger than needed.
7. **Slow calls.** Long model calls. What was it producing?
8. **Correctness.** Wrong or incomplete answers that look right. Where did the run go wrong?
9. **Run-to-run variance.** Did runs of the same unit behave differently? Why?
10. **Group differences.** If there are several groups, where is each one faster or better?

Do not report effects the context says are already measured.

## Output

Write `{{FINDINGS}}` in this shape:

{{FINDINGS_TEMPLATE}}

Rules:

- Cite trace and model call for every claim, for example `direct run 2, call 4`.
- Use numbers from the digest (seconds, tokens, chars). Do not estimate totals across
  other units.
- If a run had no waste, say so. Do not invent patterns.
- Give at most one line of proposed fix per pattern.

Your final chat reply: one short paragraph saying the file is written, with the top 3
patterns.
