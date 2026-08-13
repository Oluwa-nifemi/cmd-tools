# Renderer workflow

The brief already defines the audience, purpose, format, sources, and output
path. Do not reopen those decisions.

Run the initializer before editing:

```bash
python3 scripts/presentation_artifact.py init \
  --format <deck|page> \
  --output <path>
```

If an output exists, the initializer copies it to a timestamped file in
`.presentation-backups/` beside the output. It does not read or merge that
backup. It then creates a fresh artifact from the selected template.

Read these files in this order:

1. [content-quality.md](content-quality.md) — required for every artifact.
2. [deck.md](deck.md) for `format: deck`, or [page.md](page.md) for
   `format: page`.
3. [verification.md](verification.md) after rendering.

Edit only the template's designated content region. Do not rewrite its CSS,
JavaScript, navigation, commenting, or print chrome.
