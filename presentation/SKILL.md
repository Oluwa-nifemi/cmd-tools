---
name: presentation
description: Render a self-contained HTML artifact from caller-provided content, in one of two formats — a slide `deck` (multi-slide, hash-routed, for live presenting/tech talks) or a one-page `page` (scrollable, anchor-TOC, nested collapsible sections, for scoped docs/handoffs). Editorial/typewriter aesthetic shared by both. Designed to be invoked by other skills (e.g. /research, codebase tour, sprint retro, /handoff) — the caller composes a presentation brief and this skill renders the chosen format. Triggers when the user says "render the deck", "make the presentation", "present the deck", "tech talk" → deck; "one-pager", "quick scoped page", "single page", "scoped doc", "for reference/handoff" → page; or a calling skill invokes this skill explicitly.
---

# presentation

Generates a single self-contained HTML artifact from a caller-provided brief, in one of two formats: a **deck** (hash-routed slides) or a **page** (one scrollable document). Editorial/typewriter aesthetic, progressive-disclosure expandable content, shared between both.

## Format modes: deck vs page

Two renderer outputs, one shared aesthetic:

- **deck** — multi-slide, hash-routed (`#page-N`), built for live presenting/tech talks where a presenter walks an audience through slides at their own pace. Uses `template.html`. Slide-level progressive disclosure (`▸ Details`), code modals, slide counter, TOC overlay.
- **page** — one scrollable document meant to be read at the reader's own pace, not presented live. Uses `page-template.html`. Anchor-link TOC (`href="#section-id"`), two-level native `<details>/<summary>` disclosure, no slide chrome.

The renderer branches on the brief's `format` field (see `brief-format.md`). Everything else in this file that's deck-specific is marked as such; content-authoring principles (don't compress the source, verify claims, real SVGs, etc.) apply to both formats.

## Confirm audience, purpose, and format first

Before rendering, establish three things:

- **AUDIENCE** — execs / eng / mixed / self. Tunes depth: execs get shorter content, fewer or no code modals; eng keeps deep-dive detail and code.
- **PURPOSE** — tech talk / decision doc / scoped plan / status.
- **FORMAT** — deck or page.

**When these aren't clear from the brief or the prompt, default to asking** — 2-3 questions via AskUserQuestion — rather than assuming. Don't silently pick a format and render.

Heuristics for when NOT to ask (the signal is already unambiguous):
- Explicit "one-pager" / "scoped" / "for reference" / "handoff" → page.
- Explicit "tech talk" / "present" / "walk through" → deck.
- A large source with many independent, live-presentable sections → deck.

Scope note: many independent sections you'll present live → deck; one scoped artifact meant to be read or handed off → page. The "don't compress the source" rule (below) applies to both formats regardless of which one is chosen.

## When invoked

This skill is normally invoked **by another skill** (the caller). The caller:
1. Reads `brief-format.md` in this skill folder to know the contract
2. Composes a presentation brief — a single markdown file at a path the caller chooses
3. Dispatches a sub-agent with this skill's `SKILL.md` + the brief path

It can also be invoked directly by a user with a hand-written brief.

## How to invoke (calling-skill protocol)

A caller runs this protocol:

1. **Confirm audience, purpose, and format** per the section above — ask if unclear.
2. **Compose a brief** following the schema in `brief-format.md`, including `format:`, `audience:`, `purpose:`. Save it (e.g. `<output-dir>/presentation-brief.md`).
3. **Dispatch a sub-agent on Sonnet** (Opus if budget allows). Brief the sub-agent to:
   - Invoke the `frontend-design` skill as its first action
   - Read this `SKILL.md` end-to-end
   - Read the presentation brief at the path provided, and check its `format` field
   - Read every source file enumerated in the brief
   - **Check whether the output file already exists at the output path; if so, follow the "Re-rendering over an existing deck" protocol — inventory, audit for staleness, and preserve hand-added content rather than overwriting**
   - **Pick the template by format: `template.html` for `format: deck`, `page-template.html` for `format: page`** (see "Start from the template" below). Do NOT hand-author the chrome — it is already correct. Fill the content block with the brief's material; leave the CSS and JS untouched.
   - Render the output HTML at the brief's output path
   - Run the relevant verification grep before reporting done (a one-shot confirmation the template chrome survived — not a build-then-fix loop)

Note: the two templates' `:root` aesthetic tokens (colors, fonts) are kept byte-identical on purpose — that shared block is the one visual system both formats present. If you ever override a token for one format, consider whether the other needs the same override for consistency.

If `frontend-design` is not installed, prompt the user to install it from `https://github.com/anthropics/claude-code/tree/main/plugins/frontend-design/skills/frontend-design` before proceeding.

## Start from the template (don't re-derive the chrome)

`template.html` in this skill folder is a **correct-by-construction skeleton**. It already contains every hard invariant below — base target, hash routing, print stylesheet, export button, nav/TOC, details toggles, code modal — plus the aesthetic tokens and reusable component patterns (stat cards, note boxes, badges, SVG wrapper). **Copy it to the output path and fill only the content**, then leave everything below the `<!-- SLIDES:END -->` marker untouched.

Rules:
- Each slide is `<section class="slide" data-title="Short TOC label"> … </section>`. The cover is the first slide (add class `cover`).
- **Strip the template's instructional header comment** (the `<!-- ... PRESENTATION TEMPLATE ... -->` block between `<!DOCTYPE html>` and `<html lang="en">`) from the rendered deck — it's scaffolding for the filler, not part of a finished deck. Also replace both `TITLE_PLACEHOLDER` occurrences and `SUBTITLE_PLACEHOLDER`; a `grep -c PLACEHOLDER <output>` must return 0.
- **Navigation is derived from the DOM** — it queries `.slide` elements and their `data-title`. There is NO positional `TITLES` array, `TOTAL` count, or `slide-N`/`toggle-N` ID to maintain. Add, remove, or reorder slides freely; the counter, TOC, hash routing, and details/code wiring all just work. Do not reintroduce positional bookkeeping.
- Do not rewrite the `<style>` block or the `<script>` block. Override an aesthetic token (the `:root` vars) only if the brief's "Aesthetic overrides" says so.
- The invariants below are therefore **already satisfied by the template**. You are not building them; you are not allowed to break them. The grep in "Confirm completion" is a one-shot sanity check that the template chrome survived your content edits — NOT a generate → inspect → fix loop. If the grep fails, you edited something you shouldn't have; restore it from the template rather than patching.

## Page-mode invariants (guaranteed by `page-template.html` — do not re-author)

These apply to **page mode only**. They are the page equivalents of the deck's mandatory invariants below, and are explicitly NOT the same list — page mode has no hash routing, no slide counter, and no per-slide nav, by design (it's one scrollable document, not a sequence of slides).

- **`<base target="_blank">`** in `<head>` — same reasoning as deck: a reader clicking a link should never lose their place.
- **Anchor-link TOC** — `<nav class="toc">` with plain `href="#section-id"` links, one per top-level section. Not hash-routed; the browser's native anchor scroll handles navigation.
- **Two-level `<details>/<summary>` disclosure** — top-level `<details class="section" id="...">` sections, each optionally containing nested `<details class="sub">` sub-items. No custom JS toggle logic; the browser's native disclosure behavior is the mechanism.
- **Print stylesheet + Export button** — `@media print` forces every `<details>` open (collapsed content must not be lost in the PDF), hides the TOC and export button, and lets the browser paginate the flattened document naturally — no `break-after`/pagination hacks. An `.export-btn` calls `window.print()` directly, same pattern as the deck.
- **No remote dependencies** beyond what the deck allows (highlight.js CDN, only if the brief calls for code blocks).

Explicitly NOT part of page mode (these are deck-only, see "Mandatory invariants" below): hash routing / `window.location.hash`, a slide counter, per-slide prev/next nav, the TOC *overlay* (page mode's TOC is inline in the flow, not an overlay).

The "don't compress the source" rule and every content-quality principle later in this file (density, real SVGs, verify claims, etc.) apply to page mode exactly as they do to deck mode — only the chrome differs.

## Reviewer comments (both formats — guaranteed by both templates, do not re-author)

Both templates ship an inline commenting feature, Confluence/Notion-style, so a reader can leave notes directly on the rendered output instead of copying quotes into a separate notes file:

- **Select any text** anywhere in the content (a word, a sentence, a whole bullet, a code line — not limited to a fixed list of commentable elements) and a small **💬 Comment** bubble appears near the selection. Click it to open a popup, type a note, and save.
- Saved comments persist in the browser's `localStorage`, keyed by the file's path, so they survive a reload of the same rendered file.
- **Comments (N) button** opens a side panel listing every saved comment with its location (slide/section) and the exact quoted text, each deletable individually.
- **"Copy for Claude Code"** in that panel formats all comments as a numbered plain-text list (`[location] on: "quote" → note`) and copies it to the clipboard in one click — paste directly into a Claude Code prompt instead of manually transcribing feedback.
- This is additive chrome living in its own `<script>`/`<style>` block appended after the invariant deck/page script — it does not touch hash routing, slide nav, or the details/summary disclosure logic. Do not remove it when filling content, and do not re-derive it per render (it's already correct in both templates).
- Known limitation: the inline 💬 marker inserted at a comment's location does not survive a page reload (it's a plain DOM node, not persisted). The comment text, its location, and the export function are unaffected — only the in-place marker icon disappears on reload; the panel is always the reliable way to review everything saved.
- Known limitation: the inline 💬 marker on a specific line does not survive a page reload (the underlying `data-cid` is assigned lazily on first comment and isn't stable across re-renders of the same HTML). The comment text itself, its location, and the export function are unaffected — only the in-place marker icon needs a fresh click-through via the panel to relocate.

## Mandatory invariants (deck mode only — guaranteed by the template — do not re-author or re-verify beyond the one-shot grep)

These have been missed in past hand-authored renders, which is exactly why they now live in `template.html` instead of being rebuilt each time. They are non-negotiable and already present in the template.

### 1. `<base target="_blank" />` in `<head>`

Every hyperlink in the deck must open in a new tab — a presenter clicking a link mid-talk should never lose their slide.

```html
<head>
  <base target="_blank" />
  ...
</head>
```

This affects every link in the document automatically. Do NOT set `<base href="...">` alongside it (that would break relative URL resolution).

### 2. Hash routing per slide

Each slide must have a hash-addressable URL so reload preserves position and the user can deep-link.

Implementation contract:
- On slide change, update `window.location.hash` to `#page-<N>` (1-indexed).
- On page load, parse `window.location.hash`; if it matches `#page-<N>` and N is in range, navigate to that slide instead of slide 1.
- Listen for `hashchange` so manual URL edits navigate correctly.
- Use `history.replaceState` (no back-button entry per slide) OR `pushState` (back-button walks slides). Pick one and be consistent.

### 3. Print stylesheet and Export button

Every deck must be self-serve exportable to PDF via the browser's print dialog. No headless Chrome required for the presenter.

#### `@media print` stylesheet

The print view is a **single flat document** — all slides stacked vertically in normal flow, no pagination. Do not use `break-after: page`. Forcing one slide per page creates whitespace gaps on short slides and mid-content cuts on tall ones. Let the browser paginate naturally; `break-inside: avoid-page` keeps individual slides together when they fit on one page.

Include this block (or equivalent) in the deck's `<style>`:

```css
@page {
  size: 297mm 210mm;   /* A4 landscape */
  margin: 15mm 20mm;
}

@media print {
  /* ── Reset JS-driven layout ── */
  /* The slides wrapper clips overflow and uses position:relative for the
     absolute-positioned slides. Undo all of that for print. */
  body,
  .slides-container,
  [id^="slide-"] ~ *   { position: static !important; height: auto !important;
                          overflow: visible !important; }

  /* Override JS-driven show/hide — make every slide visible and in-flow */
  .slide              { display: block !important;
                        position: static !important;
                        inset: auto !important;
                        opacity: 1 !important;
                        pointer-events: none;
                        height: auto !important;
                        min-height: 0 !important;
                        overflow: visible !important;
                        padding: 1.5rem 2rem 1rem !important;
                        /* No break controls — completely natural flow.
                           break-after:page forces whitespace gaps on short slides;
                           break-inside:avoid-page pushes slides to the next page and
                           leaves empty space behind. Let the browser paginate freely. */
                        border-bottom: 2px solid #d8d2c6;
                        margin-bottom: 2rem; }

  /* Force progressive-disclosure panels open — collapsed content is lost in PDF */
  .details-panel      { display: block !important; max-height: none !important;
                        overflow: visible !important; }

  /* Hide nav chrome, TOC overlays, slide counter, and the export button itself */
  .nav-controls,
  .toc-overlay,
  .slide-counter,
  .export-btn         { display: none !important; }

  /* Preserve themed backgrounds and SVG colours */
  *                   { print-color-adjust: exact; -webkit-print-color-adjust: exact; }

  /* Code modals are secondary — leave hidden */
  #code-modal         { display: none !important; }
}
```

Adapt selector names to match what the deck actually uses (`.slide`, `.details-panel`, `.slides-container` are the canonical class names used elsewhere in this spec).

#### Export button

Place a **"Export to PDF"** button in the deck's persistent nav area (alongside the prev/next controls and TOC button, bottom-right). It calls `window.print()` directly. Style it to match the deck's nav chrome.

Minimal implementation:

```html
<button class="export-btn" onclick="window.print()" title="Export to PDF">
  Export PDF
</button>
```

```css
.export-btn {
  /* Match the nav button aesthetic from the navigation section */
  font-size: 0.8rem;
  opacity: 0.6;
  cursor: pointer;
  /* hidden in print via the @media print block above */
}
.export-btn:hover { opacity: 1; }
```

The button may also appear on the last slide if the design calls for a closing affordance, but the nav-area placement is mandatory so it's always accessible.

#### Self-serve export note

This makes PDF export self-serve: presenter opens the deck, clicks "Export PDF", selects "Save as PDF" in the print dialog. Landscape `@page` size ensures slides fill the page.

For batch or automated export, headless Chrome works with no changes to the HTML:
```bash
chrome --headless --print-to-pdf=deck.pdf --no-pdf-header-footer presentation.html
```

### Verification grep

Before reporting `Presentation rendered: <path>`, run:

```bash
grep -E '<base target="_blank"|window\.location\.hash|hashchange|media print|export-btn' <path-to-presentation.html>
```

All five patterns must appear. If any is missing, fix and re-verify.

## Re-rendering over an existing deck (additive + reconciled)

**Before writing `presentation.html`, check whether a file already exists at the brief's output path.** If it does, you are NOT rendering from scratch — you are updating an existing deck. Overwriting it blindly destroys work, and this has burned users: a prior deck had hand-added images and tuned slides, a new brief was rendered, and everything not in the new brief was wiped.

When a deck already exists at the output path, follow this protocol instead of a clean render:

### 0. Back up the existing deck first

Before reading or rewriting anything, snapshot the current file so a bad re-render is always recoverable. Copy it into a `.backups/` folder beside the output path with a timestamped name:

```bash
OUT="<absolute output path>"          # e.g. /Users/me/proj/local/foo/presentation.html
DIR="$(dirname "$OUT")"
mkdir -p "$DIR/.backups"
cp "$OUT" "$DIR/.backups/presentation-$(date +%Y%m%d-%H%M%S).html"
```

This runs only when a deck already exists — a first-time render has nothing to back up. The backup is the safety net for the reconciliation steps below; if the merge goes wrong, the prior deck is intact in `.backups/`. Mention the backup path in the completion report. Don't prune old backups unless the user asks.

### 1. Inventory the existing deck

Read the existing `presentation.html` end-to-end and catalog what it contains that the brief may not account for:
- Embedded images — `<img>` tags, inline `<svg>` diagrams, `data:` URIs, `background-image` URLs
- Slides with no corresponding entry in the brief's slide outline (hand-added slides)
- Hand-tuned content within slides that the brief covers (custom prose, annotations, reordered bullets)
- Aesthetic customizations applied directly to the HTML that aren't expressed in the brief

### 2. Audit for staleness

The existing deck may be out of date relative to the current source files. Don't just preserve it verbatim — reconcile it:
- For every slide the brief covers, compare the existing slide's content against the current brief + source files. Where the source has changed, **update the slide** to match. Stale facts, superseded decisions, and renamed/removed items get corrected.
- Where the brief adds slides the existing deck lacks, add them.
- Where the brief no longer covers a slide that exists in the deck **and** that slide is purely brief-derived (no hand-added images or custom content), it may be removed — the brief is authoritative for brief-derived content.

### 3. Preserve what the brief doesn't own

Content that originated outside the brief is NOT the brief's to delete:
- **Embedded images and custom diagrams must survive the re-render.** If a slide had an `<img>` or hand-drawn `<svg>` and the brief doesn't mention it, carry it forward onto the corresponding slide. Never drop a user-added asset because the brief is silent about it.
- Hand-added slides survive unless the brief (or the user) explicitly says to remove them.
- When a brief change conflicts with hand-tuned content on the same slide (e.g. the brief updates a bullet the user had customized), apply the brief's factual update but keep the user's surrounding edits where they don't contradict the source. If the conflict is genuine and unresolvable, keep both and flag it in the completion report rather than silently choosing.

### 4. Report what changed

In the completion report, summarize the reconciliation: slides updated, slides added, slides removed, and any preserved assets (images/custom slides) carried forward. This makes the additive behavior auditable. If anything was ambiguous (a brief change conflicting with hand-tuned content), call it out explicitly.

The net effect: a re-render brings brief-derived content up to date with current sources **and** keeps everything the user added by hand. It is never a destructive overwrite.

## One artifact, not two

Generate a single self-contained `presentation.html`. Inline CSS + JS. No remote fonts or icons. highlight.js may be loaded via CDN per the Code Blocks section; that is the only allowed remote.

Do NOT generate a long-form document HTML alongside the deck. The brief's source files are the source of truth; the deck is the designed view.

## Aesthetic — prescribe, don't freelance

The default aesthetic is **editorial/typewriter**. Use these values unless the brief overrides them:

- Background: warm off-white (`#f5f3ee` family)
- Ink: near-black, comfortable reading size
- Display font: Palatino-family. Body: Georgia. Mono: Menlo. All system fonts.
- Single accent: a calm green (manuscript-annotation feel, e.g. `#3a6b3a`), used sparingly for "Decision" / "shipped" markers
- Light theme. Do not force dark mode. Do not use purple gradients, "tech startup" aesthetics, or generic AI slop tropes
- Restrained motion — at most a 0.35s opacity cross-fade between slides. No scattered micro-interactions.

The brief MAY override specific values (caller's "Aesthetic overrides" section). It MAY add slide-specific treatments (e.g. "slides marked X get an amber left-border"). Apply overrides additively on top of the defaults.

If the brief doesn't override anything, render with the defaults. Never freelance.

## Slide structure

The brief's "Slide outline" section is the authoritative slide-by-slide content. Render slides in the order listed.

This skill has no opinion on slide count, slide titles, or section structure — those are caller concerns. The skill DOES have opinions on how individual slides are rendered (progressive disclosure, code modals, navigation, hash routing).

### Don't compress the source

The renderer's job is to lay out the brief's content well, not to editorialize it. **Render every item the brief lists; don't merge similar items into ranges or summary phrases just to reduce slide count or "look cleaner."**

Concrete failure modes to avoid:
- Brief lists 9 phases. Renderer outputs `Ph 1-3 → fresh checkout / native-proxy / migrate-v2.sh`, `Ph 8-9 → cleanup / migrate skill`. Result: 5 visible items instead of 9. The reader has to mentally unpack the merged ranges. **Wrong.** Render 9 separate items.
- Brief lists 9 deliverables. Renderer outputs a single bullet "9-PR stacked migration strategy." **Wrong.** Enumerate them.
- Brief has a 5-row decisions table. Renderer condenses to "Several decisions made — see details." **Wrong.** Render the table.

The right calibration: **scannable, not compressed.** Bullets and short prose are fine; merging items isn't. Each entry the brief specifies gets its own visible line/cell/row. If a phase has a long description, the description goes on the slide alongside the phase number — not folded under "Ph 1-3."

There IS a middle ground between aggressive brevity and overwhelming detail, and it's "render what the brief says without compression tricks." Outcome slides naturally end up shorter because their brief entries are shorter; deep-dive slides naturally have more on them because their brief entries do. Calibrate to the brief, not to a target word count.

### Deliverables get their own slide

When the conclusion of the work is a list of concrete deliverables (PRs, tickets, features, action items), give them a dedicated slide rather than a single bullet on "Where we landed."

The dedicated deliverables slide:
- Each item has a number/identifier, a title, and a 1-2 sentence description of what's actually in it
- BLOCKING / shipped / status tags are visible per item
- Layout: prefer a single-column row layout (each item is a full-width row with id on the left and title+description stacked on the right). Multi-column grids are visually fine for short titles but get confusing for ~9+ items with descriptions — readers can't tell whether to read across or down. **One column unless explicitly asked otherwise.**

Why dedicated rather than embedded: a deliverables list with descriptions doesn't fit comfortably alongside narrative bullets without one or the other being squeezed. Two slides ("Where we landed" with the high-level narrative + "Deliverables" with the enumerated list) read better than one cramped two-column slide.

The "Where we landed" slide should reference the deliverables slide ("see next slide for the breakdown") so the audience knows specifics are coming.

The details panel on the deliverables slide is for the *why* and the *how* (why this set, in what sequence, what depends on what). The face is the *what*: the literal list with descriptions.

### Post-Day-1 roadmap also gets its own slide (when applicable)

When the source has follow-on work that's not part of the Day-1 deliverables — items like "after we ship, the next thing we'll do is X, then Y" — surface those in the pre-deep-dive outcome section, NOT only in the deep-dive chronology.

Concretely: if the source markdown has a "Post-migration add-ons" / "Roadmap" / "Phase 2" / "After Day 1" section, render a dedicated **"Post-migration roadmap"** (or similarly titled) slide right after the Deliverables slide. Use the same row-style layout as the Deliverables slide for visual consistency: identifier/priority tag on the left, title + 1-2 sentence description on the right.

Why surface this in the outcome section: non-technical viewers leaving the deck after the "deep dive" divider should still see the full forward-looking story. "Here's what we ship Day 1, here's what comes after, here's the baseline before, here's what we found." If the post-migration items only appear inside the deep-dive steps, anyone who exits at the divider misses the roadmap.

Use a "Next / High / Cond. / Nice-to" style identifier column instead of sequential numbers when the items are priority-ranked rather than sequenced. Mutually exclusive items (e.g. "do A or B per group based on data") get described as alternatives in their description, not as separate priority tiers.

The Day-1 Deliverables slide and the Post-migration Roadmap slide are different artifacts — one is "what's IN the migration PRs," the other is "what comes AFTER." Don't merge them.

## Visual explanations with SVG

When a slide explains architecture, event flow, state transitions, request lifecycles, dependency chains, or concurrency, prefer a tasteful custom inline SVG over more bullets. The goal is to make the logic visually obvious at presentation distance.

Use custom SVGs when they add comprehension:
- Queue/drainer/producer flows, parent-child relationships, retries, cancellation, fan-out/fan-in, or before/after topology usually deserve a diagram.
- Mermaid is acceptable for quick graph sketches, but custom SVG is preferred for nuanced timing, hierarchy, callouts, or polished presentation quality.
- Do not invent diagrams unsupported by the brief/source. The SVG must represent actual mechanics from the provided material.

Design requirements for SVG diagrams:
- Keep the same editorial/typewriter aesthetic: warm paper, near-black labels, calm green for active/success paths, muted tan/gray for control or inactive paths.
- Use direct labels inside shapes; avoid legends unless the diagram genuinely needs one.
- Make sequence and hierarchy clear with lanes, grouped regions, arrows, and whitespace.
- Use generous spacing. Labels must never touch borders, overlap arrows, or overflow their boxes.
- Prefer two-line labels with `<tspan>` over tiny text when labels are long.
- Keep font sizes readable when projected. If labels become too small, simplify the diagram or split it across slides.
- Align rows and columns deliberately. When one row moves, update connected arrows, grouped-region bounds, and downstream rows together.
- Reserve bottom space for terminal/control markers so final rows do not crowd grouped regions.

Verification for SVG diagrams:
- Screenshot every slide containing an SVG and inspect it visually before reporting completion.
- If text overflows, spacing is cramped, or alignment is visibly off, fix it directly. Do not ask the user to judge obvious formatting defects.
- Re-screenshot the affected slide after each SVG layout fix.

## Progressive disclosure (the key UX feature)

Each content slide gets a `▸ Details` toggle. Default state is collapsed (clean presenter view). Expanded state reveals supplementary content as specified in the brief's per-slide "Expanded content" field.

The expansion should feel like a thoughtful editorial sidebar, not a wall of dumped text. The presenter can show flat (slide bullets only); when someone asks "why?" they expand inline.

Mandatory CSS for the slide container — solves the "scroll breaks when details panel opens" failure mode:

```css
.slide {
  position: absolute; inset: 0;
  display: flex; flex-direction: column;
  justify-content: safe center;  /* `safe` falls back to flex-start when content overflows */
  align-items: flex-start;
  padding: clamp(2rem, 6vw, 5rem) clamp(2rem, 8vw, 7rem) clamp(5rem, 10vh, 7rem);
  overflow-y: auto;
  overscroll-behavior: contain;
}
```

Mandatory JS — auto-scroll the details panel into view on open so context isn't lost:

```js
toggle.addEventListener('click', function () {
  var isOpen = panel.classList.contains('open');
  panel.classList.toggle('open', !isOpen);
  toggle.classList.toggle('open', !isOpen);
  if (!isOpen) {
    requestAnimationFrame(function () {
      panel.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    });
  }
});
```

Details panel font sizes: `1rem` for body text, `0.95rem` for ref-list items. Don't go smaller — it stops being readable when projected.

## Deck = happy path; Details panels = "why not the other path"

The deck is a presentation, not a transcript. Slides walk the audience through the **happy path** — what was done, what was landed on, the inflection points that materially shifted the plan. Things that don't drive the story forward belong in expandable details, not as their own slides.

When composing slide content from the brief:
- Failed attempts that didn't ship → the next shipped step's details under a "Why not X?" subsection
- Root-cause traces for failed attempts → live alongside the failed attempt, never split into a separate slide
- Internal cleanups / refactors / removed plumbing → details only, never a slide
- "We considered X, decided not to" → details of the step where the decision was made

The source markdown keeps the full chronology. The deck doesn't.

A useful test before adding a slide: *would a presenter be able to skip this slide entirely and still tell a coherent story?* If yes, it's details material.

## Code blocks: per-slide "See code" + modal + syntax highlighting

When a slide's content rests on a specific bit of code (a diff, a config block, a request body), the slide should expose a **"See code"** affordance — a button that opens a modal containing the relevant code at readable size. Don't dump code inline on the slide unless it's a one-liner; long snippets crowd the slide and are unreadable at presentation size.

The brief's "Code block candidates" section identifies which slides get this treatment.

### Architecture

Use [highlight.js](https://highlightjs.org/) via CDN — manual `<span class="kw">` coloring is brittle:

```html
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.10.0/styles/atom-one-light.min.css" />
<script src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.10.0/highlight.min.js"></script>
<script>
  document.addEventListener('DOMContentLoaded', function () {
    if (window.hljs) {
      document.querySelectorAll('pre code').forEach(function (el) { hljs.highlightElement(el); });
    }
  });
</script>
```

**Modal highlighting**: do NOT install a `MutationObserver` on `#code-modal` to re-highlight on content change. `hljs.highlightElement()` mutates DOM (it wraps tokens in spans), which fires the observer, which re-highlights, which mutates DOM — infinite loop, browser tab freezes. (This bit a real render. Don't repeat it.)

Instead, call `hljs.highlightElement()` explicitly inside each click handler that populates the modal, immediately after `innerHTML` is assigned:

```js
// Inside the .see-code-btn click handler, after `codeModalContent.innerHTML = source.innerHTML;`
if (window.hljs) {
  codeModalContent.querySelectorAll('pre code').forEach(function (el) { hljs.highlightElement(el); });
}
codeModal.classList.add('visible');
```

Same pattern for the `.code-block` click handler. One-shot, no observer, no loop.

Markup pattern: `<pre class="code-block"><code class="language-<lang>">...</code></pre>`. The `.code-block` class triggers the click-to-expand modal; `language-X` tells highlight.js what to colour.

Modal infrastructure (validated CSS + JS):

```css
.code-block { cursor: pointer; position: relative; }
.code-block::after { content: "↗"; position: absolute; top: 0.4rem; right: 0.6rem; opacity: 0.35; pointer-events: none; }
.code-block:hover::after { opacity: 1; }
#code-modal { display: none; position: fixed; inset: 0; background: rgba(20,20,20,0.65); z-index: 200; align-items: center; justify-content: center; }
#code-modal.visible { display: flex; }
#code-modal-inner { background: var(--paper); max-width: 110ch; max-height: 92vh; ... }
#code-modal-content { font-size: 0.95rem; overflow: auto; ... }
```

```js
// Click any .code-block → copy its innerHTML into modal, show modal
// Esc / overlay click / close button → hide
```

Don't put code in a single mega "What it actually looks like in code" details panel under one slide — that breaks per-slide coupling. Each slide that has code gets its own focused affordance.

## Inline source links (preference)

Where a constraint, finding, or decision in *collapsed* slide content is backed by a specific GitHub issue / PR / vendor doc, **inline that link directly into the bullet text**, not just in expanded details. Pattern:

> Bedrock's Opus/Sonnet 4.6 silently disables thinking on continuation turns ([pydantic-ai #5304](https://github.com/pydantic/pydantic-ai/issues/5304)). The newer adaptive shape is required.

The link gives a presenter a jump-off point during Q&A without forcing them to expand details. Don't overdo it — one or two links per slide where they earn their place.

**Always link commit SHAs, PR numbers, and ticket IDs** to their canonical URLs when referenced. Lone SHAs and bare ticket IDs are dead text — make them clickable.

## Navigation

- Keyboard: arrow keys + space. Don't hijack keys when focus is inside an open details panel.
- Visible nav: prev/next buttons + slide counter, fixed bottom-right.
- Outline / TOC button, fixed bottom-left, opens a list of all slides for jumping.
- Touch: swipe left/right.
- Hash routing per slide (see "Mandatory invariants" at top).

## What not to do

- Don't invent content. The HTML is a *designed view of the brief*, not a rewrite. If the brief doesn't say it, don't put it on the slide.
- Don't auto-generate diagrams that aren't supported by the brief. If you draw an SVG, it must represent something explicitly described in the source.
- Don't link to remote assets except highlight.js per the Code Blocks section.
- Don't generate a long-form document HTML alongside the deck.
- Don't introduce slide animations beyond the 0.35s cross-fade.
- Don't cap slide content with "... and much more!" or filler — slides finish with the content they have.

## Sanity-check the brief's sourcing before rendering

If the brief's slide outline is clearly compressed from an investigation (phrases like "we found," "the POC does X," specific file:line references, named tests/gaps) but every slide says `Source: inline` with no `## Source files to read` entries, stop and flag it back to the caller rather than rendering blind. That combination means the underlying research was never persisted anywhere — you'd be rendering a copy of a copy with no way to verify a claim or recover a dropped detail. Ask the caller to point you at the raw notes (or write them) before proceeding. This does not apply to decks that are genuinely original prose (retros, plans the caller is authoring fresh) — only to decks summarizing pre-existing investigation.

## Quality bar — hard-won principles

These recurred across real deck sessions. Each is a specific failure mode with a concrete fix.

### Density is enemy #1

Slides accrete text as concepts, tables, and asides pile on. When a section becomes a wall of text, convert it to a diagram with minimal labels. Lead with one plain sentence, then the visual — never a cold diagram with no setup, never a paragraph that a picture would carry better.

### Real SVGs — no emoji or ASCII

All diagrams must be custom inline SVGs in one consistent visual language: shared CSS color tokens, matching box/line/marker styling and fonts. Emoji (💥 ➡️ 🟢) or ASCII art alongside polished SVGs reads as lazy. Concretely:
- Reuse the deck's defined CSS custom properties in every SVG.
- Give each SVG **unique** `id` values for `<marker>`, `<linearGradient>`, etc. — duplicate `<defs>` ids across slides silently break whichever loads second.

### Phase large diagrams — never one massive one

A single comprehensive swim-lane or flow diagram overwhelms on sight. Split it into sequential mini-diagrams, one per phase: only the participants active in that phase, columns aligned across phases, prose under each. Same information; lands as "clean and stepwise" rather than "a wall."

### Verify every technical claim before it goes on a slide

Dramatic framings are almost always overstated. Concretely check: does the feature behave exactly as described, or only under certain conditions? Overstatement gets caught by technical audiences and erodes trust. State what's true, not what's punchy.

### No strawman / "myth" framing

Don't open with "let's kill a myth…" about a misconception the audience never held — it plants doubt and wastes a beat. State the fact directly.

### Define a term before describing its properties

Don't say "X is addressed by Y" before saying what X *is*. Introduce the concept in one plain line, then its attributes.

### Terminology: deliberate and consistent

Pick each term once and apply it everywhere. Distinguish closely-related concepts (e.g. the logical compute unit vs. the infra object it runs in). Avoid loaded or abstract words that sound clever but confuse — check with the caller if a term feels slippery. Keep implementation jargon out of headline copy; put it in details panels and use plain language on the slide face.

### Surface tunable numbers as headline stat cards

Key configurable values (timeouts, retry intervals, batch sizes) belong as large stat cards with a one-line rationale, so the audience can see the knobs and the reasoning. Don't bury them in prose.

### Use the full width

Don't cap slide content at a narrow line length when horizontal space is available. Diagrams, tables, and stat-row layouts should span wide. Reserve a comfortable reading measure only for long-form prose. Empty side margins on a content-rich slide read as a layout bug.


### Honest "stumbling blocks" / "known gaps" slides build credibility

Naming what went wrong and what's still open reads as rigor, not weakness. Frame as "known + planned" rather than apology. These belong in the appendix, not the main arc.

### Nav JS fragility with positional IDs — solved by the template

The template's navigation is **DOM-derived**: it queries `.slide` elements and their `data-title`, with no positional `TITLES` array, `TOTAL` count, or `slide-N`/`toggle-N`/`panel-N` IDs. Add, remove, or reorder slides freely — the counter, TOC, hash routing, and the details/code wiring adapt automatically, no renumbering. If you find yourself maintaining a positional array or numbering IDs, you've drifted off the template; stop and go back to it.

## Confirm completion

Because the chrome comes from `template.html` and is correct by construction, verification is **scoped to what you actually authored — content and SVGs — not the invariant chrome.** Do not screenshot every slide to re-confirm nav/print/routing; that's the slow, redundant loop the template exists to eliminate. **Do not fabricate results.** If a step fails or is skipped, say so.

### 1. Invariant grep

Run this and paste the raw output into your completion report:

```bash
grep -E '<base target="_blank"|window\.location\.hash|hashchange|media print|export-btn' <path-to-presentation.html>
```

All five patterns must appear. If any is missing, fix and re-run. **Paste the actual grep output — not a summary of it.**

### 2. SVG geometry audit (required if any SVG diagrams are present)

For every `<svg>` in the file, verify in the source HTML before opening in a browser:

- Every `<text>` element's `y` coordinate is at least `font-size + padding` pixels inside the containing `<rect>`'s bottom edge (`rect.y + rect.height`). Text whose `y` sits at or below the bottom edge will overflow or appear clipped.
- The rightmost node's right edge (`x + width`) is at least 10px inside the `viewBox` width — nothing is cut off at the right.
- All nodes on the same row share the same `y` and `height` values.
- Arrow `x1` / `x2` endpoints: `x1` equals the right edge of the source box; `x2` is 2–4px before the left edge of the target box (so the arrowhead sits in the gap, not inside the box).

Fix any violations directly in the HTML before proceeding to browser verification.

### 3. Visual verification with `agent-browser` — SVG + dense/novel-layout slides ONLY

The chrome (nav, routing, print, modals, details toggles) is template-guaranteed — do NOT screenshot every slide to re-confirm it works. Screenshot only:
- **Every slide containing an inline SVG** (geometry can't be trusted from source alone).
- **Any slide with unusually dense content or a novel layout** you hand-built (wide tables, multi-column, tight stat rows) where overflow is plausible.
- **One interaction spot-check, once:** open slide 1, click a details-toggle (verify expand), and if any slide has a `see-code-btn` click it (verify the modal). This confirms the template wiring survived — you don't repeat it per slide.

A text-only bullet slide filled into the template does not need a screenshot; the template's layout handles it.

```bash
DECK="file://<absolute-path>"
# Screenshot ONLY the SVG / dense slides — list their page numbers explicitly:
for i in <svg-and-dense-page-numbers>; do
  agent-browser open "${DECK}#page-${i}"
  agent-browser wait 300
  agent-browser screenshot "/tmp/deck-slide-${i}.png"
done
agent-browser open "${DECK}#page-1"
agent-browser snapshot -i   # click a details-toggle; click a see-code-btn if present
```

**Read each screenshot you take with the Read tool** and describe what you see. For each report:

- `✓ slide N` — looks correct
- `✗ slide N — <specific issue>` — broken; fix it, re-screenshot, re-read

For SVG slides specifically, confirm:
- All text is visibly inside its bounding box (no text touching or crossing box borders)
- The diagram fills the available width — no cramped cluster on one side with empty space on the other
- Labels are legible at the screenshot resolution

Fix every `✗` before reporting done. Re-screenshot the fixed slide to confirm.

**If `agent-browser` is unavailable**, say so explicitly in the report — do not silently skip:
> Visual verification skipped — agent-browser unavailable. User should spot-check before presenting.

Do not report slides as passing if you have not read their screenshots. Fabricating pass results has caused broken decks to ship.

### Report

After all three steps pass, tell the user:

```
Presentation rendered: <path>
Grep: <paste the 5 matching lines>
Visual: <per-slide ✓/✗ list, or "agent-browser unavailable">
```

If this was a re-render over an existing deck, append the backup path and reconciliation summary: slides updated / added / removed, assets preserved, conflicts flagged.
