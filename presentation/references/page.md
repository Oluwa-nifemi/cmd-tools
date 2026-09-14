# Page rendering

The initialized output already contains page chrome. Fill only the sections
region between the template markers.

- Add one anchor-TOC entry for each top-level section.
- Use `<section class="section" id="...">` with an `<h2 class="section-head">`.
- Keep load-bearing content visible. Do not hide sections behind `<details>`.
- Use `.callout` for context, decisions, and caveats.
- Use `.statgrid`, tables, pills, and SVGs to make dense material scannable.
- Split sections when concepts have different actors or flows.
- Put input and output examples beside the transformation they explain.
- Use tables only for real comparisons with shared dimensions.
- Use cards only for independent items, not sequential instructions.
- Prefer a short text or labelled flow for a simple procedure.
- Use `<details class="fold">` only for long, optional appendix material.
- PDF export uses A4 landscape orientation and starts each top-level section
  on a new page. Oversized sections may continue naturally rather than clip.
- The export helper also creates a full-height PNG of the screen layout.
- Preserve the template's print stylesheet and both download links.
- Do not alter the inline TOC, comments, export controls, or print stylesheet.
