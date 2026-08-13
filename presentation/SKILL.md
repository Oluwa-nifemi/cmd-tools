---
name: presentation
description: Coordinate a self-contained HTML deck or one-page presentation. The main agent creates a brief and delegates all template reading and rendering to a dedicated renderer subagent. Use when the user asks to make, render, or present a deck, slides, one-pager, scoped page, or tech talk.
---

# Presentation coordinator

This skill is a coordinator. Do not read HTML templates or renderer rules in
the main task.

## Main-agent workflow

1. Establish the audience, purpose, format, and size. Ask only if the format
   cannot be determined. Default size to lean.
2. Read [brief-format.md](brief-format.md). Create a complete brief and save
   it in the task output directory.
3. Dispatch one renderer subagent. Give it:
   - the brief path;
   - the source files named in the brief;
   - [renderer-guide.md](references/renderer-guide.md);
   - the requested output path.
4. Tell the renderer to run these commands exactly:

   ```bash
   python3 scripts/presentation_artifact.py init \
     --format <deck|page> \
     --output <path>
   # Render the artifact.
   python3 scripts/presentation_artifact.py verify \
     --format <deck|page> \
     --output <path>
   ```

   The renderer must not read the script or either template. The initializer
   selects the template and backs up an existing output automatically.
5. Report the completed artifact and the renderer's verification result.

For a direct user request, always delegate the rendering. Do not use an
inline rendering shortcut.

## Calling-skill contract

A calling skill may use this skill after it has assembled the source material.
It must create the brief using [brief-format.md](brief-format.md), then
dispatch the renderer as described above. It must not read:

- `template.html`
- `page-template.html`
- `references/renderer-guide.md`
- the renderer's format-specific references

## Resource loading

- Main agent and caller: `brief-format.md` only.
- Renderer subagent: `references/renderer-guide.md`,
  `references/content-quality.md`, one selected format reference, and
  `references/verification.md`.
- `scripts/presentation_artifact.py` selects and copies the template. The
  renderer does not need to read either template.
