# Verification

Run source lint first:

```bash
python3 scripts/presentation_artifact.py lint \
  --format <deck|page|interactive> \
  --output <path>
```

Then run browser verification:

```bash
python3 scripts/presentation_artifact.py verify \
  --format <deck|page|interactive> \
  --output <path>
```

Browser verification uses `agent-browser` at 1440×900 and 1263×863. It writes
individual screenshots, a contact sheet, diagnostics JSON, and interaction
evidence to `<artifact-stem>.verification/`. It fails on measurable rendering
or interaction defects.

A passing `verify` does not mean the page is readable. When you inspect the
screenshots, read the actual text in every table and card. If you cannot read a
cell in one pass, the layout is wrong even when verify passed.

For page mode it also writes annotated section screenshots. Use these for
selector-level feedback. Keep clean exports separate from annotated evidence.

For interactive mode, lint requires at least one chapter, a visible claim in
each chapter, and no `<details>` except `details.deeper`. Verify also:

- screenshots every chapter at both viewports and checks that
  `Stage.state().view` matches the chapter's `data-view`;
- reloads the page, clicks each `[data-stage-control]`, and fails if the stage
  state does not change or a key outside `data-changes` changes;
- checks that Overview keeps claims visible and hides `.full` content;
- checks that the explore button toggles explore mode.
- with drill-down nodes: lint checks one root, known parents, no unreachable
  nodes, a claim per node, and that every `data-open-node` target exists.
  Verify opens every node by URL and checks the stage view, `state().node`,
  the child list, and the breadcrumb. It clicks a stage part and the Map and
  Back to the tour buttons.

The automated checks do not judge whether the writing fits the reader. Run the
self-check in [interactive.md](interactive.md) for that.

Inspect the contact sheet. Then inspect every flagged slide, novel layout, SVG,
and open modal screenshot. The automated checks do not judge whether the story,
diagram, or evidence is useful.

Before reporting completion, confirm:

- The brief’s source claims are represented accurately.
- The conclusion and recommendation are consistent with the evidence and with
  each other.
- No placeholder text remains.
- Every prominent metric includes measurement, baseline, change, and meaning.
- Load-bearing content is visible without interaction.
- Links, labels, and terminology are readable.
- Text fits inside every visual container. Lines do not end against a box edge.
- Pills, badges, and short status labels do not wrap.
- No text block is squeezed into a narrow column. Verify fails on
  `crampedText`: a cell, list item, paragraph, or card with 3+ lines under 16
  characters per line. Fix the layout, do not shorten words to pass.
- Card labels are visually separate from body copy.
- Fixed or sticky chrome does not intersect document content.
- Every diagram's geometry matches the relationship described in the prose.
- For each load-bearing section or slide:
  - The actor and action are clear.
  - A first-time reader can follow the mechanism.
  - Important transformations show input and output.
  - Examples sit beside the claim they explain.
  - Tables compare; they do not hide sequences.
  - Every included detail improves understanding.
- The output path and any created backup path are reported.
- Lint and browser verification are reported separately.
