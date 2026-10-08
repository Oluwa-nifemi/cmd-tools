# Presentation brief — common fields

The brief is the contract between the caller and the renderer. Every brief has
the fields below. Then add the fields from the file for its format:

- [deck.md](deck.md) for `format: deck`
- [page.md](page.md) for `format: page`
- [interactive.md](interactive.md) for `format: interactive`

## Hard requirement for the renderer

The renderer MUST read `references/renderer-guide.md` before it writes any
HTML. It does not read SKILL.md, which holds caller-only rules (dispatching,
stall watching). The guide points to the invariants and verification steps.
Skipped invariants have broken artifacts before.

## Common schema

~~~markdown
# Presentation brief

## Format
<deck | page | interactive — selects the template. Use interactive only when
the user explicitly asked for it. If omitted, ask; do not assume.>

## Audience
<execs | eng | mixed | self — tunes depth>

## Purpose
<tech talk | decision doc | scoped plan | status | explainer — one line>

## Output path
<absolute path of the output HTML>

## Title
<cover or header title>

## Subtitle
<one sentence under the title>

## Aesthetic overrides (optional)
<omit to use the defaults. Each line overrides one value.>
- Background: #efe9dd
- Accent color: #2a5a3a

## Source files to read
<absolute paths the renderer reads to fact-check and fill in detail>
- /path/to/source-1.md

<format-specific fields go here — see the format file>
~~~

## Notes for caller authors

- **Output path is yours.** The renderer writes wherever the brief says.
- **Structure is yours.** No required slide, section, or chapter names.
- **Preserve mechanism detail, not conversation length.** If the source
  discussion resolved how an important mechanism works, carry that into the
  brief. Do not copy the full discussion.
- **Use concrete examples for transformations.** When data or state changes
  form, include the input, output, or short sequence. Keep the example beside
  the claim it explains.
- **Split different flows.** Concepts with different actors or mechanics get
  separate slides, sections, or chapters.
- **Source files are reading material, not authority.** Fully written content
  in the brief is used verbatim. A directive ("distill X into 5 bullets") makes
  the renderer read the source and produce the content.
- **Never mark content "Source: inline" when it came from research, sub-agent
  findings, or codebase exploration.** "Inline" means you wrote it from scratch
  and nothing upstream exists. Otherwise the renderer cannot fact-check or
  restore dropped detail.
  - Before the brief, write the raw findings to a notes file, for example
    `<output-dir>/research-notes.md`.
  - Point each affected item's `Source:` at that file and list it under
    `## Source files to read`.
  - Rule of thumb: if you cannot answer "where did that claim come from?" by
    pointing at a file, the brief is lossy.
- **Aesthetic overrides are additive.** The defaults hold for everything else.
- **The brief lives next to the output** as `<output-dir>/presentation-brief.md`.
  Do not delete it after rendering. It is needed for re-renders.
- **Check for an existing artifact first.** If the output already exists, the
  render is an update. Read it and note hand-added content in the brief.
