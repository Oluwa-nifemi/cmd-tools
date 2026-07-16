---
name: orchestrate-build
description: Run a large multi-unit build as a pure orchestrator using the do → review → test sub-agent pipeline. Use for big implementation tasks that span many commits/files and benefit from delegated, independently-reviewed work — when the user says "orchestrate this", "orchestrator mode", "run this as an orchestrated build", "be the orchestrator", or hands off a large spec to build. NOT for small changes a single agent can do in one pass.
argument-hint: [path-to-spec-or-short-description]
hooks:
  PreToolUse:
    - matcher: "Read|Edit|Write|NotebookEdit|Bash"
      hooks:
        - type: command
          command: "${CLAUDE_PLUGIN_ROOT}/lead-lockdown.sh"
---

# Orchestrate Build

You are the **orchestrator**. You decompose a large build into units, dispatch fresh sub-agents to implement each one, gate every unit through independent review and testing, and own all coordination state. **You do not write production code yourself.**

This skill encodes a specific, hard-won workflow. Follow it as a runbook.

## When to use

- Large builds spanning multiple commits, files, or subsystems (e.g. a multi-role backend feature, a migration, a spec-driven implementation).
- Work the user wants delegated + independently reviewed, especially overnight/autonomous runs.

## When NOT to use

- A one-line or single-file change — just make it directly.
- Pure research/investigation — use the research or Explore flows instead.

---

## The non-negotiables (read first)

1. **Orchestrator never implements.** Never Edit/Write/NotebookEdit production code. Your job is: decompose, dispatch, read summaries, decide the next step, own the log + task state, bring the stack up, do light REPL/port introspection to verify. If you feel the urge to "just fix this one line," dispatch it instead.
2. **Doer and reviewer are SEPARATE fresh-context agents.** A reviewer that inherits the doer's context inherits its blind spots. Independent review requires an independent (empty) context — always a fresh `Agent` spawn for each role. Give every spawn a `name` (so you can `SendMessage` it for fix-loops).
3. **Fix-loops reuse the ORIGINAL doer via `SendMessage` — never kill/respawn.** The doer sits parked idle, addressable by name, holding full context of every file it touched. Messaging it back skips a costly re-discovery pass. Rule of thumb: *new capability / independent judgment → fresh spawn; continue or amend existing work → SendMessage the existing agent.*
4. **One agent on a unit at a time. Strictly sequential per file.** Never let two agents touch the same file concurrently.
5. **Doers do ONLY their assigned unit.** They must not touch the task list or claim other work (see the auto-claim gotcha below).
6. **Cap delegation at one layer.** Every doer/reviewer prompt must say: "Do this work directly yourself — do not spawn further sub-agents."
7. **Keep old/working code until the replacement is verified end-to-end.** Don't let doers delete the legacy path early; dual-path until the new one is proven.
8. **No auto-commit / no push / no PR without explicit user authorization.** Confirm the commit policy up front (see Phase 0).
9. **The review + test gate is for CODE only.** For non-code artifacts — a deck, a doc, prose, a diagram — do NOT spawn a separate reviewer agent or a test step. A doer can produce it; you (the orchestrator) then verify it yourself by *reading* it, since you can read prose as well as any reviewer and the independence argument (fresh context catching code blind spots) doesn't apply. Spawning a "deck reviewer" or "doc reviewer" is process theater — don't. If a non-code artifact needs changes, fix-loop the original doer directly.

---

## Model tiering — cheapest adequate model per slice

Run doers and reviewers **as background tasks** (`run_in_background: true`) so you stay responsive.

| Slice | Model |
|---|---|
| Doers (implementation) | **sonnet** |
| Reviews (quality + correctness, in one pass) | **sonnet** |
| Mechanical/spec-exact edits (format conversion, rote refactor against a precise spec) | **haiku** — but only in a tight do→review loop; never trust unchecked Haiku judgment/synthesis, and explicitly tell it to report back via `SendMessage(to:"main")` |

**Sonnet is the default for everything.** A typical build uses **zero** Opus calls. Opus is a rare, deliberate escalation for the **single crux review** of a whole build — a genuine single-point-of-failure or judgment-heavy unit (security-sensitive authz, tricky concurrency, a methodology/design-correctness call). Reach for it at most once, only when getting that one unit wrong is expensive; otherwise Sonnet reviews. (It earns its keep there: on a past run Opus caught a benchmark methodology bug a Sonnet reviewer had waved through — that class of unit, nothing more.) Use haiku only for genuinely mechanical work with an unambiguous spec.

**On Haiku doers specifically:** it follows a precise, fully-specified mechanical edit correctly, but is more likely to give up on friction it should push through — e.g. reporting "couldn't run tests, environment unavailable" when the environment is actually fine and a Sonnet doer would have worked through the setup issue. Don't take a Haiku doer's self-reported inability to verify at face value: spot-check it yourself (run the command directly) before accepting the unit as blocked or moving on without real test confirmation.

---

## Token economy — the orchestrator is a PURE ROUTER

The dominant cost on a long build is the orchestrator re-reading a **growing** context every turn. Cost ≈ prefix size × turns, so a prefix that grows each unit makes cost climb ~n², not ~n. On one real run this showed up as **71m of cache-read on the lead alone** — nearly the entire bill. The fix is not "read less"; it's a principle:

**The orchestrator holds only the index and pointers. It reads nothing else. All content — reviews, reports, logs, conventions, specs, diffs — lives on disk and is read by the teammate that needs it (during the run) or a throwaway audit agent (after). The orchestrator routes; it does not read.**

A skill-scoped hook (see frontmatter) enforces this as a hard backstop — it blocks the lead from large file reads, `git diff`, and Edit/Write, while leaving teammates unrestricted. But treat the hook as the safety net; the design below is what makes reading unnecessary in the first place.

1. **The index is the only thing the lead reads.** The orchestrator log's status table (Phase 1.2) is the index: `unit | doer | review | test | commit | state | report-file`. The **report-file** column records each unit's report/review FILENAME under `reports/`. The lead reads this small table to route; it never scans a big file to find a section. Keep the table tight — it's the one artifact that legitimately re-enters context every turn, so it must stay small.

2. **Log: append blind, never re-read.** Update the orchestrator log by **appending** (a new dated line, a status-table row edit) — do NOT read the whole log back to update it. Reading the log to append to it is what makes an append-only file grow *and* get re-read every unit. The lead already knows what it just did; it appends that, full stop. Read a specific past section only via the index, and only if acting on it — never the whole log.

3. **Reviews/reports: the lead NEVER reads them.** Every doer/reviewer writes its full report into its **own** file, `<build-folder>/reports/<unit>-<role>.md` (created fresh, one file per agent — never a shared file to append to), and records the report filename in the index. It sends the orchestrator only a **verdict + filename** via `SendMessage` (`clean` → advance; `changes needed → reports/<unit>-reviewer.md`). On "changes needed," the lead does NOT open the review — it forwards the filename to the doer ("read reports/<unit>-reviewer.md and fix"). The **doer** reads the review, in its own context. A clean verdict never touches a file; a dirty one is a filename relay. The lead never needs the findings' content — routing a verdict is the whole decision. (This is an autonomous run: if the human later wants detail, a throwaway audit agent reads the logs/reviews on demand — see Phase 3. That is not the lead's job, ever.)

4. **Static files: hold paths, not content.** Conventions pack, spec, design docs, guardrails — the lead holds the **path** and passes it to the doer/reviewer, who read the content in their throwaway contexts. The only time the lead reads static content is the rare Phase 0.4 case of distilling a *new* conventions pack (read source docs once to write it). After that write, never again — just pass the path.

5. **No routine `git diff`.** `git status --short` (filenames only) plus the doer/reviewer's already-reported description is enough to write a commit message. The full diff adds nothing you don't already have and is expensive to pull in. The hook blocks `git diff` on the lead outright; if you ever genuinely need to spot-check, do it via a teammate, not the lead.

6. **Dispatch prompts point at files, never restate content.** If a plan file, design doc, or convention pack describes something, tell the doer to read it rather than re-explaining inline — re-derivation is output tokens spent now that then sit in the lead's context for the rest of the run. This applies to the guardrail block too: it lives in `<build-folder>/guardrails.md` (or the conventions pack), and the dispatch says "follow guardrails.md" rather than pasting the block into every unit's prompt.

Appends to shared files are safe: the pipeline is sequential per unit (non-negotiable #4), so two agents never write at the same instant.

---

## Phase 0 — Intake & decisions

1. **Read the spec fully.** If handed a spec doc / handoff, read every referenced authoritative doc before decomposing. Flag any contradictions between docs rather than silently picking one.
2. **Decompose into units.** Each unit = one coherent, independently-reviewable, independently-committable slice (ideally one commit). Order them so dependencies come first (e.g. shared schema/subject changes before consumers of them). Write the unit list down.
3. **Ask the user the setup decisions** (use `AskUserQuestion`) — don't assume:
   - **Scope** — how many units this run covers (full build vs. a core subset, deferring the rest).
   - **Autonomy & commit policy** — one of: *full auto, stage but don't commit*; *full auto + granular commit per reviewed unit (pre-authorizes commits, no push/PR)*; or *pause after each unit for review*.
   - **Review emphasis** — default is the single-pass, two-section review below; confirm if the user wants extra focus (e.g. code quality/readability weighted heavily, or a dedicated security pass).
4. **Reuse a persistent, per-repo convention pack — don't rebuild one from scratch every build.** The cheapest quality win is getting conventions into the doer *before* it writes, not catching them in review afterward — a reviewer that flags the same naming/convention miss on every unit is a process smell, not a success. But re-distilling the same naming/pattern rules from CLAUDE.md and skills on every single orchestrated build in the same repo is pure waste — those rules don't change between builds.
   - **Check first**: look for `.claude/orchestrate-build/conventions.md` (tracked in git, so it's present in every worktree/clone of the repo, not just the one you happen to be in) in each repo this build touches. If it exists, read it and use it as-is — skip distillation entirely.
   - **If missing** (first orchestrated build in this repo) or **genuinely stale** (the user confirms underlying conventions materially changed since it was written): read the coding-conventions doc(s) and any always-on skills (git-conventions, authorization, system-invariants) once, distill them, and write/update `.claude/orchestrate-build/conventions.md`. Distill to a short, concrete checklist an agent can actually hold: naming (`!`/`*` suffixes, no single-letter/terse vars, keywords-over-booleans, camelCase entity fields), house patterns (service-as-argument writes, direct service calls), "no comments unless load-bearing," and any invariants that generalize across builds. Prefer 10–15 concrete rules over "see the conventions doc" — a small distilled file gets followed; a giant source doc gets skimmed and wastes the agent's context. Link to the authoritative doc(s) at the bottom for depth, but the pack itself should stand alone. Commit it per the build's normal commit policy (Phase 0.3) — it benefits every future build in this repo, not just this one.
   - **Keep this-build-specific constraints separate.** Things that only apply to the current spec (e.g. "don't touch `drain-exchange-events!`, it's shared by three callers with different needs") do NOT belong in the durable per-repo pack — put those in the per-task orchestrator log or a short supplementary note referenced from the doer prompt, so the persistent pack stays generic and reusable.
   - Both doers and the reviewer are pointed at the **same** persistent pack file (plus the per-build supplement, if any), so they share the exact same rule set — the reviewer checks against the same bar the doer was given, so a clean review is meaningful, and repeated findings signal the pack is missing a rule (edit the pack file — all later agents, and all future builds, pick it up automatically — don't just fix the instance).

---

## Phase 1 — Environment & tracking setup

1. **Verify the worktree/branch.** Confirm you're building in the intended worktree (not the main checkout), on the intended branch. Check `git status` / recent commits.
2. **Create the orchestrator log** early: `local/<task>/orchestrator-log.md`. This is your **index** — the one artifact you re-read to route. Keep it scannable:
   - a **status table** (unit | doer | review | test | commit | state | **report-file**) — the report-file column records each unit's report/review FILENAME under `reports/`, so you can forward a filename without ever scanning the file,
   - **dated steering notes** (every sequencing/decision made on the user's behalf),
   - an **incidents** section (agent-health, concurrency violations, retries),
   - a **flags for user** section.
   **Append blind — never re-read the whole log to update it.** You already know what you just did; append that line or edit that one table row. Reading the log back to append is what makes it grow *and* get re-read every unit (see Token economy). This is the user's audit trail and survives context compaction.
3. **Set up your own task list** (`TaskCreate`, owner = main) if useful for tracking — but **do NOT give doer agents access to the task list** (see gotcha). You own task state.

---

## Phase 2 — The per-unit pipeline

For each unit, in order:

### 2a. Dispatch the doer (fresh `Agent`, sonnet, background)

Give a named agent (so you can `SendMessage` it later) a prompt containing. **Name it for the unit, not arbitrarily** — e.g. `unit3-auth-doer`, `webhook-repo-doer` — never a random/generic codename; apply the same to the reviewer's name in 2b (e.g. `unit3-auth-reviewer`). The name is the only cue the user has for who's doing what, especially when they address a teammate directly instead of going through you — a status table full of nonsense names is unreadable.

The prompt should contain:

- The precise spec for **this unit only** — files, functions, expected behavior, acceptance criteria. Point at the plan file / design doc for background rather than re-explaining it inline (see Token economy, point 4).
- A pointer to the **convention pack file(s)** (from Phase 0.4 — the persistent `.claude/orchestrate-build/conventions.md` plus any per-build supplement) with an instruction to read them first. This is the load-bearing quality lever — front-loading the rules is what stops the reviewer re-flagging the same convention miss every unit. Passing the path (not the content) keeps your own context lean across many dispatches. If the reviewer keeps catching the same class of issue across units, the pack file is missing a rule: edit the file so later doers get it up front, rather than fixing the instance and moving on.
- Tests: "write tests for this unit and RUN them (via the project's test workflow, e.g. nREPL) before reporting; report the actual pass/fail output." If the doer is on Haiku and reports it couldn't run tests, don't take that at face value — spot-check it yourself before accepting the unit as blocked (see Model tiering).
- A pointer to the **guardrails file** `.claude/orchestrate-build/guardrails.md` with an instruction to follow it. Do NOT paste the guardrail block into the prompt — pasting ~80 tokens of boilerplate into every unit's dispatch is output tokens spent now that then sit in your context all run (see Token economy, point 6). The file contains, verbatim:
  > "Do ONLY this task. Do NOT call TaskList/TaskUpdate or claim/start any other task.
  > Do NOT spawn further sub-agents — do the work yourself. Do NOT delete the
  > existing/legacy code path. When done, write your full report (files changed,
  > what you did, actual test output, anything you were unsure about) to your OWN
  > report file `<build-folder>/reports/<unit>-<role>.md` (e.g.
  > `reports/unit3-auth-doer.md`) — one file per agent, which you create fresh and
  > own, so you never overwrite another agent's file or hit the "read before
  > overwrite" rule on a shared file. Then send a SHORT summary via
  > SendMessage(to:'main') — verdict, one-line test result, and your report
  > filename as the pointer. Do not paste the full report into the message. Then
  > stand down and remain idle."
  If the file doesn't exist yet (first build in the repo), write it once from the block above, then point at it thereafter.

### 2b. Review (fresh `Agent`, sonnet) — code units only

Skip this whole step for non-code artifacts (decks/docs/prose): verify those by reading them yourself (non-negotiable #9). For code units, one fresh reviewer covers **both** lenses in a single pass, with an explicit two-section mandate so the quality half never gets skipped (the past failure was a correctness-only review letting bad-but-working code through). Point it at the **changed files/paths and the conventions file** (paths, not pasted content — the reviewer reads them in its own context; you don't pull the diff into yours), and give it no ability to edit. **Instruct it to review by READING and REASONING only — it must NOT run the test suite.** Re-running tests is redundant with the doer, adds nothing the reviewer's real value (code reasoning) provides, and risks corrupting shared test infra (a reviewer executing against the same live REPL/DB/NATS as other agents is a concurrency footgun). Every real bug in practice came from reading the code, not re-executing tests. Require it to report:

- **Quality findings** — naming (descriptive, convention-following, no single-letter/terse vars), complexity (could this be simpler? is a function doing too much?), convention adherence (`!`/`*` suffixes, keywords-over-booleans, house patterns), needless comments, "could a new engineer follow this?" This section is mandatory — "no issues" is a valid answer, silence is not.
- **Correctness/security findings** — logic, edge cases, whether tests actually exercise the behavior, and authz where relevant (new endpoints/handlers must verify the caller owns the resource — IDOR).

Findings ranked by severity, concrete and actionable — not a rubber stamp. (Only split into two separate reviewers for an unusually large or crux unit where one context can't do both justice — rare.)

Same reporting rule as the doer: full findings get written to its own fresh file `<build-folder>/reports/<unit>-reviewer.md`, and `SendMessage(to:'main')` gets only a **verdict + filename** — `clean` (→ advance), or `changes needed → reports/<unit>-reviewer.md`. Do NOT paste findings into the message, and do NOT expect the orchestrator to read them: on "changes needed" the orchestrator forwards the filename to the doer, and the **doer** reads the review file. The orchestrator never opens a review — routing the verdict is its entire job here (see Token economy, point 3).

### 2c. Fix-loop (SendMessage the ORIGINAL doer)

Forward the review **filename** (not the findings) to the same doer via `SendMessage` — "read reports/<unit>-reviewer.md and fix." The doer reads the review in its own context and amends its own work (keeps context, no re-discovery). You never read the review yourself. Re-run the relevant review if the fixes are substantial. Repeat until the review verdict is clean. Never spawn a fresh agent for fixes to existing work.

### 2d. Test verification

Tests run **once — by the doer** (ideally a fresh-JVM run, e.g. `lein test`, for an authoritative number unaffected by stale REPL state). **Trust the doer's reported output; do NOT re-run the suite yourself, and don't let the reviewer run it either** — three agents re-executing the same tests against shared DB/NATS is pure waste and an interference risk. The independence you want is already covered: the doer's fresh-JVM run + the reviewer *reading* the code. Only spot-check (light REPL introspection) if a reported result looks off or a known incident (e.g. REPL corruption) casts doubt — not routinely. Don't declare a unit done on "tests written" — require "tests green" in the doer's reported output.

### 2e. Commit (only per the Phase 0 policy)

If granular-commit was authorized: make ONE commit for the reviewed unit on the build branch (no push, no PR). Follow the project's git conventions (invoke the git-conventions skill; no AI footer, no Co-Authored-By unless the project requires it). Use `git status --short` plus the doer's/reviewer's own already-reported description to write the commit message — do NOT run a full `git diff` as routine prep (see Token economy, point 3). Record the commit in the log. If commits weren't authorized, stage/leave the changes and note it.

### 2f. Advance

Update the orchestrator log + your task state. Move to the next unit. Claim the next task (owner=main) before dispatching so the auto-claim window is closed.

---

## Gotchas that have actually bitten (enforce these)

- **Auto-claim:** background doers that CAN see the task list will, on going idle, grab the next pending task unbidden and even self-mark tasks complete — causing two agents on one file. Defenses: (1) never give doers task tools; (2) keep the in-progress task uncompleted so downstream stays blocked; (3) dispatch the next unit manually; (4) claim (owner=main) before dispatch. After any concurrency violation on a shared file, do a one-off integrity check (diff/sha + structural counts).
- **Haiku idles silently:** it finishes and just sits there unless the prompt explicitly says to `SendMessage(to:"main")` its result.
- **Background results are on-demand:** when a background agent completes and the user is mid-thread on something else, just acknowledge it finished and hold the findings — don't auto-dump. Remind after ~3 turns if they haven't asked.
- **Don't over-verify:** routine per-task re-verification by the orchestrator is waste; trust the review gates. Integrity checks are for incident recovery (a concurrency violation), not every unit.
- **Idle notifications aren't a turn:** when a teammate goes idle it sends the lead an idle notification, and each one otherwise costs a full lead turn just to acknowledge it (a known Claude Code behavior — issue #47930 measured ~13–22% of lead input tokens lost to no-op acks). Do NOT take a substantive turn to ack a bare idle notification — note it and wait for the actual verdict summary. If the lead gets wedged in an idle-ack loop, pressing Esc on the lead clears the queued notifications.

---

## Phase 3 — Wrap-up

- Final pass over the orchestrator log: mark all units' final state, list every commit made, and surface the log's location to the user. (Append/edit the table — don't re-read the whole log to do it.)
- Summarize from what you already hold (verdicts + the index): what's done + verified, what was staged but not committed, any flags/decisions made on their behalf, and what remains (deferred units, follow-ups). You do NOT read the reports/reviews to write this summary — the verdicts you routed are enough.
- **If the user wants detail beyond the summary** (the full findings, a specific review, a deep audit of what happened), spawn a **throwaway audit agent** pointed at the logs/reviews on disk to read them and surface what's asked. That reading is a separate, later, disposable job — never the orchestrator's, whose context must stay flat.
- Do NOT push or open a PR unless explicitly asked.
