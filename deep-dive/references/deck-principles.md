# Deck principles

These principles govern how investigation findings become presentation decks. They come from real sessions where decks were iterated based on user feedback.

## Format: always decks, not pages

Use `$presentation` in **deck** format (slide-based, hash-routed, with `template.html`). Decks with progressive disclosure (▸ Details panels) let the reader control their depth: clean slides for the overview, expandable panels for the "why" and "how."

Pages are for reference documents. Deep dives are for understanding — the slide-by-slide pacing helps.

## Audience: first-time reader

Always assume the reader has **never seen this codebase before**. This is the single most important principle.

Concretely:

- Define every term before using it — on the same slide or an earlier one
- Define it in plain language, not by restating the code symbol
- A definition hidden in ▸ Details does not count if the term appears on the slide face
- Expand every acronym on first use
- Do not assume knowledge of specific algorithms (union-find, UMAP, HDBSCAN, etc.) — explain from scratch or link to a dedicated deep-dive deck
- Do not assume knowledge of specific libraries or frameworks — say what they do

Bad: "Uses UMAP for dimensionality reduction before HDBSCAN clustering"
Good: "Reduces 1024-dimensional embeddings down to 15 dimensions using UMAP (a technique that preserves which points are neighbors of which), then finds natural clusters using HDBSCAN (a density-based algorithm that discovers groups without being told how many to expect)"

## Structure per deck

Each deck follows this arc:

1. **Cover** — title, subtitle, part N of M, date
2. **Overview slide** — what this subsystem does end-to-end, ideally with an SVG flow diagram
3. **Component slides** — one per major component/stage, with:
   - Slide face: the "what" — what it does, key facts, stat cards for important numbers
   - ▸ Details panel: the "why" and "how" — design decisions, algorithm details, edge cases
4. **Configuration slide** — stat cards for key config knobs
5. Optional: section dividers for major transitions

Target: 8–15 slides for a comprehensive deck. 3–6 for lean.

## Slide content principles

### Lead with the point, not the setup

Each slide should open with one sentence stating the takeaway. Supporting detail follows.

### Use visual primitives over prose

Before writing a third paragraph, ask whether it should be:
- A **stat card** — for key numbers, thresholds, tunable knobs
- A **table** — for mappings, comparisons, type enumerations
- An **SVG diagram** — for flows, architecture, algorithms, before/after
- A **note-box** — for design decisions, caveats, "why this approach"

### SVG diagrams for flows and algorithms

Use inline SVGs when a slide explains architecture, data flow, state transitions, or an algorithm. Use the deck's CSS tokens (`--paper`, `--ink`, `--accent`, `--warn`, `--rule`). Keep text readable, inside boxes, with generous spacing.

Give each SVG unique `id` values for markers/gradients to avoid cross-slide conflicts.

### Progressive disclosure is the key UX

The slide face should be scannable in 10 seconds. Everything else goes in ▸ Details. This includes:
- Algorithm step-by-step walkthroughs
- Code references
- Edge cases and error handling
- Rejected alternatives
- Full config tables (show stat cards for the important ones on the face)

### Note-boxes for user questions

When a user asks a question about a slide, the answer gets baked into the deck as a `note-box` div (styled by the template). This way future readers get the clarification without asking. Note-boxes have three variants:
- Default (neutral border) — general clarification
- `.decision` (green accent border) — design decisions, "why this approach"
- `.warn` (amber border) — caveats, gotchas, model-specific behavior

## Deck dispatch

Use `$presentation` to render each deck. Dispatch rules:

- Sonnet/Terra at low reasoning — rendering is execution against a brief, not synthesis
- Each renderer reads: the frontend-design skill, the presentation SKILL.md, the deck template, and its source step file
- Verify: `grep -c PLACEHOLDER` = 0, all 5 invariant patterns present
- All renderers can run in parallel since they write to different files

## Naming convention

```
local/<target-slug>-deep-dive/
├── 1-<area-slug>-deck.html
├── 2-<area-slug>-deck.html
├── ...
├── N-<bonus-topic>-deck.html     (bonus deep-dives on flagged topics)
├── research/
│   ├── research-notes.md
│   └── steps/
│       ├── step-1-<slug>.md
│       └── ...
└── orchestrator-log.md
```

## Bonus deep-dive decks

When the user flags a concept they don't understand:

1. Dispatch a dedicated researcher at **high** reasoning effort to read the relevant source code line by line
2. The researcher must explain from first principles with concrete worked examples
3. Render a bonus deck with liberal use of SVG diagrams — one per algorithm step
4. These decks are numbered after the main set (e.g., deck 6 after 5 main decks)

## Updating existing decks

When the user gives feedback on a slide:

1. Read the existing deck file
2. Find the specific slide
3. Add a `note-box` div with the clarification — do not rewrite the slide
4. Do not touch CSS, JS, or unrelated slides
5. Verify PLACEHOLDERs are still 0 after the edit
