# Research corpus protocol

Use this protocol whenever `$research` is active, including when `$orchestrate` adopts it for an orchestrated research run.

## Corpus shape

Choose a lowercase kebab-case slug. Prefer `local/<slug>_research/` in a git repository with `local/`; otherwise use `~/Desktop/<slug>_research/`, unless the user gives a path.

```text
<slug>_research/
├── research-notes.md
├── steps/
│   └── step-N-<slug>.md
└── companions/
    └── <topic>.md
```

- `research-notes.md` is the concise narrative: chronology, decisions, unresolved questions, time tracking, next steps, and pointers to evidence.
- `steps/` holds evidence-heavy detail: sources, code references, direct observations, delegated findings, and rejected alternatives.
- `companions/` holds polished designs, specs, or proposals that arise from the research.

Do not pre-create step files. Create one as soon as a main-doc section would need more than roughly five sentences of detail.

In an orchestrated run, place this corpus inside the task folder when practical, for example `local/<task>/research/`. Keep it separate from `local/<task>/orchestrator-log.md`:

- `orchestrator-log.md`: how work was coordinated.
- `research-notes.md` and `steps/`: what evidence was found and why the recommendation follows.

## Main narrative constraints

Keep `research-notes.md` under 200 lines. At about 150 lines, move detail into a step file before adding more. Do not turn the main document into a transcript.

Always maintain:

- **Time invested** near the top.
- **Open questions** containing only questions that remain open.
- **Decisions and rejected alternatives** table.
- Timestamped **Session** blocks.
- **Next steps** near the bottom.
- Quick references to files touched and files investigated.

Use Europe/Oslo timestamps: `HH:MM` in steps and `YYYY-MM-DD` in session headers. Update the time-invested total when a session ends.

### Initial template

```markdown
# <TOPIC> — research session notes

Investigation: <one sentence>

**Time invested**: 0h 0m across 1 session (in progress).

## For the next session — read these first

1. Read this whole file for the arc, decisions, and next steps.
2. Confirm current code or source state before relying on it.
3. Read `steps/` only for the evidence behind a specific point.

---

## Open questions

- *(fill as the session progresses)*

---

## Decisions and rejected alternatives

| Decision | Chosen approach | Alternatives considered | Why rejected |
|---|---|---|---|
| *(fill as the session progresses)* | | | |

---

## Session — <DATE> (started <TIME>)

(new investigation)

---

## Step 1 — <first area> (<TIME>)

*(Fill as work progresses)*

---

## Next steps (post-session)

*(Fill as work progresses)*

## Quick reference — files touched

*(Fill as changes are made)*

## Quick reference — files investigated

*(Fill as the investigation progresses)*
```

For resumption, read the existing narrative, add a session block with a one-paragraph account of the last decision and remaining open questions, then continue step numbering.

## Continuous recording

Update the corpus during the work, not at the end. Record:

| Event | Record |
|---|---|
| Finding that changes the model | Main narrative; step file when evidence is non-trivial |
| Decision or rejected alternative | Decisions table; evidence in the relevant step |
| Gotcha that reframes the work | A new `Step N.5` |
| Material delegated finding | Step file first, then a short main-doc takeaway |
| Load-bearing source, file reference, or direct observation | Main narrative if brief; otherwise a step file |
| User resolution to an open question | Update the relevant section in the same turn |

Do not record raw search output, routine reads that merely confirmed expectations, tool chatter, or trivial dead ends.

Edit an earlier step in place when later evidence invalidates it. Preserve a short note when the earlier framing is itself useful evidence of the reframe.

Keep the decisions table current. Once an open question is answered, remove it from Open questions or move its resolution into the decision table or relevant step. Do not leave a graveyard of struck-through resolved items.

## Parallel research

Parallel investigators must have bounded questions, source standards, scope limits, and assigned output paths. They should write evidence to their assigned step files, including:

- findings and supporting sources;
- confidence, limitations, and counterevidence;
- rejected explanations or alternatives;
- unanswered questions that could change the conclusion.

Never let several agents edit `research-notes.md`. For a parallel run, a named research curator owns the narrative and integrates completed step files continuously. The curator does not replace the orchestrator: it owns evidence synthesis only.

## Step file format

Use only the sections that matter:

```markdown
# Step N — <short title> (<DATE> <TIME>)

*(Companion to: ../research-notes.md)*

## Summary

<What this step examined and what it found.>

## References

- [Title](url) — why it matters

## Delegated findings

> Preserve relevant source links, file references, quotes, and confidence.

## Code refs / direct evidence

- `path/to/file:42-58` — why it matters

## Rejected alternatives

### <alternative>

What it would have meant, what evidence ruled it out, and why.

## Notes / dead ends

- Tried X; stopped because Y.
```

## Wrap-up

When the user ends the session:

1. Record any unrecorded material findings from this session.
2. Reconcile decisions, rejected alternatives, open questions, quick references, and prioritized next steps.
3. Add `Session ended <TIME> — duration ~<Xh Ym>.` to the active session.
4. Recompute the Time invested total from the completed sessions.
5. Report only the corpus update path and session/total duration unless the user asks for a prose summary.

For standalone research, offer an HTML deck once, after this reconciliation. Use `presentation-details.md` with the generic `presentation` skill; write the brief and deck inside the corpus folder.

For orchestrated research, return the finalized corpus to the coordinator instead. It decides whether the user-requested wrap-up is a deck or page and must use both the corpus and the orchestration log as source material.
