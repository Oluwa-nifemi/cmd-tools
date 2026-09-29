# Renderer workflow

The brief already defines the audience, purpose, format, sources, and output
path. Do not reopen those decisions.

For a new artifact, run the initializer before editing:

```bash
python3 scripts/presentation_artifact.py init \
  --format <deck|page|interactive> \
  --output <path>
```

If an output exists during a new render, the initializer copies it to a timestamped file in
`.presentation-backups/` beside the output. It does not read or merge that
backup. It then creates a fresh artifact from the selected template.

Read these files in this order:

1. [content-quality.md](content-quality.md) — required for every artifact.
2. [deck.md](deck.md) for `format: deck`, [page.md](page.md) for
   `format: page`, or [interactive.md](interactive.md) for
   `format: interactive`.
3. [verification.md](verification.md) after rendering.

For feedback revisions, do not run the initializer. Read the exact target HTML
immediately before editing and make only the requested changes.

Edit only the template's designated content region. Do not rewrite its CSS,
JavaScript, navigation, commenting, or print chrome.
For interactive, the regions are the stage, chapters, and explore markers.
Do not rewrite the reading shell script.

## Write in small pieces

A long response can stall and lose all its work. Write the artifact in
several edits, not one.

- Keep each edit under about 250 lines.
- Make the first edit within 10 minutes of starting. Read the brief, then
  write. Do not read everything first.
- Run `lint` after every few edits, so errors show up early.
- Keep chat replies short. Do not echo file content back.
