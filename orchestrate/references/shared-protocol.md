# Shared orchestration protocol

## Keep the lead bounded

Ensure `local/` exists; create it when absent. Before dispatching work, create `local/<task>/orchestrator-log.md`. This is the durable compact index for every orchestration run, not only runs that request a presentation. Keep a status table (`unit | owner | mode | dependency | state | validation | report`) plus concise steering decisions, incidents, and user flags. Append or update only the relevant entry; do not turn it into a transcript.

Keep detailed reports, source notes, and diagnostics in per-unit files under `local/<task>/` when the repository provides `local/`; otherwise use the project's established scratch location. Read detail only to make a decision that cannot be delegated; otherwise route the file to the agent that needs it.

The coordinator's context window is the scarcest resource in the orchestration. Every line of diagnostic output, every `cat` of a source file, every test run consumed in the coordinator's turn is context that could have been spent on coordination. When tempted to "just quickly check" something, dispatch a sub-agent to check it and report back. The only exception is a single read-only verification command when a doer's report is implausible.

## Dispatch rules

- Give every agent a precise, bounded unit, the expected deliverable, acceptance criteria, relevant paths, and a named report file.
- Give every dispatched agent a stable, descriptive prose name that explains its mandate, such as **OAuth Contract Auditor**, **Migration Risk Reviewer**, or **Competitive Landscape Researcher**; do not use generic role-only names. Use the prose name in the orchestration log and coordinator messages. On v2, encode it as the required lowercase `task_name` only at dispatch (`oauth_contract_auditor`, for example) and record the returned canonical path. On v1, record the returned `agent_id` and optional nickname; keep the prose name in the log because v1 nicknames are not durable readable task titles in the Desktop UI.
- Identify the active multi-agent surface from the collaboration tools available in the current task, not from config files: config changes do not rewrite an already-open task. `send_input`, `resume_agent`, and `close_agent` indicate v1; `send_message`, `followup_task`, `interrupt_agent`, and `list_agents` indicate v2. If neither set is available, treat delegation as unavailable. On v2, use task names/paths and its separate message, follow-up, interrupt, and list operations. On v1, use `agent_id` for follow-up and waiting; `send_input` handles both messages and steering (`interrupt=true` redirects a running agent). Do not depend on `list_agents`, canonical paths, or v2-specific control tools when running on v1.
- Use a fresh agent for an independent judgment. Reuse the original agent for amendments to its own work.
- Do not allow nested delegation unless the user explicitly asks for it. For requested v1 nesting, verify `[agents].max_depth` first: `2` permits root → child → grandchild. Keep the default shallow unless the extra delegation has a clear payoff.
- Do not give doers ownership of the coordinator's task list. One agent owns a unit at a time; never overlap writers on the same files.
- If ownership or concurrency is violated, record one incident and verify the affected files once before resuming.
- **Model and reasoning-effort selection are mandatory and explicit, not a default.** Every dispatch call (`spawn_agent` or its v2 equivalent) MUST pass an explicit `model` AND an explicit `reasoning_effort`. Omitting either does not mean "cheapest/lightest available" — it means the sub-agent inherits the coordinator's current model and effort, silently defeating tiering. Before every dispatch, state the unit type and the chosen model tier and effort level in the same message or log entry, then set both arguments to match:
  - **Luna** — mechanically specified work: fixed-format extraction, inventory, lint/syntax checks, status reads against an unambiguous spec.
  - **Terra** — routine work and review: scoped build units with a written task-note/spec, documentation, search-and-summarize, standard code review.
  - **Sol or Opus** — reserved for genuine high-consequence judgment only: adversarial/security review, ambiguous requirements needing synthesis, irreversible or cross-system decisions. Do not use Sol/Opus by default or "to be safe" — that is the failure this rule exists to prevent.
  - If a task genuinely spans tiers (e.g., a review unit doing both mechanical checks and one high-stakes judgment call), pick the tier for the riskiest part it must get right, not the average.
  - **Reasoning effort follows the unit's nature, not its model tier** — pick it independently:
    - **low** — the default for most coding/build units: implementing a specified change, writing tests, mechanical migrations, routine fixes against a clear spec. Most doer work belongs here.
    - **medium** — the default for most review units: independent read/reasoning review, falsifying claims against a spec, standard research synthesis. Most reviewer work belongs here.
    - **high** — reserved for genuinely complex review only: adversarial security review, tracing subtle cross-system control flow, reconciling contradictory sources, a judgment call with real blast radius if wrong. Do not reach for `high` by default — justify it in the dispatch message when used.
    - **Never use anything above `high`** (no `xhigh`/`max`/`ultra`) for a delegated unit, regardless of model tier or perceived task difficulty.
  - Before ending the coordinator's dispatch step, audit every `spawn_agent` call just issued and confirm each one carries both an explicit, tier-justified `model` and an explicit, justified `reasoning_effort`. Treat a dispatch missing either as a protocol violation to fix immediately, not a stylistic omission.
- Require a short message containing verdict, one-line validation result, and report path. Keep the detail in the report.

## Authority and safety

Before dispatching work that can alter shared state, record whether agents may edit files, commit, contact external systems, publish, or only investigate. Treat unspecified authority as read-only. Keep a working path until its replacement has passed the applicable validation.

## Validation

Choose a gate that can falsify the unit's main risk. Do not impose code tests on prose or shallow proofreading on security-sensitive code:

| Unit type | Default gate |
|---|---|
| Code | Independent read/reasoning review plus relevant tests run by the doer |
| Research | Fresh synthesis/audit for source quality, claim support, coverage, and uncertainty |
| Artifact | Creator self-check plus coordinator inspection against the brief; use format-specific rendering or preview when it matters |

When a gate finds material issues, route the report to the original doer, request a focused fix, and repeat the affected gate.
