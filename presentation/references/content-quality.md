# Content quality

Read this file for every artifact.

## Audience and evidence

- Define each acronym and repository-specific term before using it to explain
  another concept.
- State the point first. Then show the evidence, mechanism, or decision.
- Verify technical claims against the sources in the brief. Do not invent
  metrics, causal claims, or implementation details.
- Use one consistent term for each concept.

## Density and structure

- Default to lean. Remove material that does not support the audience's goal.
- Use a separate section or slide for a decision, deliverable, roadmap, or
  important caveat when it would otherwise be buried.
- Preserve important mechanism detail. Replace vague summaries with one
  concrete example or labelled flow before adding more prose.
- Choose structure by relationship:
  - Sequence or transformation: flow with nearby examples.
  - True comparison using common dimensions: table.
  - Independent facts or metrics: cards or stat grid.
  - One concept needing explanation: concise prose plus an example.
- Do not use tables or cards only to reduce text. Split concepts when they
  have different actors or mechanics.
- Explain mechanics. Avoid slogans, strawman comparisons, and “myth” framing.
- Keep the user-facing question or input beside the result it produced.
- Do not replace evidence with vague phrases such as “we optimized the prompt.”
  Show the semantic change and a representative exact excerpt.
- Remove trace IDs and internal references unless the presenter will use them.
- Do not repeat one showcase result across the deck when another example can
  support the point.
- Remove operational diagnostics such as span counts, token counts, trace IDs,
  or internal call counts unless they support a decision. If the audience may
  need them, provide a labelled drill-down link or modal instead of placing raw
  numbers on the slide.

## Plain writing

Write like an engineer's design notes, not a pitch. Before finishing, scan
every title, subtitle, label, and paragraph for these patterns.

- Titles describe the content. Use "API flow", "Preview validation", or
  "Approval and apply". Do not use slogans or contrast taglines such as
  "An adapter, not a second engine", "The engine does the hard part", or
  "One call, no claims".
- Use sentence case for titles. Do not use clever subtitles.
- Name the mechanism, value, or number. Cut sentences that only describe a
  feeling, such as "the code stays simple" or "errors are friendly". If a
  sentence could appear unchanged in another project's docs, cut it.
- Do not use "not X, but Y", "not just X", or "instead of X, Y" framing. State
  what the thing does.
- Do not force items into groups of three. Use the natural count.
- Use literal words. Do not personify code ("the plan knows"), use figurative
  verbs ("rides along"), or write aphorisms and dramatic fragments.
- Use plain words: "use" for "leverage", "is" for "serves as", "has" for
  "boasts". Avoid AI vocabulary such as crucial, pivotal, seamless, robust,
  delve, landscape, showcase, underscore, and testament.
- Avoid abstract metaphor nouns such as substrate, wedge, surface, primitive,
  harness, scaffolding, north star, and flywheel. Use the concrete word.
- Do not use em dashes. Use a period or comma. Use colons only before a list
  or an example.
- Prefer active voice and name the actor. "ardoq-api validates the changes"
  is better than "the changes are validated".
- Write whole sentences. Do not use arrows or dropped articles in prose.
  Arrows are fine inside diagrams and code.
- Remove filler, hedging, adverbs, and generic conclusions.

## Visuals

- Use labelled SVGs for flows, layers, and dependencies when they improve
  understanding. Do not use emoji or ASCII diagrams.
- Split a large diagram into stages rather than shrinking it into unreadable
  text.
- Use full available width for diagrams and comparison tables.
- Every diagram must have a clear reading order and legible labels.
- A diagram must encode the stated relationship correctly. Do not use a Venn
  diagram for subset or remainder data unless containment and set difference
  are visually unambiguous.
- Do not simplify a diagram until it loses actors, state, control flow, or the
  transformation the prose is explaining.

## Honesty

- Surface tunable values, known gaps, and tradeoffs when they matter.
- Do not present planned work as delivered work.
- Match recommendation strength to the evidence. A small or narrow benchmark
  can support a routing hypothesis or next test, but not a universal default.
- The recommendation must not contradict the deck's own decision rule, caveat,
  or comparison evidence.
