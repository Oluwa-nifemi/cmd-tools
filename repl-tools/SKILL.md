---
name: repl-tools
description: Use the project-scoped nREPL tools to evaluate Clojure code or inspect an nREPL. Trigger when working with Clojure REPLs, evaluating Clojure code, running Clojure tests through a REPL, or debugging a Clojure project with nREPL. Do not use for non-Clojure REPLs or generic shell evaluation.
---

# Project-scoped nREPL

Run `runrepl` from the project directory. Do not call `lein repl` directly.
`runrepl` resolves the REPL for that worktree and starts one when needed.

Do not use `clj-nrepl-eval --discover-ports`. It can select a REPL from another
worktree.

Use:

```sh
runrepl '(+ 1 2)'
runrepl --no-start '(+ 1 2)'
runrepl --fresh '(+ 1 2)'    # kill existing REPL, start fresh, then evaluate
startrepl
watchrepl
killrepl          # kill REPL for the current project
killrepl 2        # kill REPL #2 from `repls` listing
seerepl 1         # tail log for REPL #1 without cd-ing into its project
gotorepl 1        # cd into REPL #1's project directory
```

## Startup behavior

A first `runrepl` call may start the REPL and return only the startup
confirmation. When this happens, send the expression again in a second call.
`runrepl` prints "starting REPL for ..." to stderr when it launches a new
process. If you see that message and no evaluation result, retry the same
expression.

## Test workflow

Before running Clojure tests, reload both the changed source namespace and
its test namespace.

```sh
runrepl '(require (quote ardoq.some.namespace) :reload)'
runrepl '(require (quote ardoq.some.namespace-test) :reload)'
runrepl '(clojure.test/run-tests (quote ardoq.some.namespace-test))'
```

After running tests, check the **final lines** of output for the summary:

```
Ran N tests containing M assertions.
F failures, E errors.
```

Large application logs can bury this summary. Scroll past log noise to find
the `Ran ...` / `failures` / `errors` lines at the end.

When `runrepl` reports test failures (non-zero exit), treat the run as failed
even if the log output looks noisy.

## Stale vars after rename or delete

Clojure's `require :reload` does **not** remove vars that were deleted or
renamed in the source file. The old var stays interned in the namespace and
continues to run as a test.

When you know the old var name, unmap it explicitly:

```sh
runrepl '(ns-unmap (quote ardoq.some.namespace-test) (quote old-test-name))'
```

Then reload and re-run:

```sh
runrepl '(require (quote ardoq.some.namespace-test) :reload)'
runrepl '(clojure.test/run-tests (quote ardoq.some.namespace-test))'
```

Use `runrepl --fresh` to kill and restart the REPL only as a last resort,
when stale state is unknown or widespread. It is slower (~40s) and loses all
loaded state.

## Sandbox note

`runrepl` reads `~/.cache/zed-clojure-repl/registry.json`, which lives
outside the workspace. In Codex, the first call may need sandbox approval.
Retry with escalation if it fails with a permission error.

## Failure handling

If no REPL can be resolved or started, stop and report the failure. Do not
guess a port or choose another project's REPL.

When a project REPL is stale, disconnected, or unresponsive, do not waste
time debugging that session. Kill it with `killrepl`, start a clean one with
`startrepl`, reload the required namespaces, and retry once. If the fresh
REPL also fails, report the concrete failure.
