---
name: deep-dive
description: Produce detailed, plain-language presentation decks that explain how a codebase (or a section of one) works. Use when the user asks to "deep dive into this repo", "explain this codebase", "onboard me into this project", "break down this PR", "walk me through this folder", or wants to understand unfamiliar code through structured visual presentations. Targets a repo root, a subfolder, a PR, or a file glob. Outputs slide decks with progressive disclosure, SVG diagrams, and worked examples — optimized for someone encountering the code for the first time.
---

# Deep Dive

Produce presentation decks that make unfamiliar code deeply understandable. The reader should be able to walk through the decks and understand what the system does, how it works, and why it was built that way — without reading the source code themselves.

This skill combines orchestrated multi-agent research (reading actual source code) with the `$presentation` skill's deck format (slides with progressive disclosure). It does not guess or summarize from file names; investigators read every file in full.

## When to use

- "Deep dive into this repo"
- "Explain how this codebase works"
- "Onboard me into this project"
- "Break down this PR for me"
- "Walk me through src/muninn/"
- Any request to understand unfamiliar code through structured presentations

## Target types

| Target | What happens |
|---|---|
| Repo root (default) | Scan the full repo, decompose into natural subsystems, one deck per subsystem |
| Subfolder | Scope investigation to that subtree only |
| PR (URL or branch) | Read the diff + surrounding context, explain what changed and why |
| File glob or list | Read those files, explain their roles and interactions |

## Start

1. Identify the **target** (repo, folder, PR, or files) and confirm with the user.
2. Ask two questions:
   - **Depth**: lean (quick overview, 3–5 slides per deck) or comprehensive (full walkthrough, 8–15+ slides per deck)? Default to comprehensive unless the user says otherwise.
   - **Focus areas**: any specific parts they care about most, or cover everything?
3. Read [references/investigation.md](references/investigation.md) for the investigation protocol.
4. Read [references/deck-principles.md](references/deck-principles.md) for the presentation principles.
5. Create `local/<target-slug>-deep-dive/` for all artifacts.
6. Proceed to investigation.

## Investigation phase

Read [references/investigation.md](references/investigation.md) before dispatching agents.

The investigation uses `$orchestrate` in research mode with parallel investigators. Each investigator reads actual source files line by line and writes a structured step file. Do not skip this phase or substitute it with summaries from README files.

## Presentation phase

Read [references/deck-principles.md](references/deck-principles.md) before composing briefs.

After investigation, produce slide decks using `$presentation` in deck format. One deck per investigation area, plus bonus deep-dive decks for complex algorithms or concepts the user flags.

## Follow-up and refinement

When the user comments on slides (via browser comments, annotations, or messages):

1. Answer their questions directly — plain language, concrete.
2. Update the relevant deck(s) with note-boxes that bake the clarification into the slides so future readers get it without asking.
3. If a question reveals a concept that needs its own dedicated deck (the user says "I don't understand X"), dispatch a focused researcher at high reasoning effort to study that specific topic from the source code, then render a bonus deep-dive deck.

## Finish

Report:
- List of all decks produced with paths
- Suggested reading order
- Any areas that were too large or complex to cover in this pass
