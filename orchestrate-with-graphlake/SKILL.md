---
name: orchestrate-with-graphlake
description: Coordinate substantial multi-agent work through the current $orchestrate workflow, while GraphLake is the durable orchestration record. Use only when the user explicitly asks to orchestrate with GraphLake, use GraphLake for orchestration, or invokes $orchestrate-with-graphlake.
argument-hint: [task, Jira issue, or spec]
---

# Orchestrate With GraphLake

Use the current **`$orchestrate`** skill as the base workflow. Read its
`SKILL.md` and the mode-specific references it requires before dispatching any
agent. Its hands-off rule, required-source blockers, delegation protocol,
validation gates, authority boundaries, and finish protocol all apply unchanged.

This skill changes one thing: **GraphLake is the durable orchestration record.**
It replaces the base workflow's `local/<task>/orchestrator-log.md` and its
local status index. Do not maintain a duplicate markdown orchestration log.

Use this skill only when GraphLake Agent Memory is installed and connected for
the current repository. If it is unavailable, stop and ask the user to restore
it or use `$orchestrate` instead.

## Start

1. Follow `$orchestrate`'s Start section. Ask about the wrap-up presentation
   and any material scope choice before work begins.
2. Ground with `where_am_i`. Search GraphLake for an existing work item that
   matches the task before creating a new one. Resume its active run and plan
   when found. Do not recreate a plan from chat history.
3. For new work, create the GraphLake record before dispatching:
   - `create_work_item` with concrete success criteria.
   - `create_plan` for the bounded units.
   - `record_task` for every dispatchable unit, including dependencies and
     acceptance criteria in the task content.
   - `create_agent_run` with the first task as the current step.
4. Read the `$orchestrate` reference for the selected mode. Replace every
   instruction to create or update `orchestrator-log.md` with the GraphLake
   record rules below.

## GraphLake record rules

Record state when it happens. Do not reconstruct the run at closeout.

| Orchestration information | GraphLake record |
| --- | --- |
| Unit index, owner, dependency, state, validation | `agm:Task` in the plan, plus the active `agm:AgentRun` cursor |
| Dispatch brief and task-specific constraints | Concise task content and/or a linked `agm:Artifact` |
| Convention pack or shared guidance | `agm:Artifact`; store concise text in `content`, otherwise record its path, MIME type, checksum, and summary |
| Steering choice, scope change, recovery choice | `record_decision` with its basis and rejected alternative |
| Review finding, test observation, blocker, source fact | `record_datapoint` with the appropriate kind |
| Doer, reviewer, test, synthesis, or presentation report | `record_artifact`, linked to the producing task; large payloads remain on disk and are referenced by path or URI |
| Commit, PR, rendered deck, report, screenshot, query, or test result | `record_artifact`, linked to the producing task |

Use `local/<task>/` only as backing storage for large reports, logs, rendered
files, and other physical payloads. Every durable file must have a corresponding
GraphLake artifact. Do not depend on an unrecorded local path to resume work.

## Per-unit loop

Follow `$orchestrate`'s mode workflow for dispatch, review, fix loops, and
validation. Around each unit:

1. Claim or advance to the unit with `claim_step` / `advance_cursor`, then
   `heartbeat` the run before dispatch.
2. Give the doer the task IRI, success criteria, relevant GraphLake artifacts,
   and any convention artifact. The doer must report exact outputs and tests.
3. Record material findings and decisions before sending a fix loop or moving
   to another unit. A reviewer verdict is not only prose: record its findings
   and the decision to ship, revise, or defer.
4. On completion, record every durable output as an artifact, then call
   `complete_step` with the produced artifact when applicable.
5. Before a context clear, handoff, or long wait, call `checkpoint`.

The coordinator remains hands-off. Recording GraphLake state does not authorize
the coordinator to implement, debug, investigate, or test a unit itself.

## Jira input

When the user provides a Jira issue, Jira is a required source. Fetch the issue
before planning. Record a concise Jira snapshot as an artifact or data point,
including key, URL, summary, acceptance criteria, and current status.

Do not invent Jira sync fields, ontology extensions, comments, transitions, or
other Jira writes. Read the connected Atlassian tool surface first. Only write
back when the user explicitly authorized that external action and the available
tool supports it. Record the resulting Jira URL, comment, or transition as a
GraphLake artifact.

## Finish

1. Query the plan. Do not close until every required task is completed or the
   remaining task state is explicitly blocked or skipped.
2. Record the final validation evidence and all durable outputs as artifacts.
3. `checkpoint`, then `closeout` with a verdict against the work item's success
   criteria.
4. Follow `$orchestrate`'s Finish section. The final response links or names
   GraphLake artifacts rather than an `orchestrator-log.md`.
5. If the user requested a wrap-up presentation, follow `$orchestrate`'s
   presentation reference. Record the resulting deck or one-pager as an
   artifact.

## No secrets

Never record secrets, credentials, tokens, or private user data in GraphLake,
local artifacts, agent reports, or external issue comments.
