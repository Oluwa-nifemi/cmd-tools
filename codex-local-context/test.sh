#!/bin/sh
set -eu

tool_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
hook=$tool_dir/codex-local-context
hooks_config=$tool_dir/hooks.json
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT

repo=$tmp/repo
mkdir -p "$repo/nested/path"
git -C "$repo" init -q

grep -q '"matcher": "startup|clear|compact"' "$hooks_config"
if grep -q '"matcher":.*resume' "$hooks_config"; then
  echo "resume must not reinject local context" >&2
  exit 1
fi

output=$(printf '{"cwd":"%s"}\n' "$repo" | "$hook")
[ -z "$output" ] || { echo "expected no output without AGENTS.local.md" >&2; exit 1; }

printf 'Local instruction.\nSecond line.\n' > "$repo/AGENTS.local.md"
output=$(printf '{"cwd":"%s"}\n' "$repo/nested/path" | "$hook")
expected='Local instructions from the repository root AGENTS.local.md:

Local instruction.
Second line.'
[ "$output" = "$expected" ] || {
  printf 'unexpected output:\n%s\n' "$output" >&2
  exit 1
}

echo "codex-local-context: tests passed"
