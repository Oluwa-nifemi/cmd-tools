---
name: orchestrate
description: Coordinate substantial multi-agent work without becoming the primary doer. Use when the user asks to "orchestrate this", "go into orchestration mode", "coordinate agents", or wants a complex build, research effort, artifact, or mixed project decomposed, routed, verified, and summarized.
---

# Orchestrate

Act as the coordinator. Establish the outcome, decompose work, assign bounded units to fresh agents, maintain task ownership, select the right validation for each unit, and report the result. Do not take over a unit merely because it is convenient.

## Start

1. Identify the deliverable, success criteria, authority boundaries, and likely mode: `build`, `research`, `artifact`, or `mixed`.
2. Ask one concise clarification only when an unresolved choice would materially change scope, output, external actions, or validation. Otherwise state the assumption and proceed.
3. Read the matching workflow reference in full:
   - Build: [references/build.md](references/build.md)
   - Research: [references/research.md](references/research.md)
   - Artifact: [references/artifact.md](references/artifact.md)
   - Mixed work: read every applicable reference and sequence the modes around their dependencies.
4. Read [references/shared-protocol.md](references/shared-protocol.md) before dispatching agents.

## Mode choice

| Mode | Use it for | Evidence of completion |
|---|---|---|
| Build | Code, configuration, migrations, or other executable changes | Review outcome and relevant tests |
| Research | A decision, diagnosis, comparison, or investigation | Traceable findings, source/coverage audit, open questions |
| Artifact | A document, deck, design, diagram, or other human-facing deliverable | Inspection against audience, requirements, and format |
| Mixed | Work in which one mode unlocks another | Each unit passes the gate appropriate to its mode |

Do not use orchestration for a small, self-contained task that one agent can safely finish in one pass.

## Finish

Report the completed deliverable, verification performed, decisions made under delegated authority, unresolved risks, and the locations of durable artifacts. Do not commit, push, publish, or make external changes unless the user explicitly authorized them.
