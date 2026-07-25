# Build orchestration

Use this workflow for a substantial implementation spanning multiple files, subsystems, or independently reviewable units. Do not use it for a small change one agent can safely complete.

## Set up

1. Read the authoritative specification and resolve contradictions before decomposition.
2. Confirm scope, commit policy, and any special review emphasis. Do not assume commits, pushes, or pull requests are authorized.
3. Check the intended worktree and branch. Create a compact index under `local/<task>/` with one row per unit.
4. Reuse the repository's convention pack when present. If it is missing, create a short concrete checklist from the authoritative project guidance; keep build-specific constraints in a task note instead.

## Per-unit pipeline

1. **Doer:** dispatch a named, fresh agent with one unit, relevant file paths, acceptance criteria, conventions, and a report path. Require it to implement, write or update relevant tests, run the project test workflow, and report actual output. It must not claim other units, spawn agents, or remove a working legacy path before replacement is verified.
2. **Review:** dispatch a fresh reviewer for code units. It reads and reasons about the changed paths but does not rerun the test suite. Require separate quality and correctness/security sections, ranked actionable findings, and a clear `clean` or `changes needed` verdict.
3. **Fix loop:** on material findings, send the review report path to the original doer. Re-review substantial fixes.
4. **Accept:** require the doer's green relevant tests and a clean review. Spot-check only when a report is implausible or an incident makes the normal gate untrustworthy.
5. **Commit:** commit one reviewed unit only when authorized. Never push or open a pull request without explicit authorization.

## Build-specific safeguards

- One writer per file at a time. Do not let background agents claim the next unit.
- A reviewer is independent judgment, not a second test runner.
- Keep detailed doer and reviewer reports in separate files. Route report paths rather than repeatedly pasting findings into the coordinator context.
- Use Sonnet by default. Use Haiku only for tightly specified mechanical edits with review. Reserve Opus for a rare high-consequence, judgment-heavy review.
- If a code unit is really a migration, preserve the existing path until an end-to-end check proves the replacement.
