# Confident AI trace audit

A Codex skill. It finds Confident AI traces from a plain description and measures latency,
tokens and scores. It then has sub-agents explain what happened and counts the patterns
across every trace. You get research notes, and a deck if you ask for one.

## Setup

1. Link the skill into Codex:

   ```
   ln -s <path-to>/cmd-tools/confident-ai-trace-audit ~/.codex/skills/confident-ai-trace-audit
   ```

2. Export at least one Confident AI key: `CONFIDENT_API_DEV_KEY` (dev traces) or
   `CONFIDENT_API_KEY`.

## Use

Tell Codex what you ran. That is all it needs.

```
$confident-ai-trace-audit I ran the eval on org mcptest this morning around 10-12
Oslo time. Code execution vs direct tools, 3 runs each. Why is code execution slower?
```

Codex finds the matching traces and shows you the batches it found, for example
"42 traces, 10:15 UTC, looks like direct run 2". Say which batches to keep. It does
the rest.

Useful things to add to the prompt:

- **Known effects to ignore**, e.g. "the first execute_code includes ~7 s sandbox startup".
- **Deliverable**: notes only (the default), or "make a deck".
- **"Don't ask me questions"**: Codex picks defaults and lists them in the notes.
- **A sheet or list of trace ids** instead of a description, if you already have one.

## Output

Codex writes everything to an audit folder (`/tmp/<topic>-trace-audit/` or
`local/<topic>-trace-audit/`):

| File | What it is |
|---|---|
| `research-notes.md` | The result: fair metrics, counted patterns, ranked fixes |
| `unit_metrics.csv` | Per-question medians per group |
| `findings/` | One sub-agent write-up per question |
| `raw/` | Full traces. Can hold prompts and data, so never commit it |

## Running the scripts by hand

You normally don't need to. Each script in `scripts/` prints its usage with `--help`.
Order: `discover` → `fetch` → `compact` → `survey` → `metrics` → `digest` →
`dispatch` → `patterns`.
