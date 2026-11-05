# Build orchestration

Use this workflow for a substantial implementation spanning multiple files, subsystems, or independently reviewable units. Do not use it for a small change one agent can safely complete.

## Set up

1. Read the authoritative specification and resolve contradictions before decomposition.
2. Confirm scope, commit policy, and any special review emphasis. Do not assume commits, pushes, or pull requests are authorized.
3. Check the intended worktree and branch. Create a compact index under `local/<task>/` with one row per unit.
4. Check `.claude/orchestrate/conventions.md`. Reuse it if found. Otherwise distill the authoritative project guidance into it: 10–15 concrete naming, pattern, and invariant rules. Point both doers and reviewers at the same file; keep task-specific constraints in a task note instead.

5. Size every unit for the model that will run it (see Unit sizing) and confirm it passes the readiness check in [brief-template.md](brief-template.md) before dispatch.

## Unit sizing

Size units by complexity, not by file count. A unit suits a lower-cost model when you can pass these checks:

- You can state the change and its proof in a few sentences.
- The worker does not decide anything other units depend on, such as interfaces, naming, or ownership.
- Everything it needs already exists: dependencies merged, interfaces published, fixtures prepared.
- One command shows it is done.

When a check fails, split the unit. Do not move it to another model. Work that crosses layers splits by layer, with the unit that defines the shared interface first. Move a unit to a stronger tier only when the user allows it.

## Per-unit pipeline

1. **Doer:** dispatch a named, fresh agent with one unit, relevant file paths, acceptance criteria, the convention pack, [build-guardrails.md](build-guardrails.md), and a report path. Require it to implement the change and perform validation proportional to its risk and the repository's existing practice. Preserve existing tests unless the requested behavior requires a focused update. Add the smallest behavior-focused test only when it materially protects new behavior or a regression fix. It must not claim other units, spawn agents, or remove a working legacy path before replacement is verified.
2. **Review:** dispatch exactly one fresh reviewer for each code review pass, with [reviewer-brief.md](reviewer-brief.md) and the doer report path. Do not read the brief yourself. Add a specialist reviewer only when a concrete high-risk concern requires expertise outside the main review.
3. **Fix loop:** when the reviewer report header says `revision_required`, send its path to the original doer without reading the body. Re-review substantial fixes.
4. **Accept:** require the doer's reported repository-appropriate validation and a reviewer report with `status: clean`. Spot-check only when a report is implausible or an incident makes the normal gate untrustworthy.
5. **Commit:** commit one reviewed unit only when authorized. Never push or open a pull request without explicit authorization.

## Build-specific safeguards

- One writer per file at a time. Do not let background agents claim the next unit.
- A reviewer is independent judgment, not a second test runner.
- One reviewer owns the full ordinary review. Do not multiply reviewers by review category.
- Keep detailed doer and reviewer reports in separate files with the shared-protocol frontmatter. Read only the header and route report paths without loading the body into coordinator context.
- Choose model and effort from [model-tiers.md](model-tiers.md).
- If a code unit is really a migration, preserve the existing path until an end-to-end check proves the replacement.
- Write every doer brief from [brief-template.md](brief-template.md).
- Review a complete behavior, not each trivial unit. After fixes, re-review only what changed.
- Do not create a unit for a trivial follow-up the coordinator can make directly under the hands-off exceptions.

## Evidence gates

- Doers record baselines (build, type, and test results) before editing. A claim that a failure is pre-existing must cite that baseline run.
- For work that crosses layers, require a proof through the public interface: a real call with a fresh readback. Source review alone cannot show that a field survives every mapper or allowlist.
- A doer that reports done while listing unfinished parts has not passed the gate.
