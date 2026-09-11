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

echo 'repl-tools tests passed'
