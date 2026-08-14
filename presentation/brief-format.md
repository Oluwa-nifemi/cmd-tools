# Presentation brief format

This is the contract between a calling skill and the `presentation` skill. The caller composes a brief in this shape; the presentation skill renders an HTML deck from it.

## Hard requirement for the dispatched sub-agent

**The agent that renders MUST read the presentation SKILL.md in full before
writing a single line of HTML.** That file contains the mandatory invariants,
the default aesthetic, the progressive-disclosure pattern, code modal
architecture, navigation rules, and the verification grep. Skipping it leads
to broken decks (this has happened — the invariants exist because of past
failures).

## Schema

```markdown
# Presentation brief

## Format
<deck | page — selects which template the renderer starts from (template.html vs page-template.html). If omitted, the rendering skill asks the caller/user rather than assuming.>

## Audience
<execs | eng | mixed | self — tunes depth: execs get shorter content and fewer/no code modals, eng keeps deep-dive detail and code>

## Purpose
<tech talk | decision doc | scoped plan | status — one line on what this artifact is for>

## Output path
<absolute path where the output HTML should be written (presentation.html for deck, or e.g. page.html for page)>

## Title
<title shown on the deck's cover slide, or the page's header>

## Subtitle
<one sentence, shown under title — the "investigation line" or topic statement>

## Cover metadata (optional)
<key-value lines for additional cover-slide fields. Examples:>
- Time invested: 5h 17m across 2 sessions
- Date: 2026-05-10
- Author: <name or team>
- Repo: <link>

## Aesthetic overrides (optional)
<omit this section to use the editorial/typewriter defaults from SKILL.md>
<each line overrides one specific value. Examples:>
- Background: #efe9dd
- Accent color: #2a5a3a
- Special treatment: Slides marked **Reframe** in source get amber left-border (#c8860a)

## Slide outline
<ordered list. Each slide is a `### Slide:` heading with these sub-fields:>
<- Source: where content comes from. Either "inline" or absolute file path(s)>
<- Collapsed content: bullets / short prose for the slide face>
<- Expanded content: what appears in the ▸ Details panel; "none" or "n/a" if no expansion>
<- Notes (optional): per-slide rendering hints>

### Slide: <slide title>
Source: <inline | path/to/file.md>
Collapsed content:
- Bullet 1
- Bullet 2
Expanded content:
- More detail point 1
- Source link: [Issue #1234](https://...)
Notes: <optional>

### Slide: <next slide title>
...

## Source files to read
<absolute paths the rendering sub-agent should read for content. The sub-agent reads these IN ADDITION to following the slide outline. Lets the sub-agent fact-check its slide content against the source.>
- /path/to/source-1.md
- /path/to/source-2.md

## Code block candidates (optional)
<slides where a "See code" modal affordance is warranted, with the code source>
- Slide "<slide title>": /path/to/file.ext lines 42-78
- Slide "<other slide>": inline (provide the code in the slide's expanded content)
```

## Worked example: minimal deck

Sprint retro deck, no source files, content all inline:

```markdown
# Presentation brief

## Output path
/Users/me/Desktop/sprint-42-retro/presentation.html

## Title
Sprint 42 — Retrospective

## Subtitle
What we shipped, what bit us, what we'll change

## Cover metadata
- Date: 2026-05-10
- Team: Platform

## Slide outline

### Slide: Goals
Source: inline
Collapsed content:
- Land the new auth flow behind a flag
- Reduce p99 latency on /search to <300ms
- Onboard two new engineers
Expanded content: none

### Slide: What went well
Source: inline
Collapsed content:
- Auth flow shipped on time, zero rollbacks
- New engineers both have first PRs merged
- Pairing on Wednesdays is sticking
Expanded content:
- Auth: flag is at 5%, no incidents reported
- New eng onboarding doc was rewritten before they joined — paid off

### Slide: What didn't
Source: inline
Collapsed content:
- /search p99 still at 480ms
- Two incidents from the deploy pipeline (slow rollouts)
- Sprint planning ran 90 minutes
Expanded content:
- /search: identified the N+1 in `searchClusters`, fix in flight
- Pipeline: argo timeout config wrong, will be PR'd next sprint

### Slide: Action items
Source: inline
Collapsed content:
- Land /search N+1 fix (owner: A)
- Argo timeout config PR (owner: B)
- Cap sprint planning at 60min via timer (owner: C)
Expanded content: none

## Source files to read
(none — all content inline)
```

That's the minimum a brief looks like. No source files, no code modals, no aesthetic overrides — defaults handle everything.

## Worked example: research deck (with source files)

For a research session output, the caller (research skill) composes a brief that points the sub-agent at the research markdown corpus:

```markdown
# Presentation brief

## Output path
/Users/me/work/myproj/local/litellm-context-management_research/presentation.html

## Title
LiteLLM context_management investigation

## Subtitle
What we found, what we decided, what to do next

## Cover metadata
- Time invested: 5h 17m across 2 sessions
- Date: 2026-05-10

## Aesthetic overrides
- Special treatment: Slides marked with **Reframe** in their source get an amber left-border (#c8860a) — these are inflection points where the plan changed mid-investigation.

## Slide outline

### Slide: Cover
Source: inline (use Title, Subtitle, Cover metadata above)
Collapsed content: (cover-slide rendering)
Expanded content: none

### Slide: Where we landed
Source: /Users/me/work/myproj/local/litellm-context-management_research/research-notes.md (the "Outcome at a glance → After" section if present, else the Decisions table summary)
Collapsed content: <distill into 5-7 bullets summarising the wins>
Expanded content: <pointer to research-notes.md, key decision links>

### Slide: Before
Source: /Users/me/work/myproj/local/litellm-context-management_research/research-notes.md (the "Outcome at a glance → Before" section)
Collapsed content: <verbatim from Before section>
Expanded content: <none — Before should be stark>

### Slide: What we found
Source: research-notes.md
Collapsed content: <constraints that ruled out simpler paths>
Expanded content: <links to step files where each constraint was discovered>

### Slide: Open questions
Source: research-notes.md "Open questions" section
Collapsed content: <each open question as a bullet>
Expanded content: <context for each>
Notes: omit slide entirely if Open questions section is empty

### Slide: Next steps
Source: research-notes.md "Next steps" section
Collapsed content: <prioritized list>
Expanded content: <none>

### Slide: Section divider — The arc (deep dive)
Source: inline
Collapsed content: large heading "The arc (deep dive)" with subtext "stop here if you don't need the chronology"
Expanded content: none

### Slide: Step 1 — <title from steps/step-1-*.md>
Source: /Users/me/work/myproj/local/litellm-context-management_research/steps/step-1-litellm.md
Collapsed content: <step Summary section + Decision line>
Expanded content: <step body>
Notes: if step contains **Reframe**, apply amber left-border

### Slide: Step 2 — ...
... (one slide per step file)

### Slide: Section divider — Decisions
Source: inline
Collapsed content: large heading "Decisions"
Expanded content: none

### Slide: Decisions
Source: research-notes.md "Decisions and rejected alternatives" table
Collapsed content: <render the table — split across multiple slides if it doesn't fit on one>
Expanded content: <none — the table is the content>
Notes: the "why rejected" column is the focal point; visually emphasize it

### Slide: Files reference / closing
Source: research-notes.md "Quick reference" section
Collapsed content: <files investigated>
Expanded content: <none>

## Source files to read
- /Users/me/work/myproj/local/litellm-context-management_research/research-notes.md
- /Users/me/work/myproj/local/litellm-context-management_research/steps/step-1-litellm.md
- /Users/me/work/myproj/local/litellm-context-management_research/steps/step-2-bedrock.md
- /Users/me/work/myproj/local/litellm-context-management_research/steps/step-3-fix.md

## Code block candidates
- Slide "Step 2 — Bedrock rejection": /Users/me/work/myproj/local/litellm-context-management_research/steps/step-2-bedrock.md (the JSON request body)
- Slide "Where we landed": /Users/me/work/myproj/local/litellm-context-management_research/steps/step-3-fix.md (the proxy strip patch)
```

## Worked example: codebase tour

A Python codebase walkthrough. No "Reframe" semantics, no decisions table. Just sections.

```markdown
# Presentation brief

## Output path
/Users/me/work/api/docs/codebase-walkthrough.html

## Title
ardoq-api — codebase walkthrough

## Subtitle
The shape of the system — for new joiners

## Slide outline

### Slide: Overview
Source: inline
Collapsed content:
- 3 layers: HTTP routing → domain services → persistence
- Entry point: src/main.py
- ~12k lines, 4 bounded contexts (workspaces, components, integrations, auth)
Expanded content:
- Tech stack: FastAPI, SQLAlchemy, Pydantic v2
- Test infrastructure: pytest + factories

### Slide: HTTP layer
Source: /Users/me/work/api/src/routes/
Collapsed content:
- FastAPI routers, one file per bounded context
- Auth middleware: src/middleware/auth.py
- Error handlers: src/middleware/errors.py
Expanded content:
- Route registration pattern
- Response model conventions

### Slide: Domain layer — Workspaces
Source: /Users/me/work/api/src/domain/workspaces.py /Users/me/work/api/src/domain/workspace_commands.py
Collapsed content:
- Aggregate root: Workspace
- Commands: CreateWorkspace, ArchiveWorkspace, AddMember
- Queries: list_workspaces, get_workspace_by_id
Expanded content:
- CQRS split is loose; queries live in same file as aggregate
- Authorization checked at command level, not route level

### Slide: Persistence
Source: /Users/me/work/api/src/persistence/
Collapsed content:
- SQLAlchemy ORM, migrations via Alembic
- Repositories per aggregate
- No raw SQL except in 2 reporting queries
Expanded content:
- Connection pooling: SQLAlchemy default + asyncpg
- Migration runbook: docs/migrations.md

## Source files to read
- /Users/me/work/api/src/main.py
- /Users/me/work/api/src/routes/__init__.py
- /Users/me/work/api/src/domain/workspaces.py
- /Users/me/work/api/src/persistence/repositories.py

## Code block candidates
- Slide "HTTP layer": /Users/me/work/api/src/routes/workspaces.py lines 1-40
- Slide "Domain layer — Workspaces": /Users/me/work/api/src/domain/workspaces.py lines 88-120
- Slide "Persistence": /Users/me/work/api/src/persistence/repositories.py lines 50-90
```

## Notes for caller authors

- **Output path is yours.** The presentation skill writes wherever the brief says.
- **Slide titles are yours.** No required slide names; structure your deck however the content demands.
- **Source files are reading material, not authoritative.** The slide outline tells the sub-agent what to render; source files let it fact-check. If a slide's "Collapsed content" is fully written out in the brief, the sub-agent uses that verbatim. If it's a directive ("distill the Wins section into 5 bullets"), the sub-agent reads the source and produces the bullets.
- **Never mark a slide "Source: inline" when the content came from research, sub-agent findings, or codebase exploration you didn't personally author from scratch.** "Inline" means "I am hand-writing this content, there is nothing upstream to check it against" — it is correct for a sprint retro or a brief where the caller *is* the source. It is a lossiness trap when the caller is actually compressing findings from elsewhere: the render agent never sees the raw material, can't fact-check the summary, can't pull back a dropped detail (a file:line ref, a specific test name, a rejected alternative), and the deck becomes a copy of a copy with no way to audit it later.
  - Before composing the brief, **write the raw findings to a plain notes file** (e.g. `<output-dir>/research-notes.md`) — the sub-agent reports, the file/line references, the specifics you're about to compress out. This is a few minutes of transcription, not a research pass; you already have the material.
  - Then in the brief, set each such slide's `Source:` to that notes file's path (plus a pointer to the relevant section), and list it under `## Source files to read`. The render agent reads it and can restore detail the brief's bullets dropped, verify a claim before putting it on a slide, and — if asked to make a slide more specific — has somewhere to go.
  - Rule of thumb: if you could not answer "where did that number/claim come from?" by pointing at a file, the brief is lossy. Fix it before dispatching the render.
- **Aesthetic overrides are additive.** Specify what differs from the default; the default holds for everything else.
- **Brief lives next to the output.** Convention: write the brief at `<output-dir>/presentation-brief.md`. Lets the user re-edit and re-render later.
- **The brief survives rendering.** Don't delete it. Useful for re-renders.
- **Check for an existing deck before composing the brief.** If `presentation.html` already exists at the output path, the render is an *update*, not a fresh build. Read the existing deck first and note in the brief what it already contains — especially hand-added images, custom slides, or tuned content. The renderer's "Re-rendering over an existing deck" protocol (in SKILL.md) will inventory, audit for staleness, and preserve that content, but the caller flagging it makes the reconciliation reliable. The brief can be framed as the desired end-state of each slide; the renderer reconciles it against the existing deck rather than wiping and rebuilding.

## Updating an existing deck (optional section)

When re-rendering over an existing deck, you may add a `## Existing deck` section to the brief telling the renderer what to preserve and what's known-stale:

```markdown
## Existing deck
Path: <same as Output path — confirms a deck already exists there>
Preserve:
- Slide "Architecture": hand-drawn SVG diagram — keep it, do not regenerate
- Slide "Demo": embedded screenshot (<img>) — carry forward
- Custom slide "Appendix: glossary" — not in this brief's outline; keep it
Known stale (update from current sources):
- Slide "Metrics": p99 figures changed; re-pull from source
- Slide "Deliverables": PR #1234 merged since last render; update status
```

This section is optional — the renderer audits and preserves on its own — but it removes ambiguity about which assets are intentional and which content the caller knows is out of date.
