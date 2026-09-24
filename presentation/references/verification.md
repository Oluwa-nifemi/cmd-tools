# Verification

Run source lint first:

```bash
python3 scripts/presentation_artifact.py lint \
  --format <deck|page> \
  --output <path>
```

Then run browser verification:

```bash
python3 scripts/presentation_artifact.py verify \
  --format <deck|page> \
  --output <path>
```

Browser verification uses `agent-browser` at 1440×900 and 1263×863. It writes
individual screenshots, a contact sheet, diagnostics JSON, and interaction
evidence to `<artifact-stem>.verification/`. It fails on measurable rendering
or interaction defects.

For page mode it also writes annotated section screenshots. Use these for
selector-level feedback. Keep clean exports separate from annotated evidence.

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
