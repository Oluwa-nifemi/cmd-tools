# Pattern catalogue

Start from these. Each one has a counting rule so a script can check it on every trace.

| Pattern | What it looks like | Counting rule | Built in |
|---|---|---|---|
| Formatting-only turns | A turn after the data arrived that only links, charts, or re-prints | Turn tools all in the presentation list, after the last data turn | `presentation_only_turns`, `tail_turns` |
| Split independent work | Consecutive single-tool turns that did not need each other | Consecutive turns with one top-level tool each; analysts confirm independence | `single_tool_turns_in_a_row` |
| Discovery chains | list → describe → suggest → fetch, one per turn | Consecutive turns calling only discovery tools (define the list per agent) | custom |
| Errors and retries | A tool fails, the next turn calls it again | Non-success tool span, same tool next turn | `errored_tool_calls`, `retry_after_error` |
| Repeated calls | Same tool, same input, twice | Identical (name, input) pairs in one trace | `repeated_identical_calls` |
| Oversized output | Big dumps entering context | Tool output above a size cutoff | `big_tool_outputs` |
| Scratchpad turns | A turn that calls nothing and is not the answer | Non-final turn with no tool | `no_tool_turns` |
| Empty code cells | A code cell that calls no tool (e.g. only `print("done")`) | Code tool call whose parsed code calls no tool function | `no_call_cells` |
| Slow calls | Model calls far above normal | Above the group p90 | `slow_model_calls` |
| Hard-coded ids | Ids copied from earlier output into later calls | Five or more 24-hex ids written into one call's arguments | custom |
| Ignored guidance | The prompt forbids X; the model does X | Count turns matching X | custom |
| Missing guidance | Tool docs or limits never reach the model | Render the prompt locally; check per tool | verify in code |
| Infra wait | Queueing or cold start inside a tool call | First call of the tool vs later calls | `metrics.py --wait-tool` |
| Detours that buy correctness | Extra turns that made the answer right | Compare scores of runs with and without the detour | analyst judgement |

## Writing a custom counter

Built-in counters read code tools for you: compact.py keeps each code tool's full
`code`, and patterns.py parses it with `ast` to find the tool functions a cell calls
(comments and strings do not count). Reuse `functions_called(code)` from
`scripts/patterns.py` in custom counters instead of matching names with regex.

Put it in the audit folder, not the skill. Read `compact/*.json`. Each trace has `spans`
with `type` (LLM or TOOL), `turn`, `name`, `duration_s`, `input`, `output_head`,
`output_chars`, `status`, `is_top_tool`, and `code` (code tools only, else null).
Charge model seconds to the turn that wrote the call. Print events, traces affected,
units affected, and model seconds.

## When a pattern is a feature

Some extra turns buy correctness. Before calling a pattern waste, compare the scores of runs
that show it and runs that do not. Report detours that raised the score as counterpoints.
