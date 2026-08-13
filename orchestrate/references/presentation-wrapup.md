# Presentation wrap-up

Use this protocol only when the user opted in at intake. It produces two complementary deliverables:

1. **Orchestration record:** `local/<task>/orchestrator-log.md`, the durable evidence of how work was coordinated.
2. **Return artifact:** a rendered HTML deck or one-page status view explaining both how the run unfolded and what it delivered.

## At intake

Ask: “Do you want a wrap-up presentation at the end? It will show how the work ran and what it produced.” Record the answer, audience, and any explicit deck/page preference. Default the audience to `self` and purpose to `status`; defer the deck/page choice until the work is complete.

When the answer is yes, create the orchestration record before dispatching. Keep it compact and current:

- goal, scope, chosen mode, and authority boundaries;
- unit index with owner, state, dependencies, validation, and report pointers;
- material steering decisions, reframes, incidents, and deferred work;
- final outcome and verification summary.

Do not turn it into a transcript. The record is the source of truth that makes the later artifact honest and resumable.

## At wrap-up

Choose the format unless the user already chose one:

- **Deck:** the run was long or has a story to walk through — multiple sessions, multiple modes/phases, material reframes, or several independently meaningful units.
- **Page:** the run was one focused effort with a short, reference-oriented summary.

Read the `presentation` skill and its `brief-format.md` in full. Compose `local/<task>/presentation-brief.md`, preserving it for future re-renders. 
The brief must name the orchestration record and the minimum source reports needed to verify outcome claims; do not render a copy of a copy. 
For research mode, those sources must include `research/research-notes.md` and the relevant `research/steps/` files; for a deck, also use the `$research` presentation overlay.

Write the rendered deck to `local/<task>/presentation.html`; write a page to `local/<task>/wrap-up.html`, unless the user specifies a different output path.

The artifact should have two visible halves:

1. **How the work ran:** objective and scope, workflow/modes, unit or phase map, material decisions/reframes, and validation gates. Keep agent mechanics and raw chronology in expanded details or the source log.
2. **What it produced:** shipped or decided outcomes, before/after where useful, concrete deliverables, evidence of verification, deferred work, and the next action when relevant.

Use the presentation skill’s normal rendering and verification protocol. Prefer a lean artifact: a deck needs only the story necessary to regain context; a page should be scannable rather than a prose dump. In the completion report, link both the orchestration record and rendered HTML.
