# REPL troubleshooting reference

## Startup and lock timeouts

Starting a REPL can take up to 240s on a busy machine
(`ZED_CLOJURE_REPL_START_SECONDS`). A normal startup returns once ready. A
failed startup returns at once. Let the call that started it finish.

A second `startrepl` or `runrepl` for the same project waits on the startup
lock for 240s (`ZED_CLOJURE_REPL_LOCK_WAIT_SECONDS`), then fails with the lock
path and owner PID. Give the command at least 250s before your tool call times
out, or you will not see that error.

## Automatic cleanup

`startrepl`, `runrepl` and `repls` stop a REPL when its worktree folder is
deleted or it has been idle for 24 hours (`ZED_CLOJURE_REPL_IDLE_SECONDS`).
Starting a REPL evicts the least recently used one at the cap of 3
(`ZED_CLOJURE_MAX_REPLS`), like Zed's own REPL manager. A REPL serving an app
on a non-loopback port is never stopped by idleness or the cap.

## Heap limit

Every Leiningen REPL gets a 4 GB heap from `:jvm-opts ["-Xmx4g"]` in
`~/.lein/profiles.clj`. It was sized from measurements: a heavy test
namespace peaked at about 2.9 GB, with 0.6 GB live after garbage collection.

On `java.lang.OutOfMemoryError` in a test, `(go)` or an evaluation, first rule
out a runaway result, such as printing a huge collection. If the work is
legitimate, change `-Xmx4g` to `-Xmx6g` in that file. Then run `killrepl` and
`startrepl`, because a running REPL keeps its old limit. Tell the user you
raised it.
