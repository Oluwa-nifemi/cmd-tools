---
name: research
description: Run a standalone or lightly delegated deep investigation while maintaining a durable evidence corpus. Use only when the user explicitly invokes $research or explicitly asks to use the research skill. Do not infer activation from words such as research, investigate, deep dive, or dig into.
---

# Research

Run one investigation well and leave behind a compact, resumable evidence record. This skill owns the research corpus; it does not coordinate a large program of work.

## Scope

Use this for a standalone investigation or a small number of tightly scoped research delegations.

Route substantial work to `$orchestrate` when it needs parallel investigators, multiple independently reviewable units, mixed research/build/artifact phases, or a coordination record. In its research mode:

- `$orchestrate` owns the question map, routing, agent coordination, validation gates, `orchestrator-log.md`, and any wrap-up presentation.
- This skill's corpus protocol owns `research-notes.md`, `steps/`, and `companions/`: the evidence, reasoning, rejected alternatives, and open questions.

Do not make `$research` call `$orchestrate`. The dependency runs one way: orchestration may adopt this protocol.

## Start

1. Identify the investigation, decision it should support, and any authority or time boundary.
2. Read [references/corpus.md](references/corpus.md) in full before creating or updating research artifacts.
3. Determine whether this is a new corpus or a resumption. For a new corpus, initialize it; for a resumption, read `research-notes.md` first and open a new session block.
4. Tell the user the corpus location in one line, then investigate.

For an orchestrated research run, the coordinator reads `references/corpus.md` and [the orchestration research workflow](../orchestrate/references/research.md). It creates the corpus alongside its orchestration record before dispatching investigators.

## During the investigation

- Update the corpus at each material finding, decision, rejected alternative, reframe, or user-supplied resolution. Do not batch it at wrap-up.
- Keep `research-notes.md` a concise cross-step narrative. Put source detail, agent reports, traces, and exhaustive comparisons in step files.
- Record uncertainty and the evidence that would change the recommendation.
- Keep one owner for `research-notes.md`. In a parallel orchestration run, appoint a named research curator; investigators write only their assigned step files.

## Finish

Follow the wrap-up protocol in [references/corpus.md](references/corpus.md): reconcile the narrative, decisions, open questions, next steps, timestamps, and time invested.

For a standalone research run, offer the optional research presentation only after the corpus is complete. Read [presentation-details.md](presentation-details.md) and the `presentation` skill before rendering.

For an orchestrated research run, do not independently offer or render a presentation. Hand the finalized corpus back to `$orchestrate`; it owns the user’s chosen deck or page and reads both the orchestration log and the corpus.
