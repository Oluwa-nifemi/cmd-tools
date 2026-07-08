# Research presentation overlay

This file is the **research-specific layer** for deck rendering. The full rendering spec — aesthetics, code modal architecture, navigation, mandatory invariants, sub-agent dispatch protocol — lives in the generic presentation skill at `~/.claude/skills/presentation/SKILL.md`.

When the research skill renders a deck, it composes a presentation brief (per `~/.claude/skills/presentation/brief-format.md`) using this overlay's slide outline + aesthetic override, then dispatches the rendering against the generic spec.

**The dispatched sub-agent MUST read `~/.claude/skills/presentation/SKILL.md` in full before writing any HTML.** This is non-negotiable — past renders missed the mandatory invariants because the sub-agent skimmed the spec. Include this instruction verbatim near the top of the brief.

## Aesthetic override

Add this single line to the brief's "Aesthetic overrides" section:

> Special treatment: Slides whose source markdown contains `**Reframe**:` get an amber left-border (`border-left: 4px solid #c8860a`). Reframes are inflection points — moments the investigation pivoted — and visually distinguishing them tells the audience "this is where the plan changed."

Everything else uses the generic skill's defaults (warm off-white background, Palatino/Georgia/Menlo, calm green accent).

## Slide outline (research deck)

Map the research corpus to slides in this order. Forward-looking sections (Open questions, Next steps) come before the deep-dive divider so non-technical viewers can leave after the high-level outcome.

1. **Cover** — title, investigation line (research-notes.md's "Investigation:" line), time invested, session count
2. **Where we landed (After)** — distill the Decisions table or any "Outcome at a glance → After" framing into the wins. Bullets, not paragraphs. Use the calm green accent on shipped/decision markers.
3. **Before (real prod)** — short, stark. The actual baseline before the investigation. **CRITICAL**: don't conflate prod state with discoveries. Pull from the "Outcome at a glance → Before" section verbatim if present, else from the research-notes.md narrative's prod-state framing.
4. **What we found** — the constraints that ruled out simpler solutions. Pull from "Outcome at a glance → What we found" if present, else from the research-notes.md narrative.
5. **Open questions** — render each open question as a bullet. **Omit this slide entirely if the Open questions section is empty.**
6. **Next steps** — prioritized list with Blocking / Recommended / Speculative markers preserved.
7. **Section divider — "The arc (deep dive)"** — explicit exit signal: "if you don't need the chronology, this is a natural stop."
8. **One slide per step** — chronological order of `steps/step-N-<slug>.md`. For each:
   - Collapsed: step's Summary section + the `**Decision**:` line (if present)
   - Expanded: the full step body (or a "Read more →" link to the step file if too long)
   - Apply the amber Reframe border if the step source contains `**Reframe**:`
9. **Section divider — "Decisions"**
10. **Decisions table** — render the research-notes.md Decisions table verbatim. Split across multiple slides if it doesn't fit. The "why rejected" column is the focal point — visually emphasize it with the calm green accent on the chosen approach and a more muted style on the rejected alternatives.
11. **Files reference / closing** — files investigated (from research-notes.md "Quick reference" sections), condensed.

## Brief composition

When composing the presentation brief for a research session:

- **Output path**: `<slug>_research/presentation.html`
- **Brief path** (where to write the brief itself): `<slug>_research/presentation-brief.md`
- **Title**: from research-notes.md's H1
- **Subtitle**: research-notes.md's "Investigation:" line
- **Cover metadata**: time invested, session count, date
- **Source files to read**: research-notes.md + every `steps/step-*.md` (use `ls steps/` to enumerate)
- **Code block candidates**: scan steps/*.md for code fences with non-trivial content (diffs, config blocks, request bodies). Only flag slides where the code is load-bearing for the slide's point — don't blanket-add "See code" to every step.

## What this overlay does NOT specify

Anything in `~/.claude/skills/presentation/SKILL.md` is the source of truth: aesthetic defaults, progressive-disclosure mechanism, code modal architecture, navigation, mandatory invariants (`<base target="_blank" />`, hash routing), verification grep. Don't duplicate those rules here.
