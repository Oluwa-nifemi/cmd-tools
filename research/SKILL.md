---
name: research
description: Put the session into deep-dive research mode. Key findings, rejected alternatives, and the reasoning behind approach choices get captured into a living markdown doc automatically as the investigation evolves. Use when user says "research", "investigate", "deep dive", "let's dig into", or invokes /research.
model: sonnet
argument-hint: "<topic> (e.g., extended-thinking, guardrails-api, aks-autoscaling)"
---

# /research

Open a living research doc and maintain it continuously throughout the investigation. The doc captures *what was found, what was tried and rejected, and why decisions were made* — not just what was decided.

## Two artefacts, two audiences

The skill produces two distinct artefact families that should not compete on the same axes:

- **The markdown corpus** (`research-notes.md` + `steps/*.md` + `companions/*.md`) is the **dense source of truth**, optimized for future-agent resumption and the user's own deep dives. Faithful, evidence-heavy, append/edit-friendly. Read by agents in fresh conversations and by the user when grepping, scrolling, quoting, or editing.
- **The HTML deck** (`presentation.html`, generated on demand at wrap-up) is the **viewing artefact**, optimized for human presentation and progressive-disclosure scanning. Designed, navigable, expandable on demand. Read by the user (and their team) when presenting or skimming.

Each format imposes its own discipline:
- Markdown's density forces capturing the evidence trail (no hiding behind visuals).
- HTML's progressive disclosure forces committing to a headline per finding (no hiding behind walls of text).

Together they cover failure modes that single-format artefacts can't. Markdown alone is unreadable to humans for review/sharing; HTML alone loses agent-resumability and long-tail evidence. **Don't drift toward "make the markdown prettier" or "make the deck more comprehensive."** Each artefact serves its audience; resist the urge to merge their goals.

## When to use

### Explicit invocation
- User says "research X", "let's investigate X", "deep dive into X", `/research`

### Auto-activation (mid-session)
The user wants the skill to activate even when they didn't explicitly invoke it — i.e. when a deep investigation is already underway and a doc would have helped if started earlier. Watch for **at least 2 of these signals** in a single session:

- A sub-agent has been dispatched purely for research (not implementation)
- An approach has been tried and rejected, or two alternatives are being weighed
- An unexpected gotcha / bug / behaviour change has been discovered mid-investigation
- An external resource (GitHub issue, PR, vendor doc) has informed a decision
- The user has explicitly made a decision between alternatives ("let's go with X over Y because…")
- More than ~30 minutes of investigation has happened without a substantive code change

When 2+ are present, **proactively offer**: "This looks like a research session — want me to start a research doc and retroactively capture what we've covered so far?" Do not silently start writing — confirm with the user once. If they agree, follow the resumption-style flow: create the doc with a step-by-step summary of what's already happened, then continue with continuous recording from there.

Once the user has confirmed (or declined) auto-activation in a session, do not ask again that session.

## Critical behaviour rules

1. **Update the doc during the session, not at the end.** After each meaningful discovery, rejected approach, or decision, update the doc before moving on. Do not accumulate and dump at wrap-up.
2. **Never ask "should I update the doc now?"** — just do it. Only exception: if a finding is ambiguous enough that you're not sure whether it's load-bearing, use judgement.
3. **Never defer doc updates.** Phrases like "I'll add this to the doc next time we touch it", "I'll capture that in the next pass", or "I'll save this finding when we're back here" are anti-patterns — by the time "next time" comes, the texture is gone or you've forgotten the doc exists. If a finding is worth recording, record it in the same turn it surfaces. The research doc is a live working surface, not a periodic deliverable. This applies to BOTH initial creation (don't punt the doc to later in the session) AND ongoing updates (don't punt new findings to a future session).
4. **When the user provides resolution to an open question, update immediately.** If the user answers something that was in the "Open questions" section, or makes a decision that closes a row in the rejected-alternatives table, edit those sections in the same turn — don't leave stale `*(fill as session progresses)*` placeholders or unresolved questions once you have the answer.
5. **Edit in place when context shifts.** When new findings invalidate or reframe an earlier step, edit that step rather than appending a contradiction at the end. If the original framing is itself instructive (e.g. "we believed X for 30 minutes before discovering Y"), preserve a struck-through note about the prior view rather than deleting it silently.
6. **User-flagged saves bypass the judgment filter.** When the user says "save this", "make sure that goes in the doc", or similar, record it without applying the load-bearing test. They've already made the call.
7. **Do not transcribe the session.** Tool output, exploratory commands, dead ends that revealed nothing, and side chatter don't go in. Only information that would matter to a future reader who needs to understand what happened and why.
8. **The "decisions and rejected alternatives" table is mandatory** and must be maintained throughout. This is the part most often lost from research sessions.
9. **Section numbers evolve organically.** Use Step 0, Step 1, Step 1.5 etc. in chronological order of discovery. A Step 1.5 is a "gotcha that changed the picture mid-way through Step 1" — use it freely.
10. **Resumption.** If `/research <topic>` is invoked and a doc already exists for that topic, read it first, open a new session block with the resumption header, summarise where things were left off in one paragraph, then continue.
11. **`research-notes.md` MUST stay under 200 lines.** It is a human-parseable narrative log of decisions and brief step summaries — not the place where detail accumulates. If the file approaches 200 lines, the right move is **not** to add another sub-section; it is to push detail into a step file and leave a `*(See detail: steps/step-N-<slug>.md)*` pointer. Run `wc -l research-notes.md` periodically as the session progresses; when it crosses ~150 lines, audit before adding more. The 200-line cap is intentional friction — it forces step bodies in the main doc to be 3-5 sentence summaries, and pushes the verbose mechanical traces, code snippets, exhaustive option tables, and edge-case analysis into step files where they belong. The user can read the whole narrative in 2-3 minutes; they dive into a step file only when they want receipts.
12. **Closed questions move out of "Open questions".** Once a question is answered, it is no longer open. Either delete it, OR move the resolution into the relevant step file or the decisions table — wherever it best lives as a forward-looking artifact. Do not leave a long list of `~~struck-through~~` "resolved" entries in the Open questions section: they bloat the narrative without adding value, and a future reader scanning open issues has to mentally filter them out. The decisions table captures *why* something was decided; step files capture *what* was found. The Open questions section captures *what's still unanswered*. Keep them disjoint.

## Timestamps

The user values knowing *when* discoveries happened and *how much time* a research thread has consumed. Maintain timestamps using these rules:

- **Timezone**: Europe/Oslo. Always. Do not include the timezone in the rendered timestamp — it's implicit.
- **Format**: `HH:MM` (24-hour) within a session block. Full date `YYYY-MM-DD` only on session-block headers.
- **When to capture**: at step boundaries (when adding a new `## Step N — ...` heading), at session start, and at session end. Not on every individual finding within a step — that creates noise.
- **How to capture**: when adding a step heading, append the time inline: `## Step 1.5 — Adaptive thinking gotcha (16:47)`.

### Session blocks

Each time the skill activates (fresh invocation OR resumption OR auto-activation), open a session block with a timestamped header:

```
---

## Session — 2026-05-08 (started 14:32)

Resuming from: <one-paragraph summary of where the last session ended, or "(new investigation)" for the first session>
```

When the user signals the session is ending (Step 4 wrap-up), close the block:

```
Session ended 18:15 — duration ~3h 43m.
```

### Cross-session time tracking

At the very top of the doc (just under the title and Investigation line), maintain a small "Time invested" block. Update it at the end of each session:

```
**Time invested**: 5h 17m across 2 sessions (2026-05-07: 1h 34m · 2026-05-08: 3h 43m).
```

This gives the user an at-a-glance answer to "how long have I been on this?"

## Process

### Step 1 — Set up the doc

1. Determine the slug: convert the topic argument to lowercase kebab-case (e.g., "extended thinking" → `extended-thinking`). If no argument, ask the user once for a short topic name.

2. Determine the location. Prefer the following in order:
   - If the current working directory is a git repo with a `local/` directory, use `local/<slug>_research/`.
   - Otherwise, use `~/Desktop/<slug>_research/`.
   - If the user specifies a path, use that.

3. The folder structure is:

   ```
   <slug>_research/
   ├── research-notes.md       # high-level narrative — chronology, decisions, time tracking
   ├── steps/                  # one detail file per step, holding evidence
   │   ├── step-0-<slug>.md
   │   ├── step-1-<slug>.md
   │   ├── step-1.5-<slug>.md
   │   └── ...
   └── companions/             # design docs / specs (optional)
       └── <slug>.md
   ```

   - **`research-notes.md`** is the high-level narrative. **Hard target: under 200 lines.** Every step in this file is a 3-5 sentence summary plus a pointer to its step file. Code snippets, mechanical traces, code citations, exhaustive option tables, and edge-case analysis do NOT belong here.
   - **`steps/step-N-<slug>.md`** is a per-step evidence file: GitHub issues, sub-agent findings, file:line citations, mitm dumps, dead-end notes, code snippets, mechanical traces. Verbose by design — this is where verbosity lives.
   - **`companions/`** holds design docs / specs (e.g. proposed upstream patches). Distinct from evidence; these *do* want to be polished.

   **Don't pre-create step files** — but don't avoid creating them either. Create a `steps/step-N-<slug>.md` file the moment a step is about to accumulate more than ~5 sentences of detail in the main narrative. The trigger is "this section is starting to bloat research-notes.md", not "I have a polished writeup ready." A working scratchpad with a few sentences in a step file is fine; an overflowing main doc is not.

   **Rule of thumb**: when adding to research-notes.md, run `wc -l research-notes.md` in your head. If you'd push it past 150 lines, the next paragraph belongs in a step file. The 200-line ceiling is a hard cap — when crossed, the next session should split it before adding anything new.

4. Check whether the folder already exists:
   - **Exists**: Read `research-notes.md`, then go to the Resumption path (Step 2b).
   - **Does not exist**: Create the folder structure (including `steps/`), then write the initial template (Step 2a).

5. Tell the user the doc path. No fanfare — one line: `Research doc: <path>/research-notes.md`. Then proceed.

### Step 2a — Initial template

Write the following template to `research-notes.md`. Replace `<TOPIC>`, `<DATE>`, and `<TIME>`:

```
# <TOPIC> — research session notes

Investigation: <one sentence from the user's invocation or their first message>

**Time invested**: 0h 0m across 1 session (in progress).

## For the next session — read these first

If you're resuming this investigation in a fresh conversation:

1. Read this whole file (research-notes.md) — covers the arc, decisions, and **Next steps**.
2. Confirm code matches the doc by reading the **current state** of files listed under "Quick reference — files touched" near the bottom.
3. Read files under `steps/` only if you need a specific step's evidence — the narrative here is usually enough.
4. The **Next steps** section near the bottom is the "what to do next" pointer — start there once grounded.
5. Note any external new input expected (e.g. eval results, sub-agent findings, vendor responses) — those override the Next steps if they change the picture.

---

## Open questions

- *(fill as the session progresses)*

*(Followup actions in priority order: see "Next steps (post-session)" section below.)*

---

## Decisions and rejected alternatives

| Decision | Chosen approach | Alternatives considered | Why rejected |
|---|---|---|---|
| *(fill as the session progresses)* | | | |

---

## Session — <DATE> (started <TIME>)

(new investigation)

---

## Step 1 — [first area of investigation] (<TIME>)

*(Fill as work progresses)*

*(Optional: add a "Step 0 — Prior context" before Step 1 ONLY if there's real pre-investigation context to capture — prior attempts, related incidents, an existing doc that frames the question. Don't add Step 0 just to summarize the codebase or upstream version facts; those belong inline in the relevant step. If you'd struggle to fill it without padding, skip it.)*

---

## Quick reference — files touched

*(Fill at end or as changes are made)*

## Quick reference — files investigated

*(Fill as the investigation progresses)*
```

### Step 2b — Resumption path

After reading the existing doc, find the "Time invested" line at the top — you'll update it on session-end. Then open a new session block at the bottom:

```
---

## Session — <DATE> (started <TIME>)

Resuming from: <one paragraph summary of where the last session ended — what was the last decision made, what was pending, what open questions remained>
```

Then continue from where things were left off. Do not re-litigate earlier conclusions unless the user asks. Within this session, new step headings continue numbering from where the previous session left off (e.g. if the last session ended at Step 4, the next discovery starts at Step 5).

### Step 3 — Continuous recording protocol

During the investigation, update the doc after each of the following events. Do not wait to batch them.

**Always record (and where it goes):**

| Event | Where |
|---|---|
| Finding that changes your mental model | main doc (+ step file iff one exists for this step) |
| Decision (which path, which approach) | main doc decisions table (+ step file iff it has the evidence trail) |
| Rejected alternative — *with the why* | main doc decisions table; longer write-up in step file iff one exists |
| Bug / gotcha / unexpected behaviour mid-investigation | new Step N.5 in main doc (+ step file iff texture warrants it) |
| Sub-agent finding worth keeping | step file (verbatim or near-verbatim) + one-line summary in main doc — sub-agent output is a strong reason to spawn a step file |
| Load-bearing file:line reference | inline in main doc if 1-2 refs; step file if you're piling up many |
| External resource (GitHub issue/PR/doc) that informed a decision | inline in main doc if one link; step file if it's a longer reading list |

The rule of thumb: a step file exists when a step has more evidence than the narrative can hold cleanly. If your step body in `research-notes.md` is already a tight summary and there's no overflow detail, no step file is needed.

**Concrete examples** — what these look like in practice:

- "Confirmed via mitm that Bedrock returns the signature on the wire" → finding under current step + raw evidence in the step file
- "Tried `{"type": "adaptive"}` — got a 400 about thinking + forced tool_choice" → "what we tried that didn't work" in main doc, decisions table row, error message in step file
- "Discovered pydantic-ai #5304 — 4.6 models silently disable thinking after turn 1" → new Step N.5, issue URL in step file
- "Decided to migrate to AnthropicModel rather than patch litellm" → decisions table row + step file write-up of both alternatives

**Default routing rule**: when a sub-agent returns findings, paste them into the step file *before* summarizing into the main doc. The texture (URLs, exact quotes, code refs) lives in the step file; the main doc gets the takeaway and a `*(See detail: steps/step-N-<slug>.md)*` pointer.

**Rejected alternatives are first-class evidence.** When you rule out a path, write it up in the step file like a real finding — what was tried, what it would have looked like, why it didn't work. Two weeks from now you'll forget *why* faster than *what*.

**Do not record:**
- Exploratory grep/search commands and their raw output
- Reads that confirmed something expected ("checked the file, was as expected")
- Conversation back-and-forth where no new information emerged
- Trivially-ruled-out dead ends (one check, nothing there)
- Tool invocations and scaffolding

**When to add a new Step section vs append to an existing one:**
- New Step: the investigation has moved to a meaningfully different area or phase
- Step N.5: a mid-phase gotcha that reframes or complicates the current step
- Append to existing Step: more detail, more evidence, or additional sub-findings within the same area

**Decisions and rejected alternatives table:** update this as soon as a decision is made. Every time you rule out a path, add a row. The "why rejected" column should be specific enough to prevent a future reader from re-investigating the same dead end.

**Open questions:** add questions as they surface during the investigation. Strike through (~~question~~) or remove them when answered.

### Step 4 — Wrap-up (when the user signals the session is ending)

When the user says something like "ok let's stop here", "that's enough for now", "write up what we found", or similar:

1. Review the doc for any findings from the current session that were discovered but not yet recorded.
2. Fill in or update the "Quick reference — files touched" and "Quick reference — files investigated" sections.
3. Review the "Open questions" section — remove any that are clearly answered, ensure remaining ones are accurately phrased.
4. Review the "Decisions and rejected alternatives" table — ensure all major decisions made this session have rows.
5. **Maintain a "Next steps" section** near the bottom of the doc (above the "Quick reference" sections). The resumption checklist at the top of the doc points future readers here. Populate or update it with a prioritized list of followups, including:
   - Validation steps (e.g. evals, smoke tests) and expected new input.
   - Followup items in priority order, each with enough context that a future session can act without re-deriving why.
   - For each item, note whether it's blocking, conditional ("only if X happens"), or speculative.
6. **Close the current session block**: append `Session ended <TIME> — duration ~<Xh Ym>.` to the bottom of the current `## Session — <DATE> ...` block. Compute duration from the session-start time.
7. **Update the cross-session "Time invested" line** at the top of the doc:
   - Read all `Session ended ...` durations in the doc
   - Recompute the total: `<total> across <N> sessions (<DATE>: <duration> · <DATE>: <duration> · ...)`.
8. Tell the user: `Research doc updated: <path> — session <duration>, total <total>` — one line.
9. **Offer the HTML deck**: ask once — *"Want me to generate an HTML presentation for this research? (`presentation.html`)"* — and respect the answer. Don't ask twice. If yes:
   - Read `~/.claude/skills/research/presentation-details.md` (research-specific overlay)
   - Read `~/.claude/skills/presentation/brief-format.md` (the presentation skill's contract)
   - Compose a brief at `<slug>_research/presentation-brief.md` per the contract, using the research overlay's slide outline + amber Reframe-border override
   - Dispatch a sub-agent that invokes `frontend-design`, reads `~/.claude/skills/presentation/SKILL.md` in full, reads the brief, renders the deck, and runs the verification grep before reporting done

Do not write a prose summary to the user at the end. The doc is the summary. If the user wants a verbal summary, they will ask.

## HTML deck protocol

The deck is rendered by the generic `presentation` skill at `~/.claude/skills/presentation/`. Research-specific overlay (slide outline, Reframe-border treatment, brief composition guidance) lives at `~/.claude/skills/research/presentation-details.md`.

The flow when offering the deck (Step 4.9 above): read both files, compose a brief per `~/.claude/skills/presentation/brief-format.md`, dispatch a sub-agent that follows `~/.claude/skills/presentation/SKILL.md`. The generic spec has the mandatory invariants (`<base target="_blank" />`, hash routing per slide) and the verification grep — don't try to remember them, just point the sub-agent at the spec.

## Step file format

A step file is a working scratchpad, not a polished doc. Edit in place when later context refines a finding. Keep it minimal. Default template:

```
# Step N — [short title] (<DATE> <TIME>)

*(Companion to: ../research-notes.md, this step's high-level narrative)*

## Summary

<2-3 sentences on what this step investigated and what came out of it>

## References

- [Title](url) — one-line note on what this said and why it mattered
- [Issue/PR #1234](url) — one-line note
- ...

## Sub-agent findings

*(Paste sub-agent reports here verbatim. Trim only obvious filler. Keep URLs, file paths, code refs, and quoted source intact.)*

> Verbatim or near-verbatim sub-agent output goes here.

## Code refs

- `path/to/file.py:42-58` — what this code does and why it matters here
- `path/to/file.py:120` — ...

## On-the-wire / direct evidence

*(mitm captures, error messages, log output, raw API responses — the actual artefacts you saw.)*

```json
{ "raw": "evidence" }
```

## Rejected alternatives investigated

*(For steps where alternatives were considered and rejected. The *why* lives here.)*

### <alternative name>

What it would have looked like, what evidence we gathered, why we ruled it out.

## Notes / dead ends

*(Stuff that didn't pan out but is worth a line so future-you doesn't re-explore it.)*

- Tried X, found Y, didn't pursue because Z
```

Not every section is required for every step. Use what's relevant. A step where a single GitHub issue was decisive might be 5 lines total.

## Main-doc step format

The main doc is the *scannable narrative* — the place a future reader (often you in two weeks) reads top-to-bottom to understand the arc. Step bodies in the main doc should be **roughly 5 sentences** — enough to convey what happened and why it mattered, not enough to require careful reading. Detail lives in the step file.

Step headings carry an inline `(HH:MM)` timestamp. Add a `*(See detail: ...)*` pointer ONLY if a step file actually exists. Model the structure after:

```
## Step N — [short title] (HH:MM)

<1-2 sentences on what was investigated and what was found.>
<1-2 sentences on the key piece of evidence or — for steps that reframed the plan — what shifted and why.>

**Decision**: <one sentence on the call made.>

*(See detail: steps/step-N-<slug>.md)*  ← include only when a step file exists
```

Optional fields when relevant:
- **`**Reframe**: <one sentence>`** — call out steps where the discovery changed the overall plan. These are the highest-value moments in the narrative; flag them.
- **`**Side-tasks noted**: <bulleted list>`** — only if this step surfaced followups that don't fit the cross-step "Open questions" section.

The aim: a reader can skim every step body in under a minute and understand the arc. Anyone who wants the receipts (mitm dumps, full sub-agent findings, GitHub issues) clicks into the step file.

**What stays in the main doc and not the step files:**
- Decisions and rejected alternatives table (cross-step synthesis)
- Time invested + session blocks
- Open questions across all steps
- Quick reference — files touched / files investigated

These are genuinely cross-step views that step files can't provide.

## Companion docs

If the session produces a detailed design, spec, or patch proposal for a specific sub-problem, offer to write it to a companion file in the same `<slug>_research/` directory. The research-notes.md should reference it with a one-line pointer: `*(See companion doc: <filename>)*`.

Do not inline long specs or patch designs into research-notes.md — it makes the chronological narrative hard to follow.

## Notes

- The doc is for a future reader (often the user themselves in two weeks). Write as if the reader knows the technology but does not remember this session.
- File paths in the doc should be absolute where they are the primary reference, relative where context makes the repo obvious.
- A short doc is better than no doc — if the topic turns out simpler than expected (one or two findings), keep the doc anyway.
