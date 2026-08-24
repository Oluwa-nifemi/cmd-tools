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

echo 'repl-tools tests passed'
