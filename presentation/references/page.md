# Page rendering

The initialized output already contains page chrome. Fill only the sections
region between the template markers.

- Add one anchor-TOC entry for each top-level section.
- Use `<section class="section" id="...">` with an `<h2 class="section-head">`.
- Keep load-bearing content visible. Do not hide sections behind `<details>`.

## Story structure

A page is a quick refresher. An engineer should read it in about 3 minutes,
weeks later.

- Start with a one-sentence answer, then one hero SVG of the whole system or
  result.
- Follow with 4 to 6 numbered steps. Each step has a heading, one diagram,
  example or small table, a "How it works" paragraph, and 3 to 5 short key-fact
  bullets.
- Keep "How it works" to 2 or 3 sentences, about 60 words. Explain the
  mechanism or reason; do not describe the diagram again.
- Give every step a visual. Do not write text-only sections.
- Use one colour per actor or category, and keep it the same in every figure.
- Do not use stat grids or large display numbers. State the key number in a
  sentence, in bold if needed.
- Keep prose to about 500 words, bullets included.
- End with a compact Reference strip. It holds only links, paths and commands
  that the steps do not show.

## Element rules

- Use `.callout` for context, decisions, and caveats.
- Use tables, pills, and SVGs to make dense material scannable.
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
- In explanatory cards, render the label as its own block above the body. Do
  not concatenate labels such as “Method” or “Output” directly with prose.
- Preserve the template's print stylesheet and both download links.
- Do not alter the inline TOC, comments, export controls, or print stylesheet.
