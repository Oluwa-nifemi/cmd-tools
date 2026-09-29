# Deck brief

Start with the fields in [common.md](common.md). Add the deck fields below.
Audience tunes depth: execs get shorter content and few or no code modals; eng
keeps deep-dive detail and code.

## Deck fields

```markdown
## Cover metadata (optional)
<key-value lines for additional cover-slide fields. Examples:>
- Time invested: 5h 17m across 2 sessions
- Date: 2026-05-10
- Author: <name or team>
- Repo: <link>

## Slide outline
<ordered list. Each slide is a `### Slide:` heading with these sub-fields:>
<- Source: where content comes from. Either "inline" or absolute file path(s)>
<- Visible content: all content needed to understand the slide>
<- Modal content: optional dense evidence; "none" or "n/a" if absent>
<- Notes (optional): per-slide rendering hints>

### Slide: <slide title>
Source: <inline | path/to/file.md>
Visible content:
- Bullet 1
- Bullet 2
Modal content:
- More detail point 1
- Source link: [Issue #1234](https://...)
Notes: <optional>

### Slide: <next slide title>
...

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
Visible content:
- Land the new auth flow behind a flag
- Reduce p99 latency on /search to <300ms
- Onboard two new engineers
Modal content: none

### Slide: What went well
Source: inline
Visible content:
- Auth flow shipped on time, zero rollbacks
- New engineers both have first PRs merged
- Pairing on Wednesdays is sticking
Modal content:
- Auth: flag is at 5%, no incidents reported
- New eng onboarding doc was rewritten before they joined — paid off

### Slide: What didn't
Source: inline
Visible content:
- /search p99 still at 480ms
- Two incidents from the deploy pipeline (slow rollouts)
- Sprint planning ran 90 minutes
Modal content:
- /search: identified the N+1 in `searchClusters`, fix in flight
- Pipeline: argo timeout config wrong, will be PR'd next sprint

### Slide: Action items
Source: inline
Visible content:
- Land /search N+1 fix (owner: A)
- Argo timeout config PR (owner: B)
- Cap sprint planning at 60min via timer (owner: C)
Modal content: none

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
Visible content: (cover-slide rendering)
Modal content: none

### Slide: Where we landed
Source: /Users/me/work/myproj/local/litellm-context-management_research/research-notes.md (the "Outcome at a glance → After" section if present, else the Decisions table summary)
Visible content: <distill into 5-7 bullets summarising the wins>
Modal content: <pointer to research-notes.md, key decision links>

### Slide: Before
Source: /Users/me/work/myproj/local/litellm-context-management_research/research-notes.md (the "Outcome at a glance → Before" section)
Visible content: <verbatim from Before section>
Modal content: <none — Before should be stark>

### Slide: What we found
Source: research-notes.md
Visible content: <constraints that ruled out simpler paths>
Modal content: <links to step files where each constraint was discovered>

### Slide: Open questions
Source: research-notes.md "Open questions" section
Visible content: <each open question as a bullet>
Modal content: <context for each>
Notes: omit slide entirely if Open questions section is empty

### Slide: Next steps
Source: research-notes.md "Next steps" section
Visible content: <prioritized list>
Modal content: <none>

### Slide: Section divider — The arc (deep dive)
Source: inline
Visible content: large heading "The arc (deep dive)" with subtext "stop here if you don't need the chronology"
Modal content: none

### Slide: Step 1 — <title from steps/step-1-*.md>
Source: /Users/me/work/myproj/local/litellm-context-management_research/steps/step-1-litellm.md
Visible content: <step Summary section + Decision line>
Modal content: <step body>
Notes: if step contains **Reframe**, apply amber left-border

### Slide: Step 2 — ...
... (one slide per step file)

### Slide: Section divider — Decisions
Source: inline
Visible content: large heading "Decisions"
Modal content: none

### Slide: Decisions
Source: research-notes.md "Decisions and rejected alternatives" table
Visible content: <render the table — split across multiple slides if it doesn't fit on one>
Modal content: <none — the table is the content>
Notes: the "why rejected" column is the focal point; visually emphasize it

### Slide: Files reference / closing
Source: research-notes.md "Quick reference" section
Visible content: <files investigated>
Modal content: <none>

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
Visible content:
- 3 layers: HTTP routing → domain services → persistence
- Entry point: src/main.py
- ~12k lines, 4 bounded contexts (workspaces, components, integrations, auth)
Modal content:
- Tech stack: FastAPI, SQLAlchemy, Pydantic v2
- Test infrastructure: pytest + factories

### Slide: HTTP layer
Source: /Users/me/work/api/src/routes/
Visible content:
- FastAPI routers, one file per bounded context
- Auth middleware: src/middleware/auth.py
- Error handlers: src/middleware/errors.py
Modal content:
- Route registration pattern
- Response model conventions

### Slide: Domain layer — Workspaces
Source: /Users/me/work/api/src/domain/workspaces.py /Users/me/work/api/src/domain/workspace_commands.py
Visible content:
- Aggregate root: Workspace
- Commands: CreateWorkspace, ArchiveWorkspace, AddMember
- Queries: list_workspaces, get_workspace_by_id
Modal content:
- CQRS split is loose; queries live in same file as aggregate
- Authorization checked at command level, not route level

### Slide: Persistence
Source: /Users/me/work/api/src/persistence/
Visible content:
- SQLAlchemy ORM, migrations via Alembic
- Repositories per aggregate
- No raw SQL except in 2 reporting queries
Modal content:
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

## Deck notes for caller authors

- **Slide titles are yours.** Structure the deck however the content demands.
- **Check for an existing deck before composing the brief.** If `presentation.html` already exists at the output path, the render is an update. Read the existing deck and note what it already contains, especially hand-added images, custom slides, or tuned content. Frame the brief as the desired end state of each slide; the renderer reconciles it against the existing deck.

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
