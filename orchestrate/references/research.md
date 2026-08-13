# Orchestrated research

Use this workflow for a research program with parallel investigators, independently reviewable questions, or research that unlocks build or artifact work. For a single-threaded or lightly delegated investigation, use `$research` directly.

This mode owns coordination; `$research` owns the evidence protocol. Read [../../research/references/corpus.md](../../research/references/corpus.md) in full before dispatching.

## Establish the two records

Create both records before any investigator starts:

1. `local/<task>/orchestrator-log.md` — scope, question map, unit ownership, dependencies, validation, routing decisions, incidents, and final coordination outcome.
2. `local/<task>/research/` — the `$research` corpus: `research-notes.md`, `steps/`, and optional `companions/`.

Do not merge them. The log explains how the work ran; the corpus preserves evidence and reasoning.

Assign one named research curator to own `research-notes.md`. The curator continuously integrates evidence; it does not coordinate the program or duplicate the orchestration log. Investigators write only to their assigned step files.

## Intake and decomposition

Write the question map in the orchestration log: the decision to support, material sub-questions, required evidence, and the conditions that would change the recommendation. Split independent questions among investigators; do not send several agents to rediscover the same broad topic.

Give every investigator:

- a bounded sub-question and scope boundary;
- a source standard and evidence threshold;
- an assigned `research/steps/step-N-<slug>.md` path;
- a request for findings, supporting sources, confidence, counterevidence, rejected alternatives, and unanswered questions.

Prefer primary sources for technical claims, official documentation for product behavior, and directly relevant evidence over plausible recollection.

When an investigator returns, route its evidence to the curator first. The curator records a concise takeaway and any changed decision, uncertainty, or open question in `research-notes.md`.

## Synthesis gate

Dispatch a fresh synthesis/audit agent after the corpus is complete. It must read `research-notes.md`, the relevant step files, and the question map in `orchestrator-log.md`, then check:

1. Each material conclusion is supported and distinguished from inference.
2. Sources are authoritative enough for the claim.
3. The investigation answered the question map rather than merely collecting facts.
4. Material counterevidence, constraints, rejected alternatives, and uncertainty are represented.
5. The recommendation states trade-offs and what would cause it to change.

Route factual or analytical gaps to the original investigator where possible, then have the curator reconcile the corpus. Record the audit outcome in the orchestration log and produce the concise decision memo or update the user's established record.

## Presentation handoff

When the user opted into a wrap-up presentation, the coordinator owns it. Use `orchestrator-log.md` for “how the work ran” and the finalized research corpus for “what the evidence supports.”

- For a deck, also read `$research`'s `presentation-details.md` overlay.
- For a smaller page, use the generic presentation flow while citing the corpus rather than reproducing it.
