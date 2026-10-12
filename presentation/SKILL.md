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
  asks for an interactive presentation. Otherwise use deck or page, even for
  deep-dive explainers. Why: it is a more involved build and should be chosen deliberately. It can
  add clickable drill-down nodes, so the reader goes from the whole system
  down to code.

## Workflow

1. **Plan / optional brief** — Read [briefs/common.md](briefs/common.md) and the brief file
   for the format: [deck](briefs/deck.md), [page](briefs/page.md), or
   [interactive](briefs/interactive.md). Create a concise plan; save a complete brief in the task output directory when a handoff, reproducibility, or explicit specification warrants it. Before rendering, check that the
   plan or brief preserves important mechanism detail from the source. Keep it lean by
   replacing vague summaries with concrete examples or labelled flows, not by
   adding more prose.
2. **Render** — the main assistant owns and builds the artifact by default, using the full conversation and source context to make narrative and visual decisions. A brief is a useful planning and reproducibility artifact, not a mandatory context handoff. For deck and page, the main assistant reads [renderer-guide.md](references/renderer-guide.md), [content-quality.md](references/content-quality.md), the selected format reference, and [verification.md](references/verification.md). For interactive, follow "Interactive build" below. Delegate rendering only when the work is independently scoped, the main context is overloaded, or a measured benchmark supports delegation. If delegating, provide the renderer the brief, sources, acceptance criteria, and this instruction:

   > You are the renderer. Read the renderer guide and render the artifact yourself. Do NOT create or dispatch any sub-agents.

   The artifact owner runs:

   ```bash
   python3 scripts/presentation_artifact.py init \
     --format <deck|page|interactive> \
     --output <path>
   # Edit the initialized artifact per the renderer guide.
   python3 scripts/presentation_artifact.py lint \
     --format <deck|page|interactive> \
     --output <path>
   python3 scripts/presentation_artifact.py verify \
     --format <deck|page|interactive> \
     --output <path>
   ```

   Do not read the script or template files merely to initialize the artifact. The initializer selects the template and backs up an existing output automatically. For decks, it copies bundled syntax-highlighting files to `assets/highlightjs-11.10.0/` beside the HTML. Keep that folder when sharing. Both lint and browser verification must pass. Inspect the verification bundle's contact sheet and flagged screenshots, repair issues, and rerun checks. Automated checks cover structure, geometry and interactions; they do not replace judgment about narrative clarity and visual quality. For complex, high-stakes, or visually ambitious work, optionally dispatch an **independent reviewer** after the first successful render. Give the reviewer rendered screenshots and the intended audience/goal; ask for specific, actionable issues without editing the artifact. The main assistant applies fixes and verifies again. Do not dispatch a reviewer merely to repeat automated checks.
3. **Report** the completed HTML, lint result, browser verification result,
   and verification bundle. Never call an artifact verified after lint alone.

## Interactive build

The main assistant builds both the interactive stage/explore controls and the explanatory chapters by default. Write a stage spec before writing chapters so interactions and prose agree. Run `init --format interactive`, implement in small incremental edits per the renderer guide, and run `lint`, `verify`, and the self-check in [references/interactive.md](references/interactive.md). Inspect screenshots and exercise drill-down interactions.

Optionally delegate an independently scoped stage or chapter implementation if there is a concrete context-capacity or parallelism benefit. Establish a shared stage spec and acceptance criteria first; avoid two sequential agents solely for role separation. The main assistant integrates and owns the final verification. An independent visual/narrative reviewer is optional for complex work, not mandatory.

### Watching the build

Long, uncommitted responses can stall and lose work. Follow "Write in small pieces" in the renderer guide regardless of who builds. When work is delegated, run this once in the background rather than polling manually:

```bash
python3 scripts/stall_watch.py <output> [--stall-minutes 15] [--max-minutes 120]
```

On `STALLED`, interrupt and resume the same agent, instructing it to make a small edit immediately; do not restart from scratch. Report stalls to the user.

## Feedback revisions

The artifact owner (normally the main assistant) handles revisions in the existing context. If rendering was delegated, resume the same renderer when practical. Do not create a new brief for small changes; update it only when purpose, structure, or source of truth changes.

Map user comments to exact slides/elements, read the target HTML before editing, and preserve accepted material. Do not rerun `init` for revisions. Run `lint` and `verify`, inspect the contact sheet and flagged screenshots, and report each requested change as passed or unresolved. Use independent review only when it adds judgment beyond these checks.

## Calling-skill contract

A calling skill may invoke this skill after assembling source material. The caller normally retains ownership and builds the artifact directly, preserving conversation context. Create a brief using [briefs/common.md](briefs/common.md) and the format-specific file when a durable plan or explicit handoff is useful. If rendering is delegated, pass the brief, sources and acceptance criteria, and prohibit nested delegation. The artifact owner must complete verification and report the result.

## Resource loading

- Artifact owner: `references/renderer-guide.md`, `references/content-quality.md`, the selected format reference, and `references/verification.md`; for decks also `references/deck-snippets.md`; optionally `briefs/common.md` and the format brief.
- Delegated renderer: the same renderer resources plus the brief and source material.
- Independent reviewer (optional): rendered screenshots, audience/goal, and quality criteria; no artifact edits.
- `scripts/presentation_artifact.py` selects and copies the template; no need to read template source just to initialize.

