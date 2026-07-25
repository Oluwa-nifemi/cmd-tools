---
name: orchestrate-build
description: Run the strict do → review → test orchestration pipeline for a large multi-unit software build. Use only when the user explicitly asks for an orchestrated build, or when the work is implementation across multiple independently reviewable units. For general orchestration, research, artifacts, or mixed work, use $orchestrate instead.
argument-hint: [path-to-spec-or-short-description]
hooks:
  PreToolUse:
    - matcher: "Read|Edit|Write|NotebookEdit|Bash"
      hooks:
        - type: command
          command: "${CLAUDE_PLUGIN_ROOT}/lead-lockdown.sh"
---

# Orchestrate Build

Use this compatibility entry point only for code builds. Follow the full build workflow in [../orchestrate/references/build.md](../orchestrate/references/build.md), then read [../orchestrate/references/shared-protocol.md](../orchestrate/references/shared-protocol.md) before dispatching. Ask whether the user wants a wrap-up presentation; if so, also follow [../orchestrate/references/presentation-wrapup.md](../orchestrate/references/presentation-wrapup.md).

The scoped hook and [guardrails.md](guardrails.md) remain intentional: they protect the build coordinator from implementing production code or repeatedly loading large reports. Use `$orchestrate` for every other orchestration mode; it does not inherit this build-only lockdown.
