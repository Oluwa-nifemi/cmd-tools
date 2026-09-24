#!/bin/sh

set -eu

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
TEST_DIR="$(mktemp -d)"
trap 'rm -rf "$TEST_DIR"' EXIT HUP INT TERM

# A hard shutdown can leave .nrepl-port behind after its JVM is gone. Startup
# must discard it and use the port reported by the REPL it just launched.
root="$TEST_DIR/project"
bin="$TEST_DIR/bin"
mkdir -p "$root" "$bin"
touch "$root/project.clj"
printf '%s\n' 49380 > "$root/.nrepl-port"

cat > "$bin/lein" <<'EOF'
#!/bin/sh
printf '%s\n' 'nREPL server started on port 52821 on host 127.0.0.1' >> "$ZED_NREPL_LOG"
exec sleep 60
EOF

cat > "$bin/clj-nrepl-eval" <<'EOF'
#!/bin/sh
[ "$1" = -p ]
[ "$2" = 52821 ]
EOF

chmod +x "$bin/lein" "$bin/clj-nrepl-eval"
HOME="$TEST_DIR/home"
PATH="$bin:$PATH"
export HOME PATH
. "$SCRIPT_DIR/repl-lib.sh"

actual="$(start_repl "$root")"
[ "$actual" = 52821 ]
[ ! -f "$root/.nrepl-port" ]

pid="$(python3 - "$REPL_REGISTRY" "$root" <<'PY'
import json
import sys

path, root = sys.argv[1:]
with open(path) as handle:
    print(json.load(handle)["worktrees"][root]["pid"])
PY
)"
python3 - "$pid" <<'PY'
import os
import signal
import sys

os.killpg(os.getpgid(int(sys.argv[1])), signal.SIGTERM)
PY

# Leiningen can leave its launcher waiting forever when the project JVM fails
# before acknowledging startup. The wrapper must fail quickly and clean up the
# whole process group instead of leaving an orphan for every retry.
failed_root="$TEST_DIR/failed-project"
mkdir -p "$failed_root"
touch "$failed_root/project.clj"
cat > "$bin/lein" <<'EOF'
#!/bin/sh
printf '%s\n' "$$" > failed.pid
printf '%s\n' 'nREPL server started on port 53111 on host 127.0.0.1' >> "$ZED_NREPL_LOG"
printf '%s\n' 'Exception in thread "main" Syntax error compiling at (example.clj:1:1).' >> "$ZED_NREPL_LOG"
printf '%s\n' 'Caused by: java.lang.RuntimeException: No such var: example/missing' >> "$ZED_NREPL_LOG"
printf '%s\n' 'Subprocess failed (exit code: 1)' >> "$ZED_NREPL_LOG"
exec sleep 60
EOF
cat > "$bin/clj-nrepl-eval" <<'EOF'
#!/bin/sh
if [ "$2" = 53111 ]; then
    exec sleep 60
fi
[ "$2" = 52821 ]
EOF
chmod +x "$bin/clj-nrepl-eval"
REPL_START_TIMEOUT=5
REPL_EVAL_TIMEOUT=1
start_time="$(date +%s)"
if start_repl "$failed_root" >"$TEST_DIR/failed.out" 2>"$TEST_DIR/failed.err"; then
    echo 'expected failed startup to return non-zero' >&2
    exit 1
fi
elapsed=$(( $(date +%s) - start_time ))
[ "$elapsed" -lt "$REPL_START_TIMEOUT" ]
grep -q 'project failed while starting nREPL' "$TEST_DIR/failed.err"
grep -q 'No such var: example/missing' "$TEST_DIR/failed.err"
failed_pid="$(cat "$failed_root/failed.pid")"
if kill -0 "$failed_pid" 2>/dev/null; then
    echo 'failed startup left a process behind' >&2
    exit 1
fi

# Registry pruning. Each fake REPL is a session leader listening on a port, so
# it passes the same liveness check as a real one.
spawn_listener() {
    python3 - "$1" <<'PY'
import subprocess
import sys

code = '''
import socket, sys, time
s = socket.socket()
s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
s.bind((sys.argv[1], 0))
s.listen()
print(s.getsockname()[1], flush=True)
time.sleep(120)
'''
process = subprocess.Popen(
    [sys.executable, "-c", code, sys.argv[1]],
    stdout=subprocess.PIPE,
    stdin=subprocess.DEVNULL,
    start_new_session=True,
    text=True,
)
print(process.pid, process.stdout.readline().strip())
PY
}

write_entry() {
    python3 - "$REPL_REGISTRY" "$@" <<'PY'
import json
import os
import sys
import time

path, root, pid, port, idle_seconds = sys.argv[1:]
try:
    with open(path) as handle:
        registry = json.load(handle)
except FileNotFoundError:
    registry = {"worktrees": {}}
used = int(time.time()) - int(idle_seconds)
registry.setdefault("worktrees", {})[root] = {
    "pid": int(pid),
    "port": int(port),
    "log_path": "/dev/null",
    "started_at": used,
    "last_used_at": used,
    "project_cmd": ["lein", "repl"],
}
os.makedirs(os.path.dirname(path), exist_ok=True)
with open(path, "w") as handle:
    json.dump(registry, handle)
PY
}

registered() {
    python3 - "$REPL_REGISTRY" "$1" <<'PY'
import json
import sys

path, root = sys.argv[1:]
with open(path) as handle:
    raise SystemExit(0 if root in json.load(handle)["worktrees"] else 1)
PY
}

expect_dead() {
    for _ in 1 2 3 4 5 6 7 8 9 10; do
        kill -0 "$1" 2>/dev/null || return 0
        sleep 0.3
    done
    echo "expected pid $1 to be stopped: $2" >&2
    exit 1
}

expect_alive() {
    if ! kill -0 "$1" 2>/dev/null; then
        echo "expected pid $1 to keep running: $2" >&2
        exit 1
    fi
}

rm -f "$REPL_REGISTRY"
gone_root="$TEST_DIR/deleted-worktree"
idle_root="$TEST_DIR/idle"
app_root="$TEST_DIR/serving-app"
fresh_root="$TEST_DIR/fresh"
mkdir -p "$idle_root" "$app_root" "$fresh_root"
set -- $(spawn_listener 127.0.0.1); gone_pid=$1; write_entry "$gone_root" "$1" "$2" 0
set -- $(spawn_listener 127.0.0.1); idle_pid=$1; write_entry "$idle_root" "$1" "$2" 200000
set -- $(spawn_listener 0.0.0.0); app_pid=$1; write_entry "$app_root" "$1" "$2" 200000
set -- $(spawn_listener 127.0.0.1); fresh_pid=$1; write_entry "$fresh_root" "$1" "$2" 0

prune_registry
expect_dead "$gone_pid" 'its worktree folder was deleted'
! registered "$gone_root"
expect_dead "$idle_pid" 'it was idle past the timeout'
! registered "$idle_root"
expect_alive "$app_pid" 'it serves an app on a non-loopback port'
registered "$app_root"
expect_alive "$fresh_pid" 'it was used recently'
registered "$fresh_root"

# Starting a REPL from the CLI must respect the cap. It evicts the least
# recently used REPL, but never one serving an app.
older_root="$TEST_DIR/older"
mkdir -p "$older_root"
set -- $(spawn_listener 127.0.0.1); older_pid=$1; write_entry "$older_root" "$1" "$2" 600
cat > "$bin/lein" <<'EOF'
#!/bin/sh
printf '%s\n' 'nREPL server started on port 52821 on host 127.0.0.1' >> "$ZED_NREPL_LOG"
exec sleep 60
EOF
cat > "$bin/clj-nrepl-eval" <<'EOF'
#!/bin/sh
[ "$2" = 52821 ]
EOF
REPL_MAX=3
REPL_START_TIMEOUT=10
capped_root="$TEST_DIR/capped"
mkdir -p "$capped_root"
touch "$capped_root/project.clj"
start_repl "$capped_root" >"$TEST_DIR/capped.out" 2>"$TEST_DIR/capped.err" || { cat "$TEST_DIR/capped.err" >&2; exit 1; }
expect_dead "$older_pid" 'it was the least recently used REPL at the cap'
! registered "$older_root"
expect_alive "$app_pid" 'the cap must not evict a REPL serving an app'
expect_alive "$fresh_pid" 'the cap should evict only one REPL'
registered "$capped_root"
for pid in "$app_pid" "$fresh_pid"; do kill -TERM "-$pid" 2>/dev/null || true; done
python3 - "$REPL_REGISTRY" "$capped_root" <<'PY'
import json
import os
import signal
import sys

path, root = sys.argv[1:]
with open(path) as handle:
    os.killpg(int(json.load(handle)["worktrees"][root]["pid"]), signal.SIGTERM)
PY

# Startup lock recovery. The lock is a directory holding the starter's PID.
# Each case must finish in a few seconds; before the fix, an ownerless lock or a
# stuck owner made start_repl wait forever.
stop_registered() {
    python3 - "$REPL_REGISTRY" "$1" <<'PY'
import json
import os
import signal
import sys

path, root = sys.argv[1:]
with open(path) as handle:
    os.killpg(int(json.load(handle)["worktrees"][root]["pid"]), signal.SIGTERM)
PY
}

lock_root() {
    mkdir -p "$TEST_DIR/$1"
    touch "$TEST_DIR/$1/project.clj"
    lock="$(lock_path_for "$TEST_DIR/$1")"
    mkdir -p "$lock"
}

REPL_EMPTY_LOCK_GRACE=1
REPL_LOCK_WAIT_TIMEOUT=10

# The starter can die between creating the lock and writing its PID.
lock_root ownerless
[ "$(start_repl "$TEST_DIR/ownerless" 2>"$TEST_DIR/ownerless.err")" = 52821 ] || { cat "$TEST_DIR/ownerless.err" >&2; exit 1; }
[ ! -d "$lock" ]
stop_registered "$TEST_DIR/ownerless"

lock_root dead-owner
sh -c 'exit 0' & dead_pid=$!; wait "$dead_pid"
printf '%s\n' "$dead_pid" > "$lock/pid"
[ "$(start_repl "$TEST_DIR/dead-owner" 2>"$TEST_DIR/dead-owner.err")" = 52821 ] || { cat "$TEST_DIR/dead-owner.err" >&2; exit 1; }
[ ! -d "$lock" ]
stop_registered "$TEST_DIR/dead-owner"

# A live owner may be a slow but valid startup in another terminal. Fail with a
# clear error after the deadline and leave the owner running.
lock_root stuck-owner
sleep 60 & owner_pid=$!
printf '%s\n' "$owner_pid" > "$lock/pid"
REPL_LOCK_WAIT_TIMEOUT=2
start_time="$(date +%s)"
if start_repl "$TEST_DIR/stuck-owner" >/dev/null 2>"$TEST_DIR/stuck-owner.err"; then
    echo 'expected a live stuck lock owner to time out' >&2
    exit 1
fi
[ $(( $(date +%s) - start_time )) -le 4 ]
grep -qF "$TEST_DIR/stuck-owner;" "$TEST_DIR/stuck-owner.err"
grep -qF "lock=$lock owner-pid=$owner_pid" "$TEST_DIR/stuck-owner.err"
expect_alive "$owner_pid" 'another caller must not kill a live lock owner'

# A second caller reuses the REPL the lock owner registers.
lock_root concurrent
printf '%s\n' "$owner_pid" > "$lock/pid"
REPL_LOCK_WAIT_TIMEOUT=10
set -- $(spawn_listener 127.0.0.1); concurrent_pid=$1; concurrent_port=$2
( sleep 1; write_entry "$TEST_DIR/concurrent" "$concurrent_pid" "$concurrent_port" 0 ) &
[ "$(start_repl "$TEST_DIR/concurrent" 2>"$TEST_DIR/concurrent.err")" = "$concurrent_port" ] || { cat "$TEST_DIR/concurrent.err" >&2; exit 1; }
kill "$owner_pid" 2>/dev/null || true
kill -TERM "-$concurrent_pid" 2>/dev/null || true
rm -rf "$lock"

# A REPL process that exits without Leiningen's failure line must fail the
# start at once, not hold the lock for the full startup timeout.
cat > "$bin/lein" <<'EOF'
#!/bin/sh
exit 1
EOF
lock_root child-exits
rmdir "$lock"
start_time="$(date +%s)"
# Run in a subshell like runrepl's $(start_repl) so the EXIT trap clears the lock.
if (start_repl "$TEST_DIR/child-exits") >/dev/null 2>"$TEST_DIR/child-exits.err"; then
    echo 'expected startup to fail when the REPL process exits' >&2
    exit 1
fi
[ $(( $(date +%s) - start_time )) -lt 5 ]
grep -q 'REPL process exited' "$TEST_DIR/child-exits.err"
[ ! -d "$lock" ]

# killrepl must handle startup state that has a lock but no registry entry.
# Without --force it reports the owner. With --force it stops the owner and
# its REPL process group and clears the lock.
lock_root lock-only
sleep 60 & owner_pid=$!
set -- $(spawn_listener 127.0.0.1); child_pid=$1
printf '%s\n' "$owner_pid" > "$lock/pid"
printf '%s\n' "$child_pid" > "$lock/child_pid"
if (cd "$TEST_DIR/lock-only" && "$SCRIPT_DIR/killrepl") >/dev/null 2>"$TEST_DIR/lock-only.err"; then
    echo 'expected killrepl without --force to leave a live startup alone' >&2
    exit 1
fi
grep -qF "lock=$lock" "$TEST_DIR/lock-only.err"
grep -qF "owner-pid=$owner_pid" "$TEST_DIR/lock-only.err"
grep -qF 'killrepl --force' "$TEST_DIR/lock-only.err"
expect_alive "$owner_pid" 'killrepl without --force must not stop a startup'
(cd "$TEST_DIR/lock-only" && "$SCRIPT_DIR/killrepl" --force) >/dev/null 2>&1
expect_dead "$owner_pid" 'killrepl --force stops the lock owner'
expect_dead "$child_pid" 'killrepl --force stops the REPL process group'
[ ! -d "$lock" ]

lock_root dead-lock-only
printf '%s\n' "$dead_pid" > "$lock/pid"
(cd "$TEST_DIR/dead-lock-only" && "$SCRIPT_DIR/killrepl") >/dev/null 2>&1
[ ! -d "$lock" ]

echo 'repl-tools tests passed'
