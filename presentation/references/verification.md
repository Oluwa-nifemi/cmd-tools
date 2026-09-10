# Verification

Run the deterministic check:

```bash
python3 scripts/presentation_artifact.py verify \
  --format <deck|page|visualization> \
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

## Visualization behaviour

The deterministic check verifies the HTML shell, not the simulation. Also run
JavaScript syntax checks and exercise each scene’s primary action, reset,
previous/next boundaries, and scenario changes while playing. Verify the
visible results against the brief’s rules, including zero/full/failed states
when relevant. Reset and scene changes must cancel stale callbacks. Check
keyboard-only operation, a narrow viewport, and reduced motion; interactions
must remain understandable without animation. Print is a labelled snapshot,
not an interactive export. Use the available browser workflow; report any
unavailable browser verification rather than claiming it passed.

For nested exploration, open a component, drill into its operation/data view,
then use breadcrumb/Back/Close. Confirm the displayed state matches the main
process, focus remains usable, and closing preserves progress and settings.
