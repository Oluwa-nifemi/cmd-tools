#!/usr/bin/env bash

set -uo pipefail

TEST_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
GS="$(cd "$TEST_DIR/.." && pwd -P)/gs"
REAL_GIT="$(command -v git)"
PASS=0
FAIL=0

export GIT_CONFIG_GLOBAL=/dev/null
export GIT_CONFIG_NOSYSTEM=1
export GIT_AUTHOR_NAME="GS Test"
export GIT_AUTHOR_EMAIL="gs-test@example.com"
export GIT_COMMITTER_NAME="GS Test"
export GIT_COMMITTER_EMAIL="gs-test@example.com"
export GIT_EDITOR=true
export GIT_SEQUENCE_EDITOR=true

fail() {
  echo "    $*" >&2
  return 1
}

assert_eq() {
  [[ "$1" == "$2" ]] || fail "expected '$2', got '$1'"
}

assert_contains() {
  case "$1" in
    *"$2"*) ;;
    *) fail "expected output to contain: $2" ;;
  esac
}

assert_file() {
  [[ -f "$1" ]] || fail "expected file: $1"
}

assert_no_file() {
  [[ ! -e "$1" ]] || fail "unexpected path: $1"
}

assert_dir_eq() {
  diff -qr "$1" "$2" >/dev/null 2>&1 || fail "directories differ: $1 and $2"
}

new_repo() {
  TEST_ROOT="$(mktemp -d "${TMPDIR:-/tmp}/gs-test.XXXXXX")"
  REPO="$TEST_ROOT/repo"
  "$REAL_GIT" init -q -b main "$REPO"
  printf 'base\n' > "$REPO/file.txt"
  "$REAL_GIT" -C "$REPO" add file.txt
  "$REAL_GIT" -C "$REPO" commit -qm base
}

cleanup_repo() {
  [[ -n "${TEST_ROOT:-}" ]] && rm -rf "$TEST_ROOT"
}

run_gs() {
  local cwd="$1"
  shift
  (cd "$cwd" && "$GS" "$@")
}

common_dir() {
  "$REAL_GIT" -C "$REPO" rev-parse --path-format=absolute --git-common-dir
}

snapshot_metadata() {
  local destination="$1"
  mkdir -p "$destination"
  cp -R "$(common_dir)/gs/." "$destination/"
}

setup_origin() {
  REMOTE="$TEST_ROOT/origin.git"
  "$REAL_GIT" init -q --bare "$REMOTE"
  "$REAL_GIT" -C "$REPO" remote add origin "$REMOTE"
  "$REAL_GIT" -C "$REPO" push -qu origin main
}

install_fake_gh() {
  mkdir -p "$TEST_ROOT/bin"
  cat > "$TEST_ROOT/bin/gh" <<'EOF'
#!/usr/bin/env bash

[[ -n "${GS_TEST_GH_LOG:-}" ]] && printf '%s\n' "$*" >> "$GS_TEST_GH_LOG"

case "${1:-}:${2:-}" in
  pr:view)
    case "$*" in
      *"--json state"*)
        if [[ ",${GS_TEST_GH_MERGED_BRANCHES:-${GS_TEST_GH_MERGED_BRANCH:-}}," == *",${3:-},"* ]]; then
          printf 'MERGED\n'
        else
          printf 'OPEN\n'
        fi
        ;;
      *"--json reviewDecision"*) printf 'APPROVED\n' ;;
      *) exit 1 ;;
    esac
    ;;
  pr:merge)
    if [[ "${GS_TEST_GH_MERGE_PUSH:-0}" == "1" ]]; then
      git push -q origin "${3}:main"
    fi
    exit "${GS_TEST_GH_MERGE_STATUS:-0}"
    ;;
  *) exit 1 ;;
esac
EOF
  chmod +x "$TEST_ROOT/bin/gh"
  export PATH="$TEST_ROOT/bin:$PATH"
  export GS_TEST_GH_LOG="$TEST_ROOT/gh.log"
  : > "$GS_TEST_GH_LOG"
}

install_fake_git_failing_reset() {
  mkdir -p "$TEST_ROOT/bin"
  cat > "$TEST_ROOT/bin/git" <<'EOF'
#!/usr/bin/env bash

if [[ "${1:-}" == "reset" && "${2:-}" == "--hard" ]]; then
  exit 1
fi
exec "$GS_TEST_REAL_GIT" "$@"
EOF
  chmod +x "$TEST_ROOT/bin/git"
  export GS_TEST_REAL_GIT="$REAL_GIT"
  export PATH="$TEST_ROOT/bin:$PATH"
}

install_fake_git_checking_fold_journal() {
  mkdir -p "$TEST_ROOT/bin"
  cat > "$TEST_ROOT/bin/git" <<'EOF'
#!/usr/bin/env bash

if [[ " $* " == *" merge --squash "* ]]; then
  worktree="${2:-.}"
  common="$("$GS_TEST_REAL_GIT" -C "$worktree" rev-parse --path-format=absolute --git-common-dir)"
  finalizer="$common/gs/operation/finalizer"
  [[ -f "$finalizer" ]] || exit 91
  grep -q '^type=fold$' "$finalizer" || exit 92
  printf 'seen\n' > "$GS_TEST_FINALIZER_LOG"
fi
exec "$GS_TEST_REAL_GIT" "$@"
EOF
  chmod +x "$TEST_ROOT/bin/git"
  export GS_TEST_REAL_GIT="$REAL_GIT"
  export GS_TEST_FINALIZER_LOG="$TEST_ROOT/finalizer-seen"
  export PATH="$TEST_ROOT/bin:$PATH"
}

write_recovery_operation() {
  local child="$1" parent="$2" old_oid="$3" fork="$4"
  local op="$(common_dir)/gs/operation"
  mkdir -p "$op/steps"
  printf '%s\n' "$REPO" > "$op/caller"
  : > "$op/stash"
  : > "$op/stash_oid"
  printf '%s\t%s\n' "$child" "$parent" > "$op/plan"
  cat > "$op/steps/000001" <<EOF
branch=$child
parent=$parent
fork=$fork
old_branch_oid=$old_oid
old_parent_oid=$($REAL_GIT -C "$REPO" rev-parse "$parent")
old_parent_present=no
old_parent_name=
old_base_present=no
old_base_oid=
completed=no
EOF
  cat > "$op/journal" <<EOF
operation=restack
status=running
current_step=1
total_steps=1
branch=
new_parent=
executor_path=
temporary_executor=0
old_branch_oid=
old_parent_oid=
caller_path=$REPO
stash_path=
EOF
}

make_linear_stack() {
  run_gs "$REPO" init >/dev/null
  "$REAL_GIT" -C "$REPO" checkout -qb parent
  printf 'parent\n' >> "$REPO/parent.txt"
  "$REAL_GIT" -C "$REPO" add parent.txt
  "$REAL_GIT" -C "$REPO" commit -qm parent
  "$REAL_GIT" -C "$REPO" checkout -qb child
  printf 'child\n' >> "$REPO/child.txt"
  "$REAL_GIT" -C "$REPO" add child.txt
  "$REAL_GIT" -C "$REPO" commit -qm child
  run_gs "$REPO" track parent child >/dev/null
}

test_shared_metadata() {
  new_repo
  run_gs "$REPO" init >/dev/null
  "$REAL_GIT" -C "$REPO" branch side
  local linked="$TEST_ROOT/linked worktree"
  "$REAL_GIT" -C "$REPO" worktree add -q "$linked" side

  local common private
  common="$(cd "$REPO/$("$REAL_GIT" -C "$REPO" rev-parse --git-common-dir)" && pwd -P)"
  private="$("$REAL_GIT" -C "$linked" rev-parse --absolute-git-dir)"
  assert_file "$common/gs/config"
  assert_no_file "$private/gs/config"
  assert_contains "$(run_gs "$linked" ls)" "main"
}

test_legacy_metadata_migration() {
  new_repo
  "$REAL_GIT" -C "$REPO" branch side
  local linked="$TEST_ROOT/linked"
  "$REAL_GIT" -C "$REPO" worktree add -q "$linked" side
  local private common
  private="$("$REAL_GIT" -C "$linked" rev-parse --absolute-git-dir)"
  common="$(cd "$REPO/$("$REAL_GIT" -C "$REPO" rev-parse --git-common-dir)" && pwd -P)"
  mkdir -p "$private/gs/branches"
  printf 'main\n' > "$private/gs/config"
  printf 'main\n' > "$private/gs/branches/side"

  run_gs "$linked" ls >/dev/null
  assert_file "$common/gs/branches/side"
  assert_no_file "$private/gs"
  [[ -d "$private/gs.migrated" ]] || fail "legacy metadata backup missing"
}

test_conflicting_legacy_metadata_stops() {
  new_repo
  "$REAL_GIT" -C "$REPO" branch side
  local linked="$TEST_ROOT/linked"
  "$REAL_GIT" -C "$REPO" worktree add -q "$linked" side
  local private common output status
  private="$("$REAL_GIT" -C "$linked" rev-parse --absolute-git-dir)"
  common="$(cd "$REPO/$("$REAL_GIT" -C "$REPO" rev-parse --git-common-dir)" && pwd -P)"
  mkdir -p "$common/gs/branches" "$private/gs/branches"
  printf 'main\n' > "$common/gs/config"
  printf 'main\n' > "$private/gs/config"
  printf 'main\n' > "$common/gs/branches/side"
  printf 'other\n' > "$private/gs/branches/side"

  output="$(run_gs "$linked" ls 2>&1)" && status=0 || status=$?
  [[ $status -ne 0 ]] || fail "conflicting migration succeeded"
  assert_contains "$output" "conflicting gs metadata"
  assert_eq "$(cat "$common/gs/branches/side")" "main"
}

test_identical_legacy_metadata_copies_migrate() {
  new_repo
  "$REAL_GIT" -C "$REPO" branch side-one
  "$REAL_GIT" -C "$REPO" branch side-two
  local wt_one="$TEST_ROOT/wt-one" wt_two="$TEST_ROOT/wt-two" private_one private_two
  "$REAL_GIT" -C "$REPO" worktree add -q "$wt_one" side-one
  "$REAL_GIT" -C "$REPO" worktree add -q "$wt_two" side-two
  private_one="$("$REAL_GIT" -C "$wt_one" rev-parse --absolute-git-dir)"
  private_two="$("$REAL_GIT" -C "$wt_two" rev-parse --absolute-git-dir)"
  mkdir -p "$private_one/gs/branches" "$private_two/gs/branches"
  printf 'main\n' > "$private_one/gs/config"
  printf 'main\n' > "$private_two/gs/config"
  printf 'main\n' > "$private_one/gs/branches/side-one"
  printf 'main\n' > "$private_two/gs/branches/side-one"

  run_gs "$wt_one" ls >/dev/null

  assert_file "$(common_dir)/gs/branches/side-one"
  [[ -d "$private_one/gs.migrated" ]] || fail "first legacy backup missing"
  [[ -d "$private_two/gs.migrated" ]] || fail "second legacy backup missing"
}

test_restack_in_owned_worktree() {
  new_repo
  make_linear_stack
  local child_wt="$TEST_ROOT/child owner"
  "$REAL_GIT" -C "$REPO" checkout -q parent
  "$REAL_GIT" -C "$REPO" worktree add -q "$child_wt" child
  printf 'parent-2\n' >> "$REPO/parent.txt"
  "$REAL_GIT" -C "$REPO" add parent.txt
  "$REAL_GIT" -C "$REPO" commit -qm parent-2

  run_gs "$REPO" restack >/dev/null
  "$REAL_GIT" -C "$REPO" merge-base --is-ancestor parent child
  assert_eq "$("$REAL_GIT" -C "$child_wt" branch --show-current)" "child"
  [[ -z "$("$REAL_GIT" -C "$child_wt" status --porcelain)" ]] || fail "child owner is dirty"
}

test_dirty_owner_blocks_before_mutation() {
  new_repo
  make_linear_stack
  local child_wt="$TEST_ROOT/child-owner" old_child output status
  "$REAL_GIT" -C "$REPO" checkout -q parent
  "$REAL_GIT" -C "$REPO" worktree add -q "$child_wt" child
  printf 'parent-2\n' >> "$REPO/parent.txt"
  "$REAL_GIT" -C "$REPO" add parent.txt
  "$REAL_GIT" -C "$REPO" commit -qm parent-2
  printf 'dirty\n' > "$child_wt/untracked.txt"
  old_child="$("$REAL_GIT" -C "$REPO" rev-parse child)"

  output="$(run_gs "$REPO" restack 2>&1)" && status=0 || status=$?
  [[ $status -ne 0 ]] || fail "restack ignored dirty owner"
  assert_contains "$output" "child-owner"
  assert_eq "$("$REAL_GIT" -C "$REPO" rev-parse child)" "$old_child"
}

test_navigation_reports_other_owner() {
  new_repo
  make_linear_stack
  local child_wt="$TEST_ROOT/child owner" output status
  "$REAL_GIT" -C "$REPO" checkout -q parent
  "$REAL_GIT" -C "$REPO" worktree add -q "$child_wt" child
  child_wt="$(cd "$child_wt" && pwd -P)"

  output="$(run_gs "$REPO" up 2>&1)" && status=0 || status=$?
  [[ $status -ne 0 ]] || fail "navigation switched to a branch owned elsewhere"
  assert_contains "$output" "$child_wt"
}

test_unowned_branch_uses_temporary_executor() {
  new_repo
  make_linear_stack
  "$REAL_GIT" -C "$REPO" checkout -q parent
  printf 'parent-2\n' >> "$REPO/parent.txt"
  "$REAL_GIT" -C "$REPO" add parent.txt
  "$REAL_GIT" -C "$REPO" commit -qm parent-2
  local before after
  before="$("$REAL_GIT" -C "$REPO" worktree list --porcelain | grep -c '^worktree ')"

  run_gs "$REPO" restack >/dev/null

  after="$("$REAL_GIT" -C "$REPO" worktree list --porcelain | grep -c '^worktree ')"
  assert_eq "$after" "$before"
  "$REAL_GIT" -C "$REPO" merge-base --is-ancestor parent child
}

test_missing_base_refuses_guess() {
  new_repo
  make_linear_stack
  "$REAL_GIT" -C "$REPO" checkout -q parent
  printf 'parent-2\n' >> "$REPO/parent.txt"
  "$REAL_GIT" -C "$REPO" add parent.txt
  "$REAL_GIT" -C "$REPO" commit -qm parent-2
  local common output status
  common="$(cd "$REPO/$("$REAL_GIT" -C "$REPO" rev-parse --git-common-dir)" && pwd -P)"
  rm -f "$common/gs/bases/child"

  output="$(run_gs "$REPO" restack 2>&1)" && status=0 || status=$?
  [[ $status -ne 0 ]] || fail "restack guessed without a durable base"
  assert_contains "$output" "Refusing to guess"
  assert_no_file "$common/gs/operation"
}

test_conflict_continue_from_other_worktree() {
  new_repo
  run_gs "$REPO" init >/dev/null
  "$REAL_GIT" -C "$REPO" checkout -qb parent
  printf 'parent version\n' > "$REPO/file.txt"
  "$REAL_GIT" -C "$REPO" commit -qam parent
  "$REAL_GIT" -C "$REPO" checkout -qb child
  printf 'child version\n' > "$REPO/file.txt"
  "$REAL_GIT" -C "$REPO" commit -qam child
  run_gs "$REPO" track parent child >/dev/null
  local child_wt="$TEST_ROOT/child owner" output status common
  "$REAL_GIT" -C "$REPO" checkout -q parent
  "$REAL_GIT" -C "$REPO" worktree add -q "$child_wt" child
  child_wt="$(cd "$child_wt" && pwd -P)"
  printf 'rewritten parent\n' > "$REPO/file.txt"
  "$REAL_GIT" -C "$REPO" commit -qam parent-2

  output="$(run_gs "$REPO" restack 2>&1)" && status=0 || status=$?
  [[ $status -ne 0 ]] || fail "expected a rebase conflict"
  assert_contains "$output" "$child_wt"
  common="$(cd "$REPO/$("$REAL_GIT" -C "$REPO" rev-parse --git-common-dir)" && pwd -P)"
  assert_file "$common/gs/operation/journal"
  assert_contains "$(run_gs "$REPO" status)" "$child_wt"

  printf 'resolved\n' > "$child_wt/file.txt"
  "$REAL_GIT" -C "$child_wt" add file.txt
  run_gs "$REPO" restack --continue >/dev/null
  "$REAL_GIT" -C "$REPO" merge-base --is-ancestor parent child
  assert_no_file "$common/gs/operation"
}

test_restack_abort_from_other_worktree() {
  new_repo
  run_gs "$REPO" init >/dev/null
  "$REAL_GIT" -C "$REPO" checkout -qb parent
  printf 'parent version\n' > "$REPO/file.txt"
  "$REAL_GIT" -C "$REPO" commit -qam parent
  "$REAL_GIT" -C "$REPO" checkout -qb child
  printf 'child version\n' > "$REPO/file.txt"
  "$REAL_GIT" -C "$REPO" commit -qam child
  run_gs "$REPO" track parent child >/dev/null
  local child_wt="$TEST_ROOT/child-owner" old_child common
  old_child="$("$REAL_GIT" -C "$REPO" rev-parse child)"
  "$REAL_GIT" -C "$REPO" checkout -q parent
  "$REAL_GIT" -C "$REPO" worktree add -q "$child_wt" child
  child_wt="$(cd "$child_wt" && pwd -P)"
  printf 'rewritten parent\n' > "$REPO/file.txt"
  "$REAL_GIT" -C "$REPO" commit -qam parent-2
  run_gs "$REPO" restack >/dev/null 2>&1 && fail "expected conflict"

  run_gs "$REPO" restack --abort >/dev/null
  assert_eq "$("$REAL_GIT" -C "$REPO" rev-parse child)" "$old_child"
  common="$(cd "$REPO/$("$REAL_GIT" -C "$REPO" rev-parse --git-common-dir)" && pwd -P)"
  assert_no_file "$common/gs/operation"
  [[ -z "$("$REAL_GIT" -C "$child_wt" status --porcelain)" ]] || fail "abort left owner dirty"
}

test_abort_restores_completed_steps() {
  new_repo
  run_gs "$REPO" init >/dev/null
  "$REAL_GIT" -C "$REPO" checkout -qb parent
  printf 'parent one\n' > "$REPO/file.txt"
  "$REAL_GIT" -C "$REPO" commit -qam parent
  "$REAL_GIT" -C "$REPO" checkout -qb child
  printf 'child file\n' > "$REPO/child.txt"
  "$REAL_GIT" -C "$REPO" add child.txt
  "$REAL_GIT" -C "$REPO" commit -qm child
  "$REAL_GIT" -C "$REPO" checkout -qb grandchild
  printf 'grandchild version\n' > "$REPO/file.txt"
  "$REAL_GIT" -C "$REPO" commit -qam grandchild
  run_gs "$REPO" track parent child grandchild >/dev/null
  local old_child old_grandchild old_child_base
  old_child="$("$REAL_GIT" -C "$REPO" rev-parse child)"
  old_grandchild="$("$REAL_GIT" -C "$REPO" rev-parse grandchild)"
  old_child_base="$(cat "$(common_dir)/gs/bases/child")"
  "$REAL_GIT" -C "$REPO" checkout -q parent
  printf 'parent two\n' > "$REPO/file.txt"
  "$REAL_GIT" -C "$REPO" commit -qam parent-2

  run_gs "$REPO" restack >/dev/null 2>&1 && fail "expected grandchild conflict"
  [[ "$("$REAL_GIT" -C "$REPO" rev-parse child)" != "$old_child" ]] || fail "child did not complete before conflict"
  run_gs "$REPO" restack --abort >/dev/null
  assert_eq "$("$REAL_GIT" -C "$REPO" rev-parse child)" "$old_child"
  assert_eq "$("$REAL_GIT" -C "$REPO" rev-parse grandchild)" "$old_grandchild"
  assert_eq "$(cat "$(common_dir)/gs/bases/child")" "$old_child_base"
}

test_delete_dirty_owner_blocks_before_mutation() {
  new_repo
  make_linear_stack
  local parent_wt="$TEST_ROOT/parent-owner" metadata="$TEST_ROOT/metadata" output status
  "$REAL_GIT" -C "$REPO" worktree add -q "$parent_wt" parent
  parent_wt="$(cd "$parent_wt" && pwd -P)"
  printf 'dirty\n' > "$parent_wt/untracked.txt"
  snapshot_metadata "$metadata"

  output="$(run_gs "$REPO" delete parent 2>&1)" && status=0 || status=$?
  [[ $status -ne 0 ]] || fail "delete ignored dirty owner"
  assert_dir_eq "$metadata" "$(common_dir)/gs"
  "$REAL_GIT" -C "$REPO" show-ref --verify --quiet refs/heads/parent
  assert_eq "$(cat "$(common_dir)/gs/branches/child")" "parent"
}

test_delete_preserves_clean_owned_branch() {
  new_repo
  make_linear_stack
  local parent_wt="$TEST_ROOT/parent-owner"
  "$REAL_GIT" -C "$REPO" worktree add -q "$parent_wt" parent

  run_gs "$REPO" delete parent >/dev/null

  assert_eq "$("$REAL_GIT" -C "$parent_wt" branch --show-current)" "parent"
  "$REAL_GIT" -C "$REPO" show-ref --verify --quiet refs/heads/parent
  assert_no_file "$(common_dir)/gs/branches/parent"
  assert_no_file "$(common_dir)/gs/bases/parent"
  assert_eq "$(cat "$(common_dir)/gs/branches/child")" "main"
}

test_sync_dirty_owner_blocks_before_mutation() {
  new_repo
  make_linear_stack
  setup_origin
  install_fake_gh
  export GS_TEST_GH_MERGED_BRANCH=parent
  local parent_wt="$TEST_ROOT/parent-owner" metadata="$TEST_ROOT/metadata" output status old_main
  "$REAL_GIT" -C "$REPO" worktree add -q "$parent_wt" parent
  parent_wt="$(cd "$parent_wt" && pwd -P)"
  printf 'dirty\n' > "$parent_wt/untracked.txt"
  old_main="$("$REAL_GIT" -C "$REPO" rev-parse main)"
  snapshot_metadata "$metadata"

  output="$(run_gs "$REPO" sync 2>&1)" && status=0 || status=$?
  [[ $status -ne 0 ]] || fail "sync ignored dirty owner"
  assert_dir_eq "$metadata" "$(common_dir)/gs"
  assert_eq "$("$REAL_GIT" -C "$REPO" rev-parse main)" "$old_main"
  "$REAL_GIT" -C "$REPO" show-ref --verify --quiet refs/heads/parent
}

test_sync_preserves_clean_owned_merged_branch() {
  new_repo
  make_linear_stack
  setup_origin
  install_fake_gh
  export GS_TEST_GH_MERGED_BRANCH=parent
  local parent_wt="$TEST_ROOT/parent-owner"
  "$REAL_GIT" -C "$REPO" worktree add -q "$parent_wt" parent

  run_gs "$REPO" sync >/dev/null

  assert_eq "$("$REAL_GIT" -C "$parent_wt" branch --show-current)" "parent"
  "$REAL_GIT" -C "$REPO" show-ref --verify --quiet refs/heads/parent
  assert_no_file "$(common_dir)/gs/branches/parent"
  assert_no_file "$(common_dir)/gs/bases/parent"
  assert_eq "$(cat "$(common_dir)/gs/branches/child")" "main"
}

test_land_dirty_owner_blocks_before_merge() {
  new_repo
  make_linear_stack
  setup_origin
  install_fake_gh
  export GS_TEST_GH_MERGE_PUSH=1
  local parent_wt="$TEST_ROOT/parent-owner" metadata="$TEST_ROOT/metadata" output status remote_main
  "$REAL_GIT" -C "$REPO" worktree add -q "$parent_wt" parent
  parent_wt="$(cd "$parent_wt" && pwd -P)"
  printf 'dirty\n' > "$parent_wt/untracked.txt"
  remote_main="$("$REAL_GIT" --git-dir="$REMOTE" rev-parse main)"
  snapshot_metadata "$metadata"

  output="$(run_gs "$REPO" land parent 2>&1)" && status=0 || status=$?
  [[ $status -ne 0 ]] || fail "land ignored dirty owner"
  ! grep -q '^pr merge ' "$GS_TEST_GH_LOG" || fail "land merged before checking the dirty owner"
  assert_eq "$("$REAL_GIT" --git-dir="$REMOTE" rev-parse main)" "$remote_main"
  assert_dir_eq "$metadata" "$(common_dir)/gs"
}

test_land_preserves_clean_owned_branch() {
  new_repo
  make_linear_stack
  setup_origin
  install_fake_gh
  export GS_TEST_GH_MERGE_PUSH=1
  local parent_wt="$TEST_ROOT/parent-owner"
  "$REAL_GIT" -C "$REPO" worktree add -q "$parent_wt" parent

  run_gs "$REPO" land parent >/dev/null

  assert_eq "$("$REAL_GIT" -C "$parent_wt" branch --show-current)" "parent"
  "$REAL_GIT" -C "$REPO" show-ref --verify --quiet refs/heads/parent
  assert_no_file "$(common_dir)/gs/branches/parent"
  assert_no_file "$(common_dir)/gs/bases/parent"
  assert_eq "$(cat "$(common_dir)/gs/branches/child")" "main"
}

make_temporary_executor_conflict() {
  new_repo
  run_gs "$REPO" init >/dev/null
  "$REAL_GIT" -C "$REPO" checkout -qb parent
  printf 'parent version\n' > "$REPO/file.txt"
  "$REAL_GIT" -C "$REPO" commit -qam parent
  "$REAL_GIT" -C "$REPO" checkout -qb child
  printf 'child version\n' > "$REPO/file.txt"
  "$REAL_GIT" -C "$REPO" commit -qam child
  run_gs "$REPO" track parent child >/dev/null
  "$REAL_GIT" -C "$REPO" checkout -q parent
  printf 'rewritten parent\n' > "$REPO/file.txt"
  "$REAL_GIT" -C "$REPO" commit -qam parent-2

  TEMP_OLD_CHILD="$("$REAL_GIT" -C "$REPO" rev-parse child)"
  TEMP_WORKTREE_COUNT="$("$REAL_GIT" -C "$REPO" worktree list --porcelain | grep -c '^worktree ')"
  run_gs "$REPO" restack >/dev/null 2>&1 && fail "expected a temporary executor conflict"
  TEMP_EXECUTOR="$(sed -n 's/^executor_path=//p' "$(common_dir)/gs/operation/journal")"
  assert_eq "$(sed -n 's/^temporary_executor=//p' "$(common_dir)/gs/operation/journal")" "1"
  [[ -d "$TEMP_EXECUTOR" ]] || fail "temporary executor was removed during conflict"
  assert_eq "$("$REAL_GIT" -C "$REPO" worktree list --porcelain | grep -c '^worktree ')" "$((TEMP_WORKTREE_COUNT + 1))"
}

test_temporary_executor_continue_cleans_worktree() {
  make_temporary_executor_conflict
  printf 'resolved\n' > "$TEMP_EXECUTOR/file.txt"
  "$REAL_GIT" -C "$TEMP_EXECUTOR" add file.txt

  run_gs "$REPO" restack --continue >/dev/null

  assert_no_file "$TEMP_EXECUTOR"
  assert_no_file "$(common_dir)/gs/operation"
  assert_eq "$("$REAL_GIT" -C "$REPO" worktree list --porcelain | grep -c '^worktree ')" "$TEMP_WORKTREE_COUNT"
  "$REAL_GIT" -C "$REPO" merge-base --is-ancestor parent child
}

test_temporary_executor_abort_cleans_worktree() {
  make_temporary_executor_conflict

  run_gs "$REPO" restack --abort >/dev/null

  assert_no_file "$TEMP_EXECUTOR"
  assert_no_file "$(common_dir)/gs/operation"
  assert_eq "$("$REAL_GIT" -C "$REPO" worktree list --porcelain | grep -c '^worktree ')" "$TEMP_WORKTREE_COUNT"
  assert_eq "$("$REAL_GIT" -C "$REPO" rev-parse child)" "$TEMP_OLD_CHILD"
}

test_restack_autostash_restores_its_exact_stash() {
  new_repo
  run_gs "$REPO" init >/dev/null
  "$REAL_GIT" -C "$REPO" checkout -qb parent
  printf 'parent version\n' > "$REPO/file.txt"
  "$REAL_GIT" -C "$REPO" commit -qam parent
  "$REAL_GIT" -C "$REPO" checkout -qb child
  printf 'child version\n' > "$REPO/file.txt"
  "$REAL_GIT" -C "$REPO" commit -qam child
  run_gs "$REPO" track parent child >/dev/null
  "$REAL_GIT" -C "$REPO" checkout -q parent
  printf 'rewritten parent\n' > "$REPO/file.txt"
  "$REAL_GIT" -C "$REPO" commit -qam parent-2
  printf 'original dirty state\n' > "$REPO/original.txt"

  run_gs "$REPO" restack --autostash >/dev/null 2>&1 && fail "expected a restack conflict"
  local operation="$(common_dir)/gs/operation" executor recorded_stash later_stash
  executor="$(sed -n 's/^executor_path=//p' "$operation/journal")"
  recorded_stash="$(cat "$operation/stash_oid")"
  printf 'later stash\n' > "$REPO/later.txt"
  "$REAL_GIT" -C "$REPO" stash push -u -qm later-stash
  later_stash="$("$REAL_GIT" -C "$REPO" rev-parse refs/stash)"

  printf 'resolved\n' > "$executor/file.txt"
  "$REAL_GIT" -C "$executor" add file.txt
  run_gs "$REPO" restack --continue >/dev/null

  assert_eq "$(cat "$REPO/original.txt")" "original dirty state"
  assert_no_file "$REPO/later.txt"
  assert_eq "$("$REAL_GIT" -C "$REPO" rev-parse refs/stash)" "$later_stash"
  ! "$REAL_GIT" -C "$REPO" stash list --format='%H' | grep -q "^$recorded_stash$" ||
    fail "restack left its recorded stash behind"
}

test_active_operation_blocks_another_mutation() {
  make_temporary_executor_conflict
  local metadata="$TEST_ROOT/metadata" output status
  snapshot_metadata "$metadata"

  output="$(run_gs "$REPO" delete parent 2>&1)" && status=0 || status=$?
  [[ $status -ne 0 ]] || fail "mutation ran during active operation"
  assert_contains "$output" "operation is already in progress"
  assert_dir_eq "$metadata" "$(common_dir)/gs"
  "$REAL_GIT" -C "$REPO" show-ref --verify --quiet refs/heads/parent
  run_gs "$REPO" restack --abort >/dev/null
}

test_stale_mutation_lock_is_recovered() {
  new_repo
  make_linear_stack
  "$REAL_GIT" -C "$REPO" checkout -q main
  local lock dead_pid=999999
  lock="$(common_dir)/gs-mutation.lock"
  while kill -0 "$dead_pid" 2>/dev/null; do
    dead_pid=$((dead_pid + 1))
  done
  mkdir "$lock"
  printf '%s\n' "$dead_pid" > "$lock/pid"

  run_gs "$REPO" delete child >/dev/null

  assert_no_file "$lock"
  ! "$REAL_GIT" -C "$REPO" show-ref --verify --quiet refs/heads/child ||
    fail "delete did not run after recovering the stale lock"
}

test_live_mutation_lock_blocks_another_mutation() {
  new_repo
  make_linear_stack
  local metadata="$TEST_ROOT/metadata" output status lock
  snapshot_metadata "$metadata"
  lock="$(common_dir)/gs-mutation.lock"
  mkdir "$lock"
  printf '%s\n' "$$" > "$lock/pid"

  output="$(run_gs "$REPO" delete child 2>&1)" && status=0 || status=$?
  [[ $status -ne 0 ]] || fail "mutation ignored repository lock"
  assert_contains "$output" "another gs mutation"
  assert_dir_eq "$metadata" "$(common_dir)/gs"
  "$REAL_GIT" -C "$REPO" show-ref --verify --quiet refs/heads/child
}

test_move_uses_recorded_base_after_parent_rewrite() {
  new_repo
  run_gs "$REPO" init >/dev/null
  "$REAL_GIT" -C "$REPO" checkout -qb source
  printf 'old source\n' > "$REPO/source.txt"
  "$REAL_GIT" -C "$REPO" add source.txt
  "$REAL_GIT" -C "$REPO" commit -qm source
  local recorded_base
  recorded_base="$("$REAL_GIT" -C "$REPO" rev-parse source)"
  "$REAL_GIT" -C "$REPO" checkout -qb feature
  printf 'feature\n' > "$REPO/feature.txt"
  "$REAL_GIT" -C "$REPO" add feature.txt
  "$REAL_GIT" -C "$REPO" commit -qm feature
  run_gs "$REPO" track source feature >/dev/null
  assert_eq "$(cat "$(common_dir)/gs/bases/feature")" "$recorded_base"
  "$REAL_GIT" -C "$REPO" checkout -qb target main
  printf 'target\n' > "$REPO/target.txt"
  "$REAL_GIT" -C "$REPO" add target.txt
  "$REAL_GIT" -C "$REPO" commit -qm target
  "$REAL_GIT" -C "$REPO" checkout -q source
  "$REAL_GIT" -C "$REPO" reset --hard main >/dev/null
  printf 'rewritten source\n' > "$REPO/rewritten-source.txt"
  "$REAL_GIT" -C "$REPO" add rewritten-source.txt
  "$REAL_GIT" -C "$REPO" commit -qm source-rewritten
  "$REAL_GIT" -C "$REPO" checkout -q feature

  run_gs "$REPO" move --onto target >/dev/null

  "$REAL_GIT" -C "$REPO" merge-base --is-ancestor target feature
  assert_file "$REPO/feature.txt"
  assert_no_file "$REPO/source.txt"
  assert_eq "$(cat "$(common_dir)/gs/branches/feature")" "target"
  assert_eq "$(cat "$(common_dir)/gs/bases/feature")" "$("$REAL_GIT" -C "$REPO" rev-parse target)"
}

test_git_operation_in_progress_blocks_restack_preflight() {
  new_repo
  make_linear_stack
  "$REAL_GIT" -C "$REPO" checkout -qb merge-source parent
  printf 'merge source\n' > "$REPO/file.txt"
  "$REAL_GIT" -C "$REPO" commit -qam merge-source
  "$REAL_GIT" -C "$REPO" checkout -q parent
  local child_wt="$TEST_ROOT/child-owner" metadata="$TEST_ROOT/metadata" output status old_child
  "$REAL_GIT" -C "$REPO" worktree add -q "$child_wt" child
  child_wt="$(cd "$child_wt" && pwd -P)"
  printf 'child merge side\n' > "$child_wt/file.txt"
  "$REAL_GIT" -C "$child_wt" commit -qam child-side
  "$REAL_GIT" -C "$child_wt" merge merge-source >/dev/null 2>&1 && fail "expected merge conflict"
  old_child="$("$REAL_GIT" -C "$REPO" rev-parse child)"
  snapshot_metadata "$metadata"

  output="$(run_gs "$REPO" restack 2>&1)" && status=0 || status=$?
  [[ $status -ne 0 ]] || fail "restack ignored active Git operation"
  assert_contains "$output" "Git operation already in progress"
  assert_dir_eq "$metadata" "$(common_dir)/gs"
  assert_eq "$("$REAL_GIT" -C "$REPO" rev-parse child)" "$old_child"
  assert_no_file "$(common_dir)/gs/operation"
}

test_failed_git_operation_does_not_change_metadata() {
  new_repo
  run_gs "$REPO" init >/dev/null
  "$REAL_GIT" -C "$REPO" checkout -qb source
  printf 'source\n' > "$REPO/file.txt"
  "$REAL_GIT" -C "$REPO" commit -qam source
  "$REAL_GIT" -C "$REPO" checkout -qb feature
  printf 'feature\n' > "$REPO/file.txt"
  "$REAL_GIT" -C "$REPO" commit -qam feature
  run_gs "$REPO" track source feature >/dev/null
  local recorded_base
  recorded_base="$(cat "$(common_dir)/gs/bases/feature")"
  "$REAL_GIT" -C "$REPO" checkout -qb target main
  printf 'target\n' > "$REPO/file.txt"
  "$REAL_GIT" -C "$REPO" commit -qam target
  "$REAL_GIT" -C "$REPO" checkout -q source
  "$REAL_GIT" -C "$REPO" reset --hard main >/dev/null
  printf 'rewritten source\n' > "$REPO/source.txt"
  "$REAL_GIT" -C "$REPO" add source.txt
  "$REAL_GIT" -C "$REPO" commit -qm source-rewritten
  "$REAL_GIT" -C "$REPO" checkout -q feature
  local metadata="$TEST_ROOT/metadata" output status old_feature
  old_feature="$("$REAL_GIT" -C "$REPO" rev-parse feature)"
  snapshot_metadata "$metadata"

  output="$(run_gs "$REPO" move --onto target 2>&1)" && status=0 || status=$?
  [[ $status -ne 0 ]] || fail "expected move rebase to fail"
  assert_contains "$output" "rebase failed"
  assert_dir_eq "$metadata" "$(common_dir)/gs"
  assert_eq "$("$REAL_GIT" -C "$REPO" rev-parse feature)" "$old_feature"
  assert_eq "$(cat "$(common_dir)/gs/branches/feature")" "source"
  assert_eq "$(cat "$(common_dir)/gs/bases/feature")" "$recorded_base"
}

test_commit_dirty_descendant_blocks_before_commit() {
  new_repo
  make_linear_stack
  local child_wt="$TEST_ROOT/child-owner" before output status
  "$REAL_GIT" -C "$REPO" checkout -q parent
  "$REAL_GIT" -C "$REPO" worktree add -q "$child_wt" child
  printf 'dirty\n' > "$child_wt/untracked.txt"
  printf 'parent change\n' >> "$REPO/parent.txt"
  "$REAL_GIT" -C "$REPO" add parent.txt
  before="$("$REAL_GIT" -C "$REPO" rev-parse parent)"

  output="$(run_gs "$REPO" commit -m blocked 2>&1)" && status=0 || status=$?
  [[ $status -ne 0 ]] || fail "commit ignored dirty descendant owner"
  assert_contains "$output" "child-owner"
  assert_eq "$("$REAL_GIT" -C "$REPO" rev-parse parent)" "$before"
}

test_untrack_preserves_child_fork() {
  new_repo
  make_linear_stack
  local old_base
  old_base="$(cat "$(common_dir)/gs/bases/child")"

  run_gs "$REPO" untrack parent >/dev/null

  assert_eq "$(cat "$(common_dir)/gs/branches/child")" "main"
  assert_eq "$(cat "$(common_dir)/gs/bases/child")" "$old_base"
}

test_rename_preserves_base_and_children() {
  new_repo
  make_linear_stack
  local old_base
  old_base="$(cat "$(common_dir)/gs/bases/child")"
  "$REAL_GIT" -C "$REPO" checkout -q child

  run_gs "$REPO" rename renamed-child >/dev/null

  assert_no_file "$(common_dir)/gs/branches/child"
  assert_eq "$(cat "$(common_dir)/gs/branches/renamed-child")" "parent"
  assert_eq "$(cat "$(common_dir)/gs/bases/renamed-child")" "$old_base"
}

test_insert_rebases_child_in_owner_worktree() {
  new_repo
  make_linear_stack
  local child_wt="$TEST_ROOT/child-owner"
  "$REAL_GIT" -C "$REPO" checkout -q parent
  "$REAL_GIT" -C "$REPO" worktree add -q "$child_wt" child

  run_gs "$REPO" insert middle --between parent child >/dev/null

  assert_eq "$(cat "$(common_dir)/gs/branches/middle")" "parent"
  assert_eq "$(cat "$(common_dir)/gs/branches/child")" "middle"
  assert_eq "$("$REAL_GIT" -C "$child_wt" branch --show-current)" "child"
}

test_fold_uses_parent_owner_worktree() {
  new_repo
  run_gs "$REPO" init >/dev/null
  "$REAL_GIT" -C "$REPO" checkout -qb parent
  printf 'parent\n' > "$REPO/parent.txt"
  "$REAL_GIT" -C "$REPO" add parent.txt
  "$REAL_GIT" -C "$REPO" commit -qm parent
  "$REAL_GIT" -C "$REPO" checkout -qb folded
  printf 'folded\n' > "$REPO/folded.txt"
  "$REAL_GIT" -C "$REPO" add folded.txt
  "$REAL_GIT" -C "$REPO" commit -qm folded
  run_gs "$REPO" track parent folded >/dev/null
  local parent_wt="$TEST_ROOT/parent-owner"
  "$REAL_GIT" -C "$REPO" checkout -q folded
  "$REAL_GIT" -C "$REPO" worktree add -q "$parent_wt" parent

  run_gs "$REPO" fold >/dev/null

  assert_file "$parent_wt/folded.txt"
  assert_no_file "$(common_dir)/gs/branches/folded"
  assert_eq "$("$REAL_GIT" -C "$parent_wt" branch --show-current)" "parent"
  assert_eq "$("$REAL_GIT" -C "$REPO" branch --show-current)" "folded"
}

test_continue_between_steps_without_executor() {
  new_repo
  make_linear_stack
  local old_child fork
  old_child="$("$REAL_GIT" -C "$REPO" rev-parse child)"
  fork="$(cat "$(common_dir)/gs/bases/child")"
  "$REAL_GIT" -C "$REPO" checkout -q parent
  printf 'parent-2\n' >> "$REPO/parent.txt"
  "$REAL_GIT" -C "$REPO" add parent.txt
  "$REAL_GIT" -C "$REPO" commit -qm parent-2
  write_recovery_operation child parent "$old_child" "$fork"

  run_gs "$REPO" restack --continue >/dev/null

  "$REAL_GIT" -C "$REPO" merge-base --is-ancestor parent child
  assert_no_file "$(common_dir)/gs/operation"
}

test_abort_removes_metadata_that_was_originally_absent() {
  new_repo
  run_gs "$REPO" init >/dev/null
  "$REAL_GIT" -C "$REPO" checkout -qb recovery-child
  printf 'child\n' > "$REPO/child.txt"
  "$REAL_GIT" -C "$REPO" add child.txt
  "$REAL_GIT" -C "$REPO" commit -qm child
  local old_child="$("$REAL_GIT" -C "$REPO" rev-parse recovery-child)" op
  write_recovery_operation recovery-child main "$old_child" "$("$REAL_GIT" -C "$REPO" rev-parse main)"
  op="$(common_dir)/gs/operation"
  "$REAL_GIT" -C "$REPO" commit --allow-empty -qm rewritten
  printf 'main\n' > "$(common_dir)/gs/branches/recovery-child"
  printf '%s\n' "$("$REAL_GIT" -C "$REPO" rev-parse main)" > "$(common_dir)/gs/bases/recovery-child"
  sed 's/completed=no/completed=yes/' "$op/steps/000001" > "$op/steps/000001.tmp"
  mv "$op/steps/000001.tmp" "$op/steps/000001"

  run_gs "$REPO" restack --abort >/dev/null

  assert_eq "$("$REAL_GIT" -C "$REPO" rev-parse recovery-child)" "$old_child"
  assert_no_file "$(common_dir)/gs/branches/recovery-child"
  assert_no_file "$(common_dir)/gs/bases/recovery-child"
}

test_continue_after_rebase_completed_before_step_marker() {
  new_repo
  make_linear_stack
  local old_child fork op
  old_child="$("$REAL_GIT" -C "$REPO" rev-parse child)"
  fork="$(cat "$(common_dir)/gs/bases/child")"
  "$REAL_GIT" -C "$REPO" checkout -q parent
  printf 'parent-2\n' >> "$REPO/parent.txt"
  "$REAL_GIT" -C "$REPO" add parent.txt
  "$REAL_GIT" -C "$REPO" commit -qm parent-2
  "$REAL_GIT" -C "$REPO" rebase --onto parent "$fork" child --quiet
  write_recovery_operation child parent "$old_child" "$fork"
  op="$(common_dir)/gs/operation"
  sed -e 's|^branch=$|branch=child|' -e 's|^new_parent=$|new_parent=parent|' \
    -e "s|^executor_path=$|executor_path=$REPO|" -e "s|^old_branch_oid=$|old_branch_oid=$old_child|" \
    "$op/journal" > "$op/journal.tmp"
  mv "$op/journal.tmp" "$op/journal"

  run_gs "$REPO" restack --continue >/dev/null

  assert_no_file "$op"
  "$REAL_GIT" -C "$REPO" merge-base --is-ancestor parent child
}

test_autostash_conflict_retains_journal() {
  new_repo
  run_gs "$REPO" init >/dev/null
  printf 'stashed\n' > "$REPO/file.txt"
  "$REAL_GIT" -C "$REPO" stash push -qm recovery-stash
  local stash_oid="$("$REAL_GIT" -C "$REPO" rev-parse refs/stash)" op output status
  printf 'committed conflict\n' > "$REPO/file.txt"
  "$REAL_GIT" -C "$REPO" commit -qam conflict
  op="$(common_dir)/gs/operation"
  mkdir -p "$op/steps"
  printf '%s\n' "$REPO" > "$op/caller"
  printf '%s\n' "$REPO" > "$op/stash"
  printf '%s\n' "$stash_oid" > "$op/stash_oid"
  : > "$op/plan"
  cat > "$op/journal" <<EOF
operation=restack
status=running
current_step=1
total_steps=0
branch=
new_parent=
executor_path=
temporary_executor=0
old_branch_oid=
old_parent_oid=
caller_path=$REPO
stash_path=$REPO
EOF

  output="$(run_gs "$REPO" restack --continue 2>&1)" && status=0 || status=$?
  [[ $status -ne 0 ]] || fail "autostash conflict removed the operation"
  assert_contains "$output" "journal was retained"
  assert_file "$op/journal"
  assert_eq "$(sed -n 's/^status=//p' "$op/journal")" "autostash_conflict"
  assert_eq "$(cat "$op/stash_oid")" "$stash_oid"
}

test_fold_publishes_finalizer_before_parent_mutation() {
  new_repo
  make_linear_stack
  "$REAL_GIT" -C "$REPO" checkout -q parent
  install_fake_git_checking_fold_journal

  run_gs "$REPO" fold >/dev/null

  assert_file "$GS_TEST_FINALIZER_LOG"
}

test_fold_conflict_abort_restores_parent_before_cleanup() {
  new_repo
  make_linear_stack
  "$REAL_GIT" -C "$REPO" checkout -q main
  local old_main="$("$REAL_GIT" -C "$REPO" rev-parse main)" op
  "$REAL_GIT" -C "$REPO" merge --squash parent --quiet
  "$REAL_GIT" -C "$REPO" commit --no-edit -q
  op="$(common_dir)/gs/operation"
  mkdir -p "$op/steps"
  printf '%s\n' "$REPO" > "$op/caller"
  : > "$op/stash"
  : > "$op/stash_oid"
  : > "$op/plan"
  cat > "$op/journal" <<EOF
operation=restack
status=running
current_step=1
total_steps=0
branch=
new_parent=
executor_path=
temporary_executor=0
old_branch_oid=
old_parent_oid=
caller_path=$REPO
stash_path=
EOF
  cat > "$op/finalizer" <<EOF
type=fold
branch=parent
parent=main
parent_old_oid=$old_main
local_mutation_done=yes
local_restore_done=no
branch_cleanup_done=no
tracking_cleanup_done=no
EOF
  [[ "$("$REAL_GIT" -C "$REPO" rev-parse main)" != "$old_main" ]] || fail "fixture did not mutate parent"

  run_gs "$REPO" restack --abort >/dev/null

  assert_eq "$("$REAL_GIT" -C "$REPO" rev-parse main)" "$old_main"
  "$REAL_GIT" -C "$REPO" show-ref --verify --quiet refs/heads/parent
  assert_file "$(common_dir)/gs/branches/parent"
}

test_land_finalizer_tolerates_missing_branch() {
  new_repo
  make_linear_stack
  "$REAL_GIT" -C "$REPO" checkout -q main
  "$REAL_GIT" -C "$REPO" branch -D parent >/dev/null
  local op="$(common_dir)/gs/operation"
  mkdir -p "$op/steps"
  printf '%s\n' "$REPO" > "$op/caller"
  : > "$op/stash"
  : > "$op/stash_oid"
  : > "$op/plan"
  cat > "$op/journal" <<EOF
operation=restack
status=running
current_step=1
total_steps=0
branch=
new_parent=
executor_path=
temporary_executor=0
old_branch_oid=
old_parent_oid=
caller_path=$REPO
stash_path=
EOF
  cat > "$op/finalizer" <<'EOF'
type=land
branch=parent
parent=main
parent_old_oid=
strategy=--squash
remote_merge_done=yes
parent_update_done=yes
branch_cleanup_done=no
tracking_cleanup_done=no
EOF

  run_gs "$REPO" restack --continue >/dev/null

  assert_no_file "$op"
  assert_no_file "$(common_dir)/gs/branches/parent"
  assert_no_file "$(common_dir)/gs/bases/parent"
}

test_stack_rejects_self_cycle() {
  new_repo
  make_linear_stack
  local metadata="$TEST_ROOT/metadata" output status
  snapshot_metadata "$metadata"

  output="$(run_gs "$REPO" stack child 2>&1)" && status=0 || status=$?
  [[ $status -ne 0 ]] || fail "stack allowed a self-cycle"
  assert_contains "$output" "onto itself"
  assert_dir_eq "$metadata" "$(common_dir)/gs"
}

test_commit_missing_descendant_base_stops_before_commit() {
  new_repo
  make_linear_stack
  "$REAL_GIT" -C "$REPO" checkout -q parent
  "$REAL_GIT" -C "$REPO" checkout --orphan rewritten-parent >/dev/null
  "$REAL_GIT" -C "$REPO" rm -rf . >/dev/null
  printf 'rewritten root\n' > "$REPO/parent.txt"
  "$REAL_GIT" -C "$REPO" add parent.txt
  "$REAL_GIT" -C "$REPO" commit -qm rewritten-parent
  "$REAL_GIT" -C "$REPO" branch -f parent HEAD
  "$REAL_GIT" -C "$REPO" checkout -q parent
  "$REAL_GIT" -C "$REPO" branch -D rewritten-parent >/dev/null
  printf 'parent change\n' >> "$REPO/parent.txt"
  "$REAL_GIT" -C "$REPO" add parent.txt
  rm -f "$(common_dir)/gs/bases/child"
  local before output status
  before="$("$REAL_GIT" -C "$REPO" rev-parse parent)"

  output="$(run_gs "$REPO" commit -m blocked 2>&1)" && status=0 || status=$?
  [[ $status -ne 0 ]] || fail "commit succeeded without a durable descendant base"
  assert_contains "$output" "no recorded base"
  assert_eq "$("$REAL_GIT" -C "$REPO" rev-parse parent)" "$before"
}

test_split_rejects_commit_below_recorded_base() {
  new_repo
  make_linear_stack
  "$REAL_GIT" -C "$REPO" checkout -q child
  local metadata="$TEST_ROOT/metadata" output status
  snapshot_metadata "$metadata"

  output="$(run_gs "$REPO" split main too-low 2>&1)" && status=0 || status=$?
  [[ $status -ne 0 ]] || fail "split accepted a commit below the recorded base"
  assert_contains "$output" "below the recorded base"
  assert_dir_eq "$metadata" "$(common_dir)/gs"
  ! "$REAL_GIT" -C "$REPO" show-ref --verify --quiet refs/heads/too-low || fail "failed split left a branch"
}

run_test() {
  local name="$1"
  TEST_ROOT=""
  local result_file
  result_file="$(mktemp "${TMPDIR:-/tmp}/gs-test-result.XXXXXX")"
  (set -e; "$name"; printf '%s\n' "$TEST_ROOT" > "$result_file")
  local status=$?
  [[ -s "$result_file" ]] && TEST_ROOT="$(cat "$result_file")"
  rm -f "$result_file"
  if [[ $status -eq 0 ]]; then
    echo "ok - $name"
    PASS=$((PASS + 1))
  else
    echo "not ok - $name"
    FAIL=$((FAIL + 1))
  fi
  cleanup_repo
}

for test_name in \
  test_shared_metadata \
  test_legacy_metadata_migration \
  test_conflicting_legacy_metadata_stops \
  test_identical_legacy_metadata_copies_migrate \
  test_restack_in_owned_worktree \
  test_dirty_owner_blocks_before_mutation \
  test_navigation_reports_other_owner \
  test_unowned_branch_uses_temporary_executor \
  test_missing_base_refuses_guess \
  test_conflict_continue_from_other_worktree \
  test_restack_abort_from_other_worktree \
  test_abort_restores_completed_steps \
  test_delete_dirty_owner_blocks_before_mutation \
  test_delete_preserves_clean_owned_branch \
  test_sync_dirty_owner_blocks_before_mutation \
  test_sync_preserves_clean_owned_merged_branch \
  test_land_dirty_owner_blocks_before_merge \
  test_land_preserves_clean_owned_branch \
  test_temporary_executor_continue_cleans_worktree \
  test_temporary_executor_abort_cleans_worktree \
  test_restack_autostash_restores_its_exact_stash \
  test_active_operation_blocks_another_mutation \
  test_stale_mutation_lock_is_recovered \
  test_live_mutation_lock_blocks_another_mutation \
  test_move_uses_recorded_base_after_parent_rewrite \
  test_git_operation_in_progress_blocks_restack_preflight \
  test_failed_git_operation_does_not_change_metadata \
  test_commit_dirty_descendant_blocks_before_commit \
  test_untrack_preserves_child_fork \
  test_rename_preserves_base_and_children \
  test_insert_rebases_child_in_owner_worktree \
  test_fold_uses_parent_owner_worktree \
  test_continue_between_steps_without_executor \
  test_abort_removes_metadata_that_was_originally_absent \
  test_continue_after_rebase_completed_before_step_marker \
  test_autostash_conflict_retains_journal \
  test_fold_publishes_finalizer_before_parent_mutation \
  test_fold_conflict_abort_restores_parent_before_cleanup \
  test_land_finalizer_tolerates_missing_branch \
  test_stack_rejects_self_cycle \
  test_commit_missing_descendant_base_stops_before_commit \
  test_split_rejects_commit_below_recorded_base
do
  run_test "$test_name"
done

echo "$PASS passed; $FAIL failed"
[[ $FAIL -eq 0 ]]
