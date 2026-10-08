# From patterns to fixes

## Each fix states

- **Pattern** it targets and the **count** behind it (events, traces, model seconds).
- **Type:** prompt, tooling, bug, infra, or eval.
- **Expected saving** in seconds, turns, or tokens, and how it was estimated.
- **Status:** `proposed`, `agreed` (user confirmed), `potential` (needs more data), or
  `done` (merged).
- **Verification** that would show it worked in the next eval.

## Verify before claiming a bug

- Read the code path. Quote the file and line.
- Render the prompt or tool signature locally when the trace input could be truncated.
- Check the backend or UI when a fix depends on how a link, id, or route behaves. A link
  that "looks right" in a trace can be dead.

## Check the "free" ideas with data

For ideas such as "return links inside data tools" or "pre-load names in the prompt":

1. **Coverage.** What share of the target calls would the change remove? Trace each linked
   or reused id back to the tool that first returned it.
2. **Cost.** Extra tokens per trace: added chars × number of later turns that re-send them.
3. **Saving.** Model seconds and input tokens of the turns that would disappear.
4. **Edge cases.** Inputs the tool cannot know (for example a viewpoint link needs its start
   components). Check that real calls used the same inputs.

## Prompt and schema changes

- Any change to a prompt, tool description, or tool schema needs an eval re-run before it
  ships.
- When the current wording is ignored in most traces, that shows the wording fails. It does
  not prove prompting cannot work. Test variants on the same units.
- When a tool change makes a prompt rule obsolete, change both in the same branch.

## Ranking

Rank by measured saving × how many traces it touches. Put infra and eval fixes that change
how fair the numbers are near the top; they change every other comparison.
