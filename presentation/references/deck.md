# Deck rendering

The initialized output already contains the deck chrome. Fill only the slides
region between the template markers.

- Use `<section class="slide" data-title="Short label">`.
- Make the first slide a cover with `class="cover"`.
- Keep slide titles short and the deck lean.
- Use details panels only for supporting material. The slide must stand on its
  own without opening one.
- Put code in the template’s existing code modal pattern. Do not add a second
  navigation or modal system.
- Do not alter hash routing, the slide counter, the TOC overlay, inline
  comments, or the print stylesheet.

Use a deck only for a live walkthrough. For a document meant to be read, use
page mode.
