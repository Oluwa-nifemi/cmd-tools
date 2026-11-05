# Brief template

Every dispatch uses this shape. Put hard constraints first. Keep the brief short enough to read in one pass; a long brief hides the one thing that matters.

## Readiness check

Run this before writing the brief. Dispatch only when every item holds. Otherwise create a preparation unit or fix the gap yourself.

- Every input exists now: dependencies merged, interfaces published, files present, fixtures and saved test data prepared. Never tell a worker to wait for something another worker is still producing.
- The unit owns its files exclusively. No other writer touches them.
- You ran the acceptance command once and recorded its baseline (error counts, known failing tests).
- The environment works: dependencies installed, a clean copy or worktree when the work is risky, the target app or service running once when the check needs it.
- Anything that allows one user at a time (a GUI or browser session, a running app instance, a port, a database, a lockfile) has exactly one owner in the run.

## Fields

1. **Goal.** One behavior, in one or two sentences.
2. **Constraints.** The few rules that must not be broken: scope, forbidden commands, files not to touch.
3. **Owned files.** The files the worker may edit. Everything else is read-only.
4. **Context files.** What to read, and which function or section matters. Never "the repo".
5. **Given interfaces.** Signatures, types, or message shapes already decided. If the worker must invent one, the unit is too big or needs a spec step first.
6. **Insertion points.** File and function where the change goes, when you know them.
7. **Acceptance.** The exact command, its baseline, and the expected result. State what "done" proves.
8. **Out of scope.** What the worker must leave alone.
9. **Blocker rule.** If the worker cannot start editing within the declared bound, or needs something that does not exist, it stops and reports the exact blocker.
10. **Bounds.** When the first change is expected, and a ceiling on time or tool calls. The coordinator enforces the ceiling; the worker is not trusted to keep it.
11. **Report.** Path, frontmatter, and contents: changed files, baseline versus after, proof output, gaps.

## Shape for lower-cost models

- Prefer exact paths and insertion points over a description of where to look.
- State the check up front and make it runnable by the worker. "Done" is a command passing, not a judgment.
- One behavior per brief. If you wrote "and" between two behaviors, write two briefs.
- Hand over prepared inputs (fixtures, a working copy) instead of asking the worker to build them.
- Do not stack reminders. When a worker misses its bound, narrow or replace the unit (see the stall protocol in [shared-protocol.md](shared-protocol.md)).
- Mapping, fixtures, specified implementation, mechanical edits, and first-pass review work well. Deciding interfaces, ownership, or trust boundaries does not belong in a lower-cost brief.

## Example

Weak: "Implement chat move. Handle active runs, rollback, the client menu and the server route. Another worker is finishing the preparation API, so coordinate with it. Be quick."

Strong: "Add an 'Archive chats' item to the row menu in ProjectsPage.tsx. Confirm first, archive every non-running chat of that project with the existing per-chat archive action, skip running chats, and show a one-line result. Owned files: ProjectsPage.tsx plus one new helper beside it. Done when tsc shows only the 2 known baseline errors. Do not add tests."
