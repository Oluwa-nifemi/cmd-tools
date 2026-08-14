# Investigation protocol

This protocol governs how source code is read and analyzed before any presentation is created.

## Decomposition

Before dispatching investigators, scan the target to identify natural subsystems. Use file structure, module boundaries, and import graphs as guides.

Heuristics for splitting:

- Separate data-pipeline stages from retrieval/query paths
- Separate model/ML integration from business logic
- Separate infrastructure (DB, Docker, config) from application code
- Separate external integrations (plugins, extensions, APIs) from core
- Separate UI/frontend from backend
- If a subsystem has its own spec file or dedicated test file, it's probably a natural unit

Target: 3–7 investigation areas for a medium repo. Fewer for a small folder, more for a large monorepo. Each area should be investigable by one agent reading 5–15 files.

## Investigator dispatch

Use `$orchestrate` in research mode. For each area, dispatch one investigator agent with:

- A bounded mandate: what subsystem to investigate
- An explicit file list: every source file to read, in order
- A structured output template: the step file format below
- A rule: "read every file in full, do not skim, report what the code actually does"

Model and effort selection:
- Investigators: Sonnet/Terra at medium reasoning (routine read-and-summarize)
- Focused deep-dives on complex algorithms: Sonnet at high reasoning
- Dispatch all independent investigators in parallel

## Step file format

Each investigator writes to `research/steps/step-N-<slug>.md`:

```markdown
# Step N — <area name> (<date>)

*(Companion to: ../research-notes.md)*

## Summary
<2-3 paragraphs: what this subsystem does, key design decisions, main insight>

## <Section per major component>
<How it works. What the key functions do. Data flow.>

## Key configuration
<Table of config values with defaults and what they control>

## Design decisions worth noting
<Non-obvious choices and why they were made>

## Code refs
<file:line references for key functions>
```

## Quality gate

Before moving to presentation, verify each step file:
- Contains actual code references (file:line), not vague descriptions
- Explains mechanisms, not just names ("it uses UMAP" → "it reduces 1024-dim embeddings to 15 dims using UMAP, which preserves local neighbor structure")
- Defines terms before using them
- Has a Summary section that a newcomer could read standalone

## PR-specific investigation

When the target is a PR:

1. Fetch the diff with `gh pr diff <number>`
2. Read every changed file in full (not just the diff hunks)
3. Read surrounding files that the changes interact with
4. Structure the step file around: what changed → why → how → what it affects
5. One step file for the whole PR unless it touches 4+ independent subsystems
