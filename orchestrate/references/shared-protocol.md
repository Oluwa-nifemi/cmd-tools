# Shared orchestration protocol

## Keep the lead bounded

Maintain a compact task index and pointers, not a growing transcript. Put detailed reports, source notes, and diagnostics in per-unit files. Read detail only to make a decision that cannot be delegated; otherwise route the file to the agent that needs it.

Keep durable work under `local/<task>/` when the repository provides `local/`; otherwise use the project's established scratch location. The index records `unit | owner | mode | dependency | state | validation | report`.

## Dispatch rules

- Give every agent a precise, bounded unit, the expected deliverable, acceptance criteria, relevant paths, and a named report file.
- Use a fresh agent for an independent judgment. Reuse the original agent for amendments to its own work.
- Do not allow nested delegation unless the user explicitly asks for it.
- Do not give doers ownership of the coordinator's task list. One agent owns a unit at a time; never overlap writers on the same files.
- Use the cheapest adequate model: Haiku for mechanically specified work, Sonnet for routine work and review, Opus only for a genuine high-consequence judgment.
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
