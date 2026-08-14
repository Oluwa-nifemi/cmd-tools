---
name: presentation
description: Build a self-contained HTML deck or one-page presentation. Use when the user asks to make, render, or present a deck, slides, one-pager, scoped page, or tech talk.
---

# Presentation skill

## Workflow

1. **Brief** — Read [brief-format.md](brief-format.md). Create or receive a
   complete brief. Save it in the task output directory.
2. **Render** — either do it yourself, or dispatch exactly one sub-agent.
   If you dispatch a sub-agent, you MUST include this line in its prompt:

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

## Calling-skill contract

A calling skill may use this skill after it has assembled the source material.
It must create the brief using [brief-format.md](brief-format.md), then
render or dispatch exactly one sub-agent to render. When dispatching, the
caller MUST tell the sub-agent not to delegate further — include the line
from step 2 above in the dispatch prompt. The sub-agent must not read:

- `template.html`
- `page-template.html`
- `references/renderer-guide.md`
- the renderer's format-specific references

## Resource loading

- Brief author: `brief-format.md` only.
- Renderer (whether root agent or sub-agent): `references/renderer-guide.md`,
  `references/content-quality.md`, one selected format reference, and
  `references/verification.md`.
- `scripts/presentation_artifact.py` selects and copies the template. The
  renderer does not need to read either template.
