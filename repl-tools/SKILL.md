---
name: repl-tools
description: Use the project-scoped nREPL tools to evaluate Clojure code or inspect an nREPL. Trigger when working with Clojure REPLs, evaluating Clojure code, running Clojure tests through a REPL, or debugging a Clojure project with nREPL.
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
startrepl
watchrepl
killrepl          # kill REPL for the current project
killrepl 2        # kill REPL #2 from `repls` listing
seerepl 1         # tail log for REPL #1 without cd-ing into its project
gotorepl 1        # cd into REPL #1's project directory
```

Before running Clojure tests, reload both the changed source namespace and its
test namespace.

```sh
runrepl '(require (quote ardoq.some.namespace) :reload)'
runrepl '(require (quote ardoq.some.namespace-test) :reload)'
runrepl '(clojure.test/run-tests (quote ardoq.some.namespace-test))'
```

If no REPL can be resolved or started, stop and report the failure. Do not
guess a port or choose another project's REPL.
