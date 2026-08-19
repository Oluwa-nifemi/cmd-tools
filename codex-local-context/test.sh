#!/bin/sh
set -eu

tool_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
hook=$tool_dir/codex-local-context
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT

repo=$tmp/repo
mkdir -p "$repo/nested/path"
git -C "$repo" init -q

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
