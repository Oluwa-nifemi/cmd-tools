---
name: repl-tools
description: Evaluate Clojure code and run Clojure tests through a project-scoped nREPL using runrepl, runtests, startrepl, killrepl and repls. Use whenever the task involves a Clojure/Leiningen project REPL: evaluating forms, reloading namespaces, running clojure.test tests, starting or stopping the dev system ((go), (user/stop)), a stuck or stale or out-of-memory REPL, REPL memory use, or Postgres "connection slots" errors from dev systems. Make sure to use it even if the user only says "run this test", "check it in the REPL" or "restart the REPL", and prefer it over calling lein repl or clj-nrepl-eval directly. Not for ClojureScript browser REPLs, non-Clojure REPLs, or plain shell commands.
---

# Project-scoped nREPL

Run tools from the project directory. They resolve the REPL for that worktree
and start one when needed. A first call on a cold project starts the REPL and
then evaluates in the same call (about 40s), so do not retry or start a second
one while it runs.

Never run `lein repl` (it starts a JVM the registry, cap and cleanup cannot
see). Never use `clj-nrepl-eval --discover-ports` (it can pick a REPL from
another worktree).

```sh
runrepl '(+ 1 2)'
runrepl --no-start '(+ 1 2)'
runrepl --fresh '(+ 1 2)'      # kill REPL, start clean, evaluate (~40s, loses state)
runrepl --port-owner 3000 '(user/stop)'   # target the worktree whose app holds port 3000
runtests TEST_NS [SOURCE_NS...]           # reload sources + tests, run tests, one call
startrepl
killrepl [N]                   # current project, or REPL #N from `repls`
repls                          # list live REPLs
```

## Do not run these bare (they hang agents)

- `watchrepl` / `seerepl` run `tail -f` and never exit. Use `watchrepl --no-follow [N]` (last 80 log lines, exits).
- `gotorepl` opens an interactive subshell. Use `gotorepl --print [N]` to get the path.

## Running tests

`runtests ardoq.foo-test ardoq.foo` reloads the source ns, then the test ns,
then runs the tests. Reloading both is needed, or you test old code. The exit
code is non-zero on failures or errors. Check the last lines of output for
`Ran N tests...` and `F failures, E errors.`, because app logs can bury them.

`require :reload` does not remove deleted or renamed vars, so an old test keeps
running. Unmap it, then rerun:

```sh
runrepl '(ns-unmap (quote ardoq.foo-test) (quote old-test-name))'
```

Use `runrepl --fresh` only when stale state is widespread.

## Other tools

- `pgslots [--reclaim]`: every `(go)` fails with "remaining connection slots are reserved". This is a full local Postgres pool, not a broken REPL. Run `pgslots`, then `pgslots --reclaim` (frees idle backends, safe).
- `repl-memory [--kill N]`: show JVM memory of REPLs and Clojure LSP; stop one.

## When something fails

- No REPL can be resolved or started: stop and report. Do not guess a port.
- REPL stale, disconnected or unresponsive: `killrepl`, `startrepl`, reload namespaces, retry once. If it fails again, report the error. Debugging a dead session wastes time.
- Startup or lock wait times out (lock path and owner PID in the error): `killrepl --force`, `startrepl` once, retry once, then report.
- `OutOfMemoryError`, timeouts, env vars, auto-cleanup: read [references/troubleshooting.md](references/troubleshooting.md).
- `runrepl` reads `~/.cache/zed-clojure-repl/registry.json`, outside the Codex workspace. On a permission error, retry with escalation.
