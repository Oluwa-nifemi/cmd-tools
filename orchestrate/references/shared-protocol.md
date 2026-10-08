# Shared orchestration protocol

## Keep the lead bounded

Ensure `local/` exists; create it when absent. Before dispatching work, create `local/<task>/orchestrator-log.md`. This is the durable compact index for every orchestration run. Keep a status table (`unit | owner | mode | dependency | state | validation | report`) plus concise steering decisions, incidents, and user flags. Append or update only the relevant entry; do not turn it into a transcript.

Keep detailed reports, source notes, and diagnostics in per-unit files under `local/<task>/` when the repository provides `local/`; otherwise use the project's established scratch location. Read detail only to make a decision that cannot be delegated; otherwise route the file to the agent that needs it.

## Opaque report handoffs

The coordinator reads only report metadata by default. It routes detailed reports by path without reading, summarizing, or reproducing their bodies. Read the body only when the user explicitly asks.

Every doer and reviewer report starts with a small YAML frontmatter header:

```yaml
---
status: revision_required
summary: Two correctness issues remain.
validation: review_complete
---
```

Keep `summary` to one sentence. The report path comes from the agent's final message, so do not add a redundant path or recipient field to the header. The status determines the next action:

- `ready_for_review` sends the report path to the reviewer.
- `revision_required` sends the report path to the original doer.
- `clean` accepts the review gate.
- `blocked` or `escalation_required` reports the header to the user.

An agent's final message contains only the report path. The coordinator reads the frontmatter, updates the orchestration log, and routes the path.

## Monitoring long-running units

Do not use an interrupt, cancellation, or redirect solely to request progress. Treat a running build, deployment, migration, browser flow, or E2E scenario as healthy until it reports a failure, completes, or has exceeded a concrete time bound set before dispatch. Prefer a long `wait_agent` timeout and completion notifications.

Interrupt a unit only when one of these conditions applies:

- The user changes or cancels the assignment.
- Continuing creates a concrete safety, cost, or data-integrity risk.
- A known command is stuck beyond its declared bound, with no expected progress.
- The agent asks for input that requires immediate redirection.

If a long-running unit needs observability, require milestone reports in its initial brief. Do not demand ad-hoc checkpoints while a command is running.

## Dispatch rules

- Give every agent a precise, bounded unit, the expected deliverable, acceptance criteria, relevant paths, and a named report file.
- Give every dispatched agent a stable, descriptive prose name that explains its mandate, such as **OAuth Contract Auditor**, **Migration Risk Reviewer**, or **Competitive Landscape Researcher**; do not use generic role-only names. Use the prose name in the orchestration log and coordinator messages. On v2, encode it as the required lowercase `task_name` only at dispatch (`oauth_contract_auditor`, for example) and record the returned canonical path. On v1, record the returned `agent_id` and optional nickname; keep the prose name in the log because v1 nicknames are not durable readable task titles in the Desktop UI.
- Identify the active multi-agent surface from the collaboration tools available in the current task, not from config files: config changes do not rewrite an already-open task. `send_input`, `resume_agent`, and `close_agent` indicate v1; `send_message`, `followup_task`, `interrupt_agent`, and `list_agents` indicate v2. If neither set is available, treat delegation as unavailable. On v2, use task names/paths and its separate message, follow-up, interrupt, and list operations. On v1, use `agent_id` for follow-up and waiting; `send_input` handles both messages and steering (`interrupt=true` redirects a running agent). Do not depend on `list_agents`, canonical paths, or v2-specific control tools when running on v1.
- Use a fresh agent for an independent judgment. Reuse the original agent for amendments to its own work.
- Do not allow nested delegation unless the user explicitly asks for it. For requested v1 nesting, verify `[agents].max_depth` first: `2` permits root → child → grandchild. Keep the default shallow unless the extra delegation has a clear payoff.
- Do not give doers ownership of the coordinator's task list. One agent owns a unit at a time; never overlap writers on the same files.
- If ownership or concurrency is violated, record one incident and verify the affected files once before resuming.
- Choose model and effort from [model-tiers.md](model-tiers.md). Pass both explicitly on every dispatch.
- Require the standard report frontmatter. The agent's final message contains only the report path.

## Authority and safety

Before dispatching work that can alter shared state, record whether agents may edit files, commit, contact external systems, publish, or only investigate. Treat unspecified authority as read-only. Keep a working path until its replacement has passed the applicable validation.

## Validation

Choose a gate that can falsify the unit's main risk. Do not impose code tests on prose or shallow proofreading on security-sensitive code:

| Unit type | Default gate |
|---|---|
| Code | Independent read/reasoning review plus repository-appropriate validation performed by the doer |
| Research | Fresh synthesis/audit for source quality, claim support, coverage, and uncertainty |
| Artifact | Creator self-check plus coordinator inspection against the brief; use format-specific rendering or preview when it matters |

When a report header says `revision_required`, send the report path to the original doer without reading or reproducing the detailed findings. Request a focused fix and repeat the affected gate.
