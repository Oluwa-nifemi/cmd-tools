# Verification

Run the deterministic check:

```bash
python3 scripts/presentation_artifact.py verify \
  --format <deck|page> \
  --output <path>
```

For every artifact, inspect the rendered cover and one content-dense
slide/section. Also inspect every slide or section containing an SVG or a
novel dense layout.

Before reporting completion, confirm:

- The brief’s source claims are represented accurately.
- No placeholder text remains.
- Links, labels, and terminology are readable.
- For each load-bearing section or slide:
  - The actor and action are clear.
  - A first-time reader can follow the mechanism.
  - Important transformations show input and output.
  - Examples sit beside the claim they explain.
  - Tables compare; they do not hide sequences.
  - Every included detail improves understanding.
- The output path and any created backup path are reported.
