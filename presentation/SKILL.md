---
name: presentation
description: Build a self-contained HTML deck, one-page presentation, or interactive explainer. Use when the user asks to make, render, or present a deck, slides, one-pager, scoped page, tech talk, or an interactive presentation.
---

# Presentation skill

## Formats

- **deck**: slides for a talk.
- **page**: one scrolling document.
- **interactive**: a sticky visual model plus scrolling story chapters, for
  learning how something complex works. Use it ONLY when the user explicitly
  asks for an interactive presentation. Otherwise use deck or page. It can
  add clickable drill-down nodes, so the reader goes from the whole system
  down to code. Deep-dive codebase explainers use this.

## Workflow

1. **Brief** — Read [briefs/common.md](briefs/common.md) and the brief file
   for the format: [deck](briefs/deck.md), [page](briefs/page.md), or
   [interactive](briefs/interactive.md). Create or receive a complete brief.
   Save it in the task output directory. Before rendering, check that the
   brief preserves important mechanism detail from the source. Keep it lean by
   replacing vague summaries with concrete examples or labelled flows, not by
   adding more prose.
2. **Render** — for deck and page, dispatch exactly one renderer sub-agent.
   For interactive, see "Interactive build" below. The main assistant
   gathers requirements and reviews evidence; it does not edit the artifact
   unless the user explicitly asks it to. You MUST include this line in
   the sub-agent prompt:

   > You are the renderer. Read the renderer guide and render the deck
   > yourself. Do NOT create or dispatch any sub-agents.

   The renderer reads [renderer-guide.md](references/renderer-guide.md) and
   runs these commands:

   ```bash
   python3 scripts/presentation_artifact.py init \
     --format <deck|page|interactive> \
     --output <path>
   # Edit the initialized artifact per the brief and renderer guide.
   python3 scripts/presentation_artifact.py lint \
     --format <deck|page|interactive> \
     --output <path>
   python3 scripts/presentation_artifact.py verify \
     --format <deck|page|interactive> \
     --output <path>
   ```

   Do not read the script or any template file. The initializer selects
   the template and backs up an existing output automatically.
   `lint` checks source structure. `verify` opens the artifact with
   `agent-browser`, checks rendered geometry and interactions, and writes a
   verification bundle beside the artifact. Both must pass.
3. **Report** the completed HTML, lint result, browser verification result,
   and verification bundle. Never call an artifact verified after lint alone.

## Interactive build

This is an approved exception to the one-renderer rule. Dispatch two
renderer sub-agents, one after the other. Both use model
`anthropic-apikey/claude-opus-5-5`. Include the renderer line from step 2 in
both prompts.

1. **Stage builder**: runs `init --format interactive`, builds the stage and
   explore controls, and writes the stage spec beside the artifact.
2. **Writer**: starts after the stage builder finishes. It reads the brief and
   the stage spec, then writes the chapters for the brief's reader profile.

Each agent runs `lint` and `verify`. The writer also runs the self-check in
[references/interactive.md](references/interactive.md) and reports each item.
Do not dispatch a separate reviewer agent. For feedback revisions, resume the
writer for text changes and the stage builder for stage changes.

### Watching the build

A renderer can stall while producing one long response. It then fails and
loses everything it wrote in that response. Both prompts must tell the agent
to follow "Write in small pieces" in the renderer guide.

While an agent runs, check the artifact every 10 minutes. Look at its file
size and modified time. Treat the agent as stuck in either case:

- the artifact is unchanged 15 minutes after dispatch, or
- the artifact is unchanged for 20 minutes after that.

When an agent is stuck, interrupt it. Send it the "Write in small pieces"
rules and tell it to make an edit now. When an agent fails, resume the same
agent with the same message. Do not start over. Tell the user about each
stall.

## Feedback revisions

Keep the renderer agent ID after the first render. When the user gives feedback
on that artifact, resume the same renderer and send the feedback directly. The
renderer already knows the brief, sources, artifact, and visual decisions, so it
can make a surgical update and verify the result.

Do not create a new brief for a small feedback pass. Update the brief only when
the requested change alters the artifact's purpose, structure, or source of
truth. Start a new renderer only when the previous renderer cannot be resumed.

Before editing, turn every user comment into a numbered checklist mapped to an
exact slide and element. Read the exact target HTML immediately before each
edit. Preserve accepted slides and change only checklist targets unless a
sequencing change requires adjacent edits. Do not run `init` during a revision.

The resumed renderer must run `lint` and `verify`, inspect the generated contact
sheet and flagged screenshots, and report each checklist item as passed or
unresolved. Do not dispatch a second agent only to review its work.

## Calling-skill contract

A calling skill may use this skill after it has assembled the source material.
It must create the brief using [briefs/common.md](briefs/common.md) and the
format's brief file, then dispatch the renderer as described above. The caller
MUST tell each renderer sub-agent
not to delegate further — include the line from step 2 above in the dispatch
prompt. The calling skill must not read renderer-only resources or templates:

- `template.html`
- `page-template.html`
- `interactive-template.html`
- `references/renderer-guide.md`
- the renderer's format-specific references

## Resource loading

- Brief author: `briefs/common.md` plus the brief file for the format.
- Renderer sub-agent: `references/renderer-guide.md`,
  `references/content-quality.md`, one selected format reference, and
  `references/verification.md`.
- `scripts/presentation_artifact.py` selects and copies the template. The
  renderer does not need to read any template.
