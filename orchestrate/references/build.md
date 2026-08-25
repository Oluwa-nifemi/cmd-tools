# Build orchestration

Use this workflow for a substantial implementation spanning multiple files, subsystems, or independently reviewable units. Do not use it for a small change one agent can safely complete.

Act as the coordinator, not an implementation doer. Do not edit production code yourself because it is convenient; dispatch a bounded doer unit instead.

This extends to ALL hands-on work: reading error logs to debug a failure, running commands to investigate why a test broke, applying a "quick" one-line fix, interacting with a UI to test behavior, or reading source code to understand a bug. If a doer reports a failure, send the failure report back to the doer or dispatch a fresh fix agent. Do not absorb the investigation or fix into the coordinator's turn.

## Set up

1. Read the authoritative specification and resolve contradictions before decomposition.
2. Confirm scope, commit policy, and any special review emphasis. Do not assume commits, pushes, or pull requests are authorized.
3. Check the intended worktree and branch. Create a compact index under `local/<task>/` with one row per unit.
4. Check `.claude/orchestrate/conventions.md`, then the legacy `.claude/orchestrate-build/conventions.md`. Reuse the first one found. If neither exists, distill the authoritative project guidance into `.claude/orchestrate/conventions.md`: 10–15 concrete naming, pattern, and invariant rules. Point both doers and reviewers at the same file; keep task-specific constraints in a task note instead.

## Per-unit pipeline

1. **Doer:** dispatch a named, fresh agent with one unit, relevant file paths, acceptance criteria, the convention pack, [build-guardrails.md](build-guardrails.md), and a report path. Require it to implement, write or update relevant tests, run the project test workflow, and report actual output. It must not claim other units, spawn agents, or remove a working legacy path before replacement is verified.
2. **Review:** dispatch exactly one fresh reviewer for each code review pass. The same reviewer assesses simplicity, quality, correctness, and security together. It reads and reasons about the changed paths but does not rerun the test suite. Require separate simplicity, quality, and correctness/security sections, ranked actionable findings, and a clear `clean` or `changes needed` verdict. Do not dispatch separate correctness and simplicity reviewers. Add a specialist reviewer only when a concrete high-risk concern requires expertise outside the main review.

   The simplicity section is mandatory. The reviewer must compare the implementation with the required behavior and the repository's existing primitives. It must identify anything that can be removed, collapsed, or expressed directly without losing required behavior. Review at least these risks:

   - abstractions, wrappers, indirection, or state that serve only one current use;
   - speculative flexibility for unrequested future cases;
   - defensive normalization, retries, fallbacks, or compatibility behavior without a stated requirement;
   - duplicated responsibilities or logic that an existing primitive already owns;
   - interfaces, configuration, dependencies, or helper types that expose more than the current contract needs.

   For each material complexity finding, give the simpler concrete design. Do not accept vague advice such as "simplify this." Tests passing does not justify unnecessary complexity. A reviewer MUST return `changes needed` when the code is correct but materially more complex than the requirements demand.
3. **Fix loop:** on material findings, send the review report path to the original doer. Re-review substantial fixes.
4. **Accept:** require the doer's green relevant tests and a clean review. Spot-check only when a report is implausible or an incident makes the normal gate untrustworthy.
5. **Commit:** commit one reviewed unit only when authorized. Never push or open a pull request without explicit authorization.

## Build-specific safeguards

- One writer per file at a time. Do not let background agents claim the next unit.
- A reviewer is independent judgment, not a second test runner.
- One reviewer owns the full ordinary review. Do not multiply reviewers by review category.
- Keep detailed doer and reviewer reports in separate files. Route report paths rather than repeatedly pasting findings into the coordinator context.
- Use Terra with low reasoning effort by default. Use Luna for tightly specified mechanical edits and checks. Routine implementation and review remain low effort. Use medium only for a named architectural or cross-system correctness risk. Reserve Sol or Opus with high effort for rare security-sensitive, irreversible, or adversarial judgment.
- If a code unit is really a migration, preserve the existing path until an end-to-end check proves the replacement.
