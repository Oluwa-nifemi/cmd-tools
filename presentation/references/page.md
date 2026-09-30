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
- Keep optional appendix material visible or place it in a clearly labelled
  modal. Do not use `<details>` or generic “more” labels.
- Apply the same metric rule as decks: measurement, baseline, change, and why
  it matters must appear together.
- Pills and badges must stay on one line. Give their table column enough width;
  do not let a short status label wrap into a tall, hard-to-read capsule.
- Keep table cells readable. A cell must not wrap into a narrow column of 3 or
  more lines with under 16 characters per line. Long paths or identifiers:
  - Do not use `word-break: break-all`. It splits words mid-token.
  - Prefer a list or card layout with the path on its own full-width line.
  - In a table, give the path column a `min-width` (about 22rem) and let the
    table scroll horizontally inside a wrapper, or shorten the path and put
    the full path in a `title`.
  - Cap tables at about 4 text columns. Merge "what it is" and "action" if
    needed.
- In explanatory cards, render the label as its own block above the body. Do
  not concatenate labels such as “Method” or “Output” directly with prose.
- Preserve the template's print stylesheet and both download links.
- Do not alter the inline TOC, comments, export controls, or print stylesheet.
