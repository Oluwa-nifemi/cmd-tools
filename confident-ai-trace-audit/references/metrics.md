# Metrics

## What metrics.py produces

`trace_metrics.csv`, one row per trace:

| Field | Meaning |
|---|---|
| wall_s | Agent root span duration |
| llm_s / tool_s / other_s | Union of model spans / top-level tool spans / the rest |
| model_calls | LLM spans after removing duplicates |
| top_tool_calls / nested_tool_calls | Tools the model called / tools called inside another tool |
| fixed_prefix_tokens | Input tokens of the first model call (system prompt + tools) |
| peak_working_tokens | Largest input minus the fixed prefix |
| total_tokens | Sum of input + output over all model calls |
| final_call_s | Duration of the last model call (usually the answer) |
| wait_excess_s / wall_minus_wait_s | Only with `--wait-tool` |

`summary.json`: per group, the median, p90, and mean of per-unit medians.
`unit_metrics.csv`: per unit and group, the median of each metric over the runs. Use it
for per-question cross-checks.
`tool_stats.csv`: calls, errors, duration and output size per tool.

## Fair comparison rules

- **Same units.** Compare groups only on units present in both.
- **Median of unit medians.** Each unit counts once. Report p90 next to it.
- **Separate infra from agent time.** Queueing or cold starts hide inside one tool call (for
  example a sandbox claim in the first call of a code tool). Use `--wait-tool` and say exactly
  what was removed. Show the ideal case (all waits removed) only when labelled as ideal.
- **Peak context misleads when system prompts differ.** Report working tokens (input minus
  the fixed prefix) next to raw peak input. The prefix is usually cache-read.
- **Total tokens grow with turns.** Every turn re-sends the whole context, so one extra
  turn costs roughly the full input again. Count turns, not just tokens.
- **Score.** Report the mean and the number of units each group wins. A slower group that
  is right more often is a tradeoff, not a regression.

## Cross-checks

- Wall time vs the eval's own duration: median absolute difference under 1 s.
- Token totals vs the eval: ratio near 1.0 after removing duplicate LLM spans.
- If a Confident report exists, reproduce its headline medians.

Write each cross-check result into the method section of the notes.
