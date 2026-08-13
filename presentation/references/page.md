# Page rendering

The initialized output already contains page chrome. Fill only the sections
region between the template markers.

- Add one anchor-TOC entry for each top-level section.
- Use `<section class="section" id="...">` with an `<h2 class="section-head">`.
- Keep load-bearing content visible. Do not hide sections behind `<details>`.
- Use `.callout` for context, decisions, and caveats.
- Use `.statgrid`, tables, pills, and SVGs to make dense material scannable.
- Use `<details class="fold">` only for long, optional appendix material.
- Do not alter the inline TOC, comments, export button, or print stylesheet.
