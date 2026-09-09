---
name: presentation
description: Build a self-contained HTML deck or one-page presentation. Use when the user asks to make, render, or present a deck, slides, one-pager, scoped page, or tech talk.
---

# Presentation skill

## Workflow

1. **Brief** — Read [brief-format.md](brief-format.md). Create or receive a
   complete brief. Save it in the task output directory. Before rendering,
   check that the brief preserves important mechanism detail from the source.
   Keep it lean by replacing vague summaries with concrete examples or
   labelled flows, not by adding more prose.
2. **Render** — dispatch exactly one sub-agent. You MUST include this line in
   the sub-agent prompt:

   > You are the renderer. Read the renderer guide and render the deck
   > yourself. Do NOT create or dispatch any sub-agents.

   The renderer reads [renderer-guide.md](references/renderer-guide.md) and
   runs these commands:

   ```bash
   python3 scripts/presentation_artifact.py init \
     --format <deck|page> \
     --output <path>
   # Edit the initialized artifact per the brief and renderer guide.
   python3 scripts/presentation_artifact.py verify \
     --format <deck|page> \
     --output <path>
   ```

   Do not read the script or either template file. The initializer selects
   the template and backs up an existing output automatically.
3. **Report** the completed artifact and the verification result.

## Feedback revisions

Keep the renderer agent ID after the first render. When the user gives feedback
on that artifact, resume the same renderer and send the feedback directly. The
renderer already knows the brief, sources, artifact, and visual decisions, so it
can make a surgical update and verify the result.

Do not create a new brief for a small feedback pass. Update the brief only when
the requested change alters the artifact's purpose, structure, or source of
truth. Start a new renderer only when the previous renderer cannot be resumed.

The resumed renderer must apply the requested edits, run the deterministic
verification, and inspect the changed sections itself. Do not dispatch a second
agent only to review its work.

## Calling-skill contract

A calling skill may use this skill after it has assembled the source material.
It must create the brief using [brief-format.md](brief-format.md), then
dispatch exactly one sub-agent to render. The caller MUST tell the sub-agent
not to delegate further — include the line from step 2 above in the dispatch
prompt. The calling skill must not read renderer-only resources or templates:

- `template.html`
- `page-template.html`
- `references/renderer-guide.md`
- the renderer's format-specific references

## Resource loading

- Brief author: `brief-format.md` only.
- Renderer sub-agent: `references/renderer-guide.md`,
  `references/content-quality.md`, one selected format reference, and
  `references/verification.md`.
- `scripts/presentation_artifact.py` selects and copies the template. The
  renderer does not need to read either template.
