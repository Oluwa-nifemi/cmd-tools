# Interactive principles

These rules turn investigation findings into one interactive drill-down
explorer, rendered by `$presentation` in interactive format.

## What the reader gets

- **A guided tour** (story chapters): what the system is for, the main pieces,
  how one real request or job flows through them, and the key design choices.
  The stage shows the system map and highlights the part each chapter covers.
- **A map to explore** (drill-down nodes): click any part of the map to open
  it. Each node explains its part and lists what is inside it. The reader goes
  as deep as they want: system → component → module → file → function, with
  real code excerpts at the bottom levels.

## Audience

The deck audience rules in [deck-principles.md](deck-principles.md) apply:
assume a first-time reader. Define every term, acronym, library, and
algorithm in plain words before using it. Write the brief's reader profile
from what the user has said about themselves.

## Investigation additions

On top of [investigation.md](investigation.md), each investigator also
returns:

- **Node list** for its area: every module, important file, and important
  function, each with a one-sentence claim and a file:line reference.
- **Interfaces**: what this area calls and what calls it, and what data passes
  between them. These become the edges on the map.
- **Libraries**: each third-party library the area uses, what it does in plain
  words, and why this code uses it.
- **One worked example**: a concrete input and output through the area.

Add one extra investigator for the dependency and library audit when the repo
has many libraries. Use `pyproject.toml`, `package.json`, lock files, and
imports as the source.

## Composing the brief

Use `briefs/common.md` and `briefs/interactive.md` from `$presentation`.

- **Stage**: the system map. Components are boxes, interfaces are labelled
  arrows, external services and libraries sit at the edge. Views: one per
  component plus a whole-system view. Every box is clickable.
- **Chapters**: 5–10 for the guided tour. Follow one real flow end to end.
- **Node tree**: root = the system. Children = components from the
  investigation areas. Then modules, files, and functions. Add a "Libraries"
  branch with one node per important library.
- Every node's `Source:` points at a step file section with file:line refs.
- Code excerpts are short (under ~25 lines) and come from the actual file.

## Size

A medium repo gives about 40–120 nodes. Stop at function level for important
functions only. List the rest in the file node's text.

Above about 80 nodes, tell the user the node count and the expected build
time before dispatching the renderers. The writer takes about 1 minute per
node. Offer to stop at file level.

## Quality

After the render, check the explorer as the reader in the profile:

- Can the reader reach every component and library from the map?
- Does every node say what it does in plain words before showing code?
- Does every interface arrow say what passes along it?
- Does every claim trace back to a file:line reference in the step files?

Fix gaps by resuming the writer. Report the node count, chapters, verify
result, and any areas left shallow.
