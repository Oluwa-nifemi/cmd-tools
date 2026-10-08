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
| Empty tool calls | A call that runs nothing useful (e.g. a code cell that only prints) | `tools_in_call` in the profile returns an empty set | `empty_tool_calls` (needs a profile) |
| Slow calls | Model calls far above normal | Above the group p90 | `slow_model_calls` |
| Hard-coded ids | Ids copied from earlier output into later calls | Five or more 24-hex ids written into one call's arguments | custom |
| Ignored guidance | The prompt forbids X; the model does X | Count turns matching X | custom |
| Missing guidance | Tool docs or limits never reach the model | Render the prompt locally; check per tool | verify in code |
| Infra wait | Queueing or cold start inside a tool call | First call of the tool vs later calls | `metrics.py --wait-tool` |
| Detours that buy correctness | Extra turns that made the answer right | Compare scores of runs with and without the detour | analyst judgement |

## Writing a custom counter

Copy `assets/counter_template.py` into the audit folder and edit `matches()`. Keep
counters in the audit folder, not the skill. The template reads `compact/*.json`,
charges model seconds to the turn that wrote the call, and prints events, traces, units,
and model seconds per group.

Built-in counters only see tools that appear as spans. If a tool runs other tools
without spans (for example a code tool, or a router tool), override `tools_in_call` in
the audit's `profile.py`. The template has a commented example for a Python code tool.
Custom counters can import the same profile so both agree on what a call ran.

## When a pattern is a feature

Some extra turns buy correctness. Before calling a pattern waste, compare the scores of runs
that show it and runs that do not. Report detours that raised the score as counterpoints.
