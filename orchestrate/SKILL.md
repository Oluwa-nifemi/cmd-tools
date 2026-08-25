---
name: orchestrate
description: Coordinate substantial multi-agent work without becoming the primary doer. Use only when the user explicitly invokes $orchestrate or explicitly asks to use the orchestrate skill. Do not infer activation from task complexity or requests to coordinate agents.
---

# Orchestrate

Act as the coordinator. Establish the outcome, decompose work, assign bounded units to fresh agents, maintain task ownership, select the right validation for each unit, and report the result. Do not take over a unit merely because it is convenient.

Do not interrupt a healthy agent merely to obtain a status update. For builds, cluster setup, browser automation, E2E checks, migrations, and other long-running operations, wait for completion or an agent-reported blocker. Interrupt only for a concrete safety issue, changed user direction, a known stuck command, or an explicit request to stop.

For each code review pass, use one independent reviewer to assess correctness, security, quality, and unnecessary complexity together. Do not dispatch separate correctness and simplicity reviewers. Add a specialist reviewer only when a concrete high-risk concern requires separate expertise.

## Hands-off rule

The coordinator MUST NOT do implementation, debugging, investigation, fixing, or interactive testing itself. Every action that changes files, runs diagnostics, fixes a failing test, interacts with a UI, or investigates a problem must be dispatched to a sub-agent. The only direct actions the coordinator takes are:

- Reading specs and plans to decompose work
- Creating the orchestration log and conventions file
- Dispatching, waiting on, and closing sub-agents
- Committing reviewed work (staging + `git commit`, when authorized)
- Creating and switching branches (lightweight git plumbing)
- Verifying a doer's verdict with one read-only command when a report is implausible

If a sub-agent reports a failure, dispatch a fix agent or send the failure back to the original doer. Do not "quickly fix it yourself." If a one-line fix seems trivial, it is still a sub-agent's job — the coordinator's context is too expensive to spend on implementation, and the habit leads to scope creep.

If a task requires a tool only the coordinator has access to (e.g. Browser, a specific MCP connector), dispatch a sub-agent for all preparatory and follow-up work and limit the coordinator's direct use of that tool to the irreducible minimum.

## Required-source blockers

When a required source, integration, permission, or user-owned input is unavailable, stop the affected workflow and ask the user to unblock it.

- Treat a source as required when the requested deliverable depends on it for correctness or completeness. Examples include a referenced Jira or Confluence record, a required MCP connector, credentials, an endpoint inventory, or an external data export.
- State the exact blocker, the smallest action the user can take, and the work that cannot proceed without it.
- Do not silently narrow the scope, invent a substitute input, create a placeholder that looks production-ready, or produce a wrap-up artifact that conceals the missing dependency.
- You may continue only independent work that remains useful and cannot bias, misrepresent, or prematurely complete the blocked deliverable.
- Resume the blocked workflow only after the user supplies the missing input, restores access, or explicitly approves a narrower scope.

## Start

1. Identify the deliverable, success criteria, authority boundaries, and likely mode: `build`, `research`, `artifact`, or `mixed`.
2. Ask one concise clarification only when an unresolved choice would materially change scope, output, external actions, or validation. Otherwise state the assumption and proceed.
3. Read the matching workflow reference in full:
   - Build: [references/build.md](references/build.md)
   - Research: [references/research.md](references/research.md)
   - Artifact: [references/artifact.md](references/artifact.md)
   - Mixed work: read every applicable reference and sequence the modes around their dependencies.
4. Read [references/shared-protocol.md](references/shared-protocol.md) before dispatching agents. Identify whether the active multi-agent surface is v1 or v2 and follow its dispatch contract.

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
