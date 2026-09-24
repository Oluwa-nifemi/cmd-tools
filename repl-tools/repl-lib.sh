#!/bin/sh

set -eu

REPL_CACHE_DIR="${HOME}/.cache/zed-clojure-repl"
REPL_REGISTRY="${REPL_CACHE_DIR}/registry.json"
REPL_LOCK_DIR="${REPL_CACHE_DIR}/locks"
REPL_START_TIMEOUT=120
REPL_EVAL_TIMEOUT=10
# How long a caller waits on another process's startup lock before failing,
# and how long an ownerless lock (starter died before writing its PID) may
# exist before we treat it as abandoned.
REPL_LOCK_WAIT_TIMEOUT="${ZED_CLOJURE_REPL_LOCK_WAIT_SECONDS:-$REPL_START_TIMEOUT}"
REPL_EMPTY_LOCK_GRACE="${ZED_CLOJURE_REPL_EMPTY_LOCK_GRACE_SECONDS:-2}"
REPL_MAX="${ZED_CLOJURE_MAX_REPLS:-3}"
REPL_IDLE_TIMEOUT="${ZED_CLOJURE_REPL_IDLE_SECONDS:-86400}"

# Stops REPLs that should no longer hold memory: the worktree folder is gone,
# or it has been idle past REPL_IDLE_TIMEOUT. Dead entries are dropped. With
# MODE=reserve it also evicts least-recently-used REPLs until one more fits
# under REPL_MAX, matching enforce_limit in the editor. A REPL serving an app
# on a non-loopback port is never stopped for idleness or the cap, and KEEP
# (the worktree being used right now) is never stopped for idleness.
prune_registry() {
    python3 - "$REPL_REGISTRY" "${1:-prune}" "${2:-}" "$REPL_MAX" "$REPL_IDLE_TIMEOUT" <<'PY'
import json
import os
import signal
import socket
import subprocess
import sys
import time

path, mode, keep, max_repls, idle_timeout = sys.argv[1:]
try:
    max_repls = max(int(max_repls), 1)
except ValueError:
    max_repls = 3
idle_timeout = int(idle_timeout)

try:
    with open(path) as handle:
        registry = json.load(handle)
except FileNotFoundError:
    raise SystemExit(0)
except (OSError, json.JSONDecodeError) as error:
    print(f"repl-tools: cannot read nREPL registry: {error}", file=sys.stderr)
    raise SystemExit(0)

entries = registry.get("worktrees", {})
hook = os.path.expanduser("~/.config/zed-clojure/on-repl-evicted")


def port_answers(port):
    try:
        with socket.create_connection(("127.0.0.1", int(port)), 0.25):
            return True
    except ConnectionRefusedError:
        return False
    except OSError:
        return True


def alive(entry):
    try:
        os.kill(int(entry["pid"]), 0)
    except (KeyError, OSError, TypeError, ValueError):
        return False
    return port_answers(entry.get("port", 0))


def serves_app(entry):
    # nREPL binds loopback; a dev system's HTTP server binds all interfaces.
    try:
        output = subprocess.run(
            ["lsof", "-nP", "-a", "-g", str(os.getpgid(int(entry["pid"]))),
             "-iTCP", "-sTCP:LISTEN", "-Fn"],
            capture_output=True, text=True, timeout=5,
        ).stdout
    except (OSError, subprocess.SubprocessError, ValueError):
        return True
    names = [line[1:] for line in output.splitlines() if line.startswith("n")]
    return any(not name.startswith(("127.0.0.1:", "[::1]:", "localhost:")) for name in names)


def stop(worktree, entry, reason):
    pid = int(entry["pid"])
    try:
        group = os.getpgid(pid)
        os.killpg(group, signal.SIGTERM)
        for _ in range(20):
            time.sleep(0.1)
            os.killpg(group, 0)
        os.killpg(group, signal.SIGKILL)
    except (ProcessLookupError, PermissionError):
        pass
    try:
        os.remove(os.path.join(worktree, ".nrepl-port"))
    except OSError:
        pass
    name = worktree.rstrip("/").rsplit("/", 1)[-1]
    print(f"stopped REPL for {name} (pid {pid}): {reason}", file=sys.stderr)
    if os.access(hook, os.X_OK):
        subprocess.Popen([hook, "evicted", worktree], stdin=subprocess.DEVNULL,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                         start_new_session=True)


now = time.time()
live = {}
for worktree, entry in entries.items():
    if not alive(entry):
        continue
    if not os.path.isdir(worktree):
        stop(worktree, entry, "worktree folder was deleted")
        continue
    idle = now - entry.get("last_used_at", 0)
    if worktree != keep and idle > idle_timeout and not serves_app(entry):
        stop(worktree, entry, f"idle for {int(idle // 3600)}h")
        continue
    live[worktree] = entry

if mode == "reserve":
    candidates = sorted(
        (item for item in live.items() if item[0] != keep and not serves_app(item[1])),
        key=lambda item: item[1].get("last_used_at", 0),
    )
    while len(live) >= max_repls and candidates:
        worktree, entry = candidates.pop(0)
        stop(worktree, entry, f"at the {max_repls}-REPL limit, least recently used")
        del live[worktree]

if live != entries:
    registry["worktrees"] = live
    with open(path, "w") as handle:
        json.dump(registry, handle, indent=2)
        handle.write("\n")
PY
}

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

remove_lock() {
    rm -f "$1/pid" "$1/child_pid"
    rmdir "$1" 2>/dev/null || true
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
        # Leiningen can keep its launcher alive after the project JVM fails.
        # Detect that child failure instead of waiting for the full timeout.
        if grep -q 'Subprocess failed (exit code:' "$log_path" 2>/dev/null; then
            return 2
        fi
        # The launcher writes this line when the project command exits. Its
        # `tail` stays alive, so the process group alone never shows the exit.
        if grep -q '^zed-nrepl: REPL process exited' "$log_path" 2>/dev/null; then
            return 3
        fi
        sleep 1
        elapsed=$((elapsed + 1))
    done
    return 1
}

stop_repl_process() {
    pid="$1"
    # The launcher creates a new session, so its PID is also its process-group
    # ID. Kill the group to avoid leaving Leiningen and its children behind.
    kill -TERM "-$pid" 2>/dev/null || kill -TERM "$pid" 2>/dev/null || true
}

print_startup_failure() {
    log_path="$1"
    grep -E 'Exception in thread|Syntax error|Caused by:|Subprocess failed' "$log_path" 2>/dev/null | tail -n 12 >&2 || true
}

repl_accepts_evaluation() {
    port="$1"
    timeout="$2"
    # A TCP listener is not sufficient proof of readiness. Bound the probe so
    # a temporary or wedged nREPL cannot block startrepl indefinitely.
    python3 - "$port" "$timeout" <<'PY'
import subprocess
import sys

try:
    result = subprocess.run(
        ["clj-nrepl-eval", "-p", sys.argv[1], "nil"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        timeout=int(sys.argv[2]),
    )
except (OSError, subprocess.TimeoutExpired):
    raise SystemExit(1)
raise SystemExit(result.returncode)
PY
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
    prune_registry prune "$root"
    existing_port="$(registry_port "$root")"
    if [ -n "$existing_port" ]; then
        printf '%s\n' "$existing_port"
        return 0
    fi

    lock_path="$(lock_path_for "$root")"
    mkdir -p "$REPL_LOCK_DIR"
    announced_wait=false
    wait_started="$(date +%s)"
    ownerless_since=
    while ! mkdir "$lock_path" 2>/dev/null; do
        now="$(date +%s)"
        lock_pid="$(cat "$lock_path/pid" 2>/dev/null || true)"
        if [ -n "$lock_pid" ] && ! kill -0 "$lock_pid" 2>/dev/null; then
            remove_lock "$lock_path"
            continue
        fi
        # The owner writes its PID right after mkdir. A lock that stays empty
        # past the grace period belongs to a starter that died in between.
        # rmdir only succeeds on an empty directory, so a late PID write wins.
        if [ -z "$lock_pid" ]; then
            ownerless_since="${ownerless_since:-$now}"
            if [ $((now - ownerless_since)) -ge "$REPL_EMPTY_LOCK_GRACE" ]; then
                rmdir "$lock_path" 2>/dev/null || true
                ownerless_since=
                continue
            fi
        else
            ownerless_since=
        fi
        # A live owner may be a slow but valid startup in another terminal, so
        # never kill it here. Fail with enough detail to run killrepl instead.
        if [ $((now - wait_started)) -ge "$REPL_LOCK_WAIT_TIMEOUT" ]; then
            echo "runrepl: timed out after ${REPL_LOCK_WAIT_TIMEOUT}s waiting for REPL startup lock for $root; lock=$lock_path owner-pid=${lock_pid:-unknown}. Run 'killrepl --force' to stop that startup." >&2
            return 1
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
        remove_lock "$lock_path"
    }
    trap cleanup_lock EXIT HUP INT TERM
    printf '%s\n' "$$" > "$lock_path/pid"

    existing_port="$(registry_port "$root")"
    if [ -n "$existing_port" ]; then
        printf '%s\n' "$existing_port"
        return 0
    fi

    # A hard shutdown leaves Leiningen's discovery file behind. It names the
    # previous JVM's port, so reading it during this launch can race the new
    # JVM and make us evaluate a server that no longer exists. The registry
    # check above proved no live REPL owns this worktree, so this file is stale.
    rm -f "$root/.nrepl-port"
    prune_registry reserve "$root"

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
        "tail -f /dev/null | { \"$@\" >> \"$ZED_NREPL_LOG\" 2>&1; echo \"zed-nrepl: REPL process exited with status $?\" >> \"$ZED_NREPL_LOG\"; }",
        "zed-nrepl",
        *sys.argv[1:],
    ],
    os.environ,
)
' "$program" "$@"
    ) >/dev/null 2>&1 &
    pid=$!
    # killrepl --force reads this to stop a startup that has no registry entry.
    printf '%s\n' "$pid" > "$lock_path/child_pid"

    wait_status=0
    port="$(wait_for_port "$root" "$log_path")" || wait_status=$?
    if [ "$wait_status" -ne 0 ]; then
        stop_repl_process "$pid"
        if [ "$wait_status" -eq 2 ]; then
            echo "runrepl: project failed while starting nREPL in $root" >&2
            print_startup_failure "$log_path"
        elif [ "$wait_status" -eq 3 ]; then
            echo "runrepl: REPL process exited before nREPL started in $root; see $log_path" >&2
            tail -n 12 "$log_path" >&2
        else
            echo "runrepl: timed out waiting for nREPL in $root after ${REPL_START_TIMEOUT}s; see $log_path" >&2
        fi
        return 1
    fi

    if ! repl_accepts_evaluation "$port" "$REPL_EVAL_TIMEOUT"; then
        stop_repl_process "$pid"
        if grep -q 'Subprocess failed (exit code:' "$log_path" 2>/dev/null; then
            echo "runrepl: project failed while starting nREPL in $root" >&2
            print_startup_failure "$log_path"
        else
            echo "runrepl: nREPL on port $port did not accept an evaluation within ${REPL_EVAL_TIMEOUT}s; see $log_path" >&2
        fi
        return 1
    fi

    register_repl "$root" "$pid" "$port" "$log_path" "$program" "$@"
    printf '%s\n' "$port"
}
