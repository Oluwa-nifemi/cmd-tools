# Deck rendering

The initialized output already contains the deck chrome. Fill only the slides
region between the template markers.

- Use `<section class="slide" data-title="Short label">`.
- Make the first slide a cover with `class="cover"`.
- Keep slide titles short and the deck lean.
- Keep all load-bearing content visible. Do not use `<details>`, details panels,
  or generic “more” affordances in deck mode.
- Do not make a slide cryptic to keep it short. If a mechanism needs several
  steps, split it across slides or show one worked example in visible content.
- Keep examples beside the claim or step they explain.
- Use the template’s modal only for optional dense evidence such as exact code,
  prompt excerpts, or output comparisons. Give every trigger a specific label
  such as “Compare outputs” or “View prompt changes.”
- A prominent metric must show what was measured, the baseline, what changed,
  and why it matters. Do not use a large number as decoration.
- Introduce a concept before its demo, limitation, or optimization. Put prose
  before a supporting diagram.
- Use compact comparison rows or tables for related metrics. Use vertical cards
  only when each card contains a complete context, result, and explanation.
- When prompt or code changes are evidence, show representative exact excerpts.
- Custom interactive controls must declare `data-verify-target` with a selector
  for the state they reveal.
- Every SVG text or `foreignObject` label placed inside a shape must declare
  `data-fit-within="#shape-id"`. Give the shape a unique ID. The verifier
  uses this relationship to reject labels that exceed their intended box.
- Prefer HTML/CSS layout over SVG when the visual is primarily text in boxes.
  SVG text does not wrap automatically.
- Do not alter hash routing, the slide counter, the TOC overlay, inline
  comments, or the print stylesheet.

Use a deck only for a live walkthrough. For a document meant to be read, use
page mode.
