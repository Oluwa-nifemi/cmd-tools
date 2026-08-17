#!/bin/sh

set -eu

REPL_CACHE_DIR="${HOME}/.cache/zed-clojure-repl"
REPL_REGISTRY="${REPL_CACHE_DIR}/registry.json"
REPL_LOCK_DIR="${REPL_CACHE_DIR}/locks"
REPL_START_TIMEOUT=120

resolve_project_root() {
    root="$(git rev-parse --show-toplevel 2>/dev/null || true)"
    if [ -n "$root" ]; then
        printf '%s\n' "$root"
        return
    fi

    current="$(pwd)"
    while [ "$current" != "/" ]; do
        for marker in project.clj deps.edn bb.edn shadow-cljs.edn build.clj; do
            if [ -f "$current/$marker" ]; then
                printf '%s\n' "$current"
                return
            fi
        done
        current="$(dirname "$current")"
    done
}

require_project_root() {
    root="$(resolve_project_root)"
    if [ -z "$root" ]; then
        echo "No Git or Clojure project root found from $(pwd)." >&2
        exit 1
    fi
    printf '%s\n' "$root"
}

# Absolute worktree path of the registered REPL whose process group holds
# APP_PORT, or empty. The registry stores the shell wrapper pid; the JVM that
# binds the port is its child in the same process group, so compare groups.
registry_worktree_for_app_port() {
    python3 - "$REPL_REGISTRY" "$1" <<'PY'
import json
import os
import subprocess
import sys

path, app_port = sys.argv[1:]
try:
    with open(path) as handle:
        registry = json.load(handle)
except (OSError, json.JSONDecodeError):
    raise SystemExit(0)


def pgid(pid):
    try:
        return subprocess.run(
            ["ps", "-o", "pgid=", "-p", str(pid)],
            capture_output=True,
            text=True,
            timeout=5,
        ).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return ""


try:
    listing = subprocess.run(
        ["lsof", "-nP", f"-iTCP:{app_port}", "-sTCP:LISTEN"],
        capture_output=True,
        text=True,
        timeout=5,
    ).stdout.splitlines()[1:]
except (OSError, subprocess.SubprocessError):
    raise SystemExit(0)

holders = set()
for row in listing:
    parts = row.split()
    if len(parts) > 1 and parts[1].isdigit():
        group = pgid(parts[1])
        if group:
            holders.add(group)

for worktree, entry in registry.get("worktrees", {}).items():
    pid = entry.get("pid")
    if pid is None:
        continue
    try:
        os.kill(int(pid), 0)
    except OSError:
        continue
    if pgid(pid) in holders:
        print(worktree)
        break
PY
}

registry_port() {
    python3 - "$REPL_REGISTRY" "$1" <<'PY'
import json
import os
import sys

path, root = sys.argv[1:]
try:
    with open(path) as handle:
        registry = json.load(handle)
except FileNotFoundError:
    registry = {"worktrees": {}}
except (OSError, json.JSONDecodeError) as error:
    print(f"runrepl: cannot read nREPL registry: {error}", file=sys.stderr)
    raise SystemExit(2)

entries = registry.get("worktrees", {})
def port_answers(port):
    # A live process with a dead port is a phantom: it keeps its registry slot
    # and can never be reached. Check both, cheaply.
    import socket
    try:
        with socket.create_connection(("127.0.0.1", int(port)), 0.25):
            return True
    except ConnectionRefusedError:
        return False
    except OSError:
        return True


live = {}
for worktree, entry in entries.items():
    try:
        os.kill(int(entry["pid"]), 0)
        if not port_answers(entry.get("port", 0)):
            continue
    except (KeyError, OSError, TypeError, ValueError):
        continue
    live[worktree] = entry

if live != entries:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as handle:
        json.dump({"worktrees": live}, handle, indent=2)
        handle.write("\n")

entry = live.get(root)
if entry:
    try:
        print(int(entry["port"]))
    except (KeyError, TypeError, ValueError):
        print(f"runrepl: registry entry for {root} has no valid port", file=sys.stderr)
        raise SystemExit(2)
PY
}

touch_registry_entry() {
    python3 - "$REPL_REGISTRY" "$1" <<'PY'
import json
import sys
import time

path, root = sys.argv[1:]
try:
    with open(path) as handle:
        registry = json.load(handle)
except FileNotFoundError:
    raise SystemExit

entry = registry.get("worktrees", {}).get(root)
if entry:
    entry["last_used_at"] = int(time.time())
    with open(path, "w") as handle:
        json.dump(registry, handle, indent=2)
        handle.write("\n")
PY
}

project_command() {
    root="$1"
    if [ -f "$root/project.clj" ]; then
        printf '%s\n' lein repl
    elif [ -f "$root/deps.edn" ]; then
        printf '%s\n' clojure -M:dev:nrepl
    elif [ -f "$root/bb.edn" ]; then
        printf '%s\n' bb nrepl-server
    elif [ -f "$root/shadow-cljs.edn" ]; then
        printf '%s\n' npx shadow-cljs server
    else
        printf '%s\n' lein repl
    fi
}

log_path_for() {
    python3 - "$REPL_CACHE_DIR" "$1" <<'PY'
import os
import sys

cache_dir, worktree = sys.argv[1:]
sanitized = "".join(character if character.isascii() and character.isalnum() else "_" for character in worktree)
print(os.path.join(cache_dir, "logs", f"{sanitized}.log"))
PY
}

lock_path_for() {
    python3 - "$REPL_LOCK_DIR" "$1" <<'PY'
import os
import sys

lock_dir, worktree = sys.argv[1:]
sanitized = "".join(character if character.isascii() and character.isalnum() else "_" for character in worktree)
print(os.path.join(lock_dir, f"{sanitized}.lock"))
PY
}

wait_for_port() {
    root="$1"
    log_path="$2"
    elapsed=0
    while [ "$elapsed" -lt "$REPL_START_TIMEOUT" ]; do
        port="$(python3 - "$root" "$log_path" <<'PY'
import os
import re
import sys

root, log_path = sys.argv[1:]
port_path = os.path.join(root, ".nrepl-port")
try:
    with open(port_path) as handle:
        port = int(handle.read().strip())
        if 0 < port <= 65535:
            print(port)
            raise SystemExit
except (OSError, ValueError):
    pass

try:
    with open(log_path) as handle:
        for line in handle:
            match = re.match(r"nREPL server started on port ([0-9]+)", line)
            if match:
                print(match.group(1))
                raise SystemExit
except OSError:
    pass
PY
)"
        if [ -n "$port" ]; then
            printf '%s\n' "$port"
            return 0
        fi
        sleep 1
        elapsed=$((elapsed + 1))
    done
    return 1
}

register_repl() {
    root="$1"
    pid="$2"
    port="$3"
    log_path="$4"
    shift 4
    python3 - "$REPL_REGISTRY" "$root" "$pid" "$port" "$log_path" "$@" <<'PY'
import json
import os
import sys
import time

path, root, pid, port, log_path, *project_cmd = sys.argv[1:]
try:
    with open(path) as handle:
        registry = json.load(handle)
except FileNotFoundError:
    registry = {"worktrees": {}}

timestamp = int(time.time())
registry.setdefault("worktrees", {})[root] = {
    "pid": int(pid),
    "port": int(port),
    "log_path": log_path,
    "started_at": timestamp,
    "last_used_at": timestamp,
    "project_cmd": project_cmd,
}
os.makedirs(os.path.dirname(path), exist_ok=True)
with open(path, "w") as handle:
    json.dump(registry, handle, indent=2)
    handle.write("\n")
PY
}

# Resolve a 1-based index from the `repls` listing to an absolute worktree
# path. The ordering mirrors `repls`: live entries sorted by last_used_at
# descending, so index 1 is always the most-recently-used REPL.
resolve_worktree_by_index() {
    python3 - "$REPL_REGISTRY" "$1" <<'PY'
import json
import os
import socket
import sys

path, index_str = sys.argv[1:]
try:
    index = int(index_str)
except ValueError:
    print(f"killrepl: '{index_str}' is not a number", file=sys.stderr)
    raise SystemExit(1)

try:
    with open(path) as handle:
        registry = json.load(handle)
except FileNotFoundError:
    print("No REPLs running.", file=sys.stderr)
    raise SystemExit(1)
except (OSError, json.JSONDecodeError) as error:
    print(f"Cannot read registry: {error}", file=sys.stderr)
    raise SystemExit(1)

def port_answers(port):
    try:
        with socket.create_connection(("127.0.0.1", int(port)), 0.25):
            return True
    except ConnectionRefusedError:
        return False
    except OSError:
        return True

entries = registry.get("worktrees", {})
live = {}
for worktree, entry in entries.items():
    try:
        os.kill(int(entry["pid"]), 0)
        if not port_answers(entry.get("port", 0)):
            continue
    except (KeyError, OSError, TypeError, ValueError):
        continue
    live[worktree] = entry

if not live:
    print("No REPLs running.", file=sys.stderr)
    raise SystemExit(1)

ordered = sorted(live.items(), key=lambda item: -item[1]["last_used_at"])
if index < 1 or index > len(ordered):
    print(f"No REPL at index {index}. {len(ordered)} running.", file=sys.stderr)
    raise SystemExit(1)

print(ordered[index - 1][0])
PY
}

start_repl() {
    root="$1"
    existing_port="$(registry_port "$root")"
    if [ -n "$existing_port" ]; then
        printf '%s\n' "$existing_port"
        return 0
    fi

    lock_path="$(lock_path_for "$root")"
    mkdir -p "$REPL_LOCK_DIR"
    announced_wait=false
    while ! mkdir "$lock_path" 2>/dev/null; do
        lock_pid="$(cat "$lock_path/pid" 2>/dev/null || true)"
        if [ -n "$lock_pid" ] && ! kill -0 "$lock_pid" 2>/dev/null; then
            rm -f "$lock_path/pid"
            rmdir "$lock_path" 2>/dev/null || true
            continue
        fi
        if [ "$announced_wait" = false ]; then
            echo "waiting for another process to start REPL for $(basename "$root")" >&2
            announced_wait=true
        fi
        sleep 1
        existing_port="$(registry_port "$root")"
        if [ -n "$existing_port" ]; then
            printf '%s\n' "$existing_port"
            return 0
        fi
    done

    cleanup_lock() {
        rm -f "$lock_path/pid"
        rmdir "$lock_path" 2>/dev/null || true
    }
    trap cleanup_lock EXIT HUP INT TERM
    printf '%s\n' "$$" > "$lock_path/pid"

    existing_port="$(registry_port "$root")"
    if [ -n "$existing_port" ]; then
        printf '%s\n' "$existing_port"
        return 0
    fi

    set -- $(project_command "$root")
    program="$1"
    shift
    log_path="$(log_path_for "$root")"
    mkdir -p "$(dirname "$log_path")"
    : > "$log_path"

    echo "starting REPL for $(basename "$root"), ~40s" >&2
    (
        cd "$root"
        exec env ZED_NREPL_LOG="$log_path" python3 -c '
import os
import sys
os.setsid()
os.execvpe(
    "sh",
    [
        "sh",
        "-c",
        "tail -f /dev/null | exec \"$@\" >> \"$ZED_NREPL_LOG\" 2>&1",
        "zed-nrepl",
        *sys.argv[1:],
    ],
    os.environ,
)
' "$program" "$@"
    ) >/dev/null 2>&1 &
    pid=$!

    if ! port="$(wait_for_port "$root" "$log_path")"; then
        echo "runrepl: timed out waiting for nREPL in $root; see $log_path" >&2
        return 1
    fi

    if ! clj-nrepl-eval -p "$port" "nil" >/dev/null; then
        echo "runrepl: nREPL on port $port did not accept an evaluation; see $log_path" >&2
        return 1
    fi

    register_repl "$root" "$pid" "$port" "$log_path" "$program" "$@"
    printf '%s\n' "$port"
}
