# Shared, worktree-aware restack support for gs.

branch_owner_path() {
  local wanted="$1" field path=""
  while IFS= read -r -d '' field; do
    case "$field" in
      worktree\ *) path="${field#worktree }" ;;
      branch\ refs/heads/*)
        if [[ "${field#branch refs/heads/}" == "$wanted" ]]; then
          printf '%s\n' "$path"
          return 0
        fi
        ;;
    esac
  done < <(git worktree list --porcelain -z)
  return 1
}

worktree_has_git_operation() {
  local path="$1" marker marker_path
  for marker in rebase-merge rebase-apply MERGE_HEAD CHERRY_PICK_HEAD REVERT_HEAD BISECT_LOG; do
    marker_path="$(git -C "$path" rev-parse --path-format=absolute --git-path "$marker" 2>/dev/null)" || continue
    [[ -e "$marker_path" ]] && return 0
  done
  return 1
}

display_worktree_path() {
  local path="$1" alternate
  case "$path" in
    /private/var/*) alternate="${path#/private}" ;;
    /var/*) alternate="/private$path" ;;
  esac
  if [[ -n "${alternate:-}" ]]; then
    printf '%s (also %s)\n' "$path" "$alternate"
  else
    printf '%s\n' "$path"
  fi
}

collect_restack_plan() {
  local parent="$1" child
  while IFS= read -r child; do
    [[ -n "$child" ]] || continue
    branch_exists "$child" || continue
    printf '%s\t%s\n' "$child" "$parent"
    collect_restack_plan "$child"
  done <<< "$(get_children "$parent")"
}

collect_reparent_plan() {
  local old_parent="$1" new_parent="$2" child
  while IFS= read -r child; do
    [[ -n "$child" ]] || continue
    branch_exists "$child" || continue
    printf '%s\t%s\n' "$child" "$new_parent"
    collect_restack_plan "$child"
  done <<< "$(get_children "$old_parent")"
}

validate_restack_bases() {
  local root="$1" child parent base
  while IFS=$'\t' read -r child parent; do
    [[ -n "$child" ]] || continue
    base="$(get_base_oid "$child" 2>/dev/null || true)"
    if [[ -z "$base" ]] && ! git merge-base --is-ancestor "$parent" "$child" 2>/dev/null; then
      printf "${RED}error:${RESET} no recorded base for '%s'; refusing to guess after '%s' changed history\n" "$child" "$parent" >&2
      return 1
    fi
  done <<< "$(collect_restack_plan "$root")"
}

would_create_stack_cycle() {
  local branch="$1" parent="$2" seen=" $branch "
  while [[ -n "$parent" ]]; do
    [[ "$seen" != *" $parent "* ]] || return 0
    seen="$seen$parent "
    parent="$(get_parent "$parent" 2>/dev/null || true)"
  done
  return 1
}

operation_dir() {
  printf '%s\n' "$(gs_dir)/operation"
}

journal_value() {
  sed -n "s/^$1=//p" "$(operation_dir)/journal" | head -1
}

finalizer_value() {
  sed -n "s/^$1=//p" "$(operation_dir)/finalizer" | head -1
}

set_finalizer_value() {
  local key="$1" value="$2" finalizer="$(operation_dir)/finalizer" updated
  updated="$(awk -v key="$key" -v value="$value" '
    BEGIN { found = 0 }
    index($0, key "=") == 1 { print key "=" value; found = 1; next }
    { print }
    END { if (!found) print key "=" value }
  ' "$finalizer")"
  atomic_write "$finalizer" "$updated"
}

step_value() {
  sed -n "s/^$2=//p" "$(operation_dir)/steps/$1" | head -1
}

write_restack_journal_at() {
  local op="$1"
  shift
  local status="$1" index="$2" branch="${3:-}" parent="${4:-}"
  local executor="${5:-}" temporary="${6:-0}" old_oid="${7:-}" old_parent_oid="${8:-}"
  local total caller stash
  total="$(find "$op/steps" -type f 2>/dev/null | wc -l | tr -d ' ')"
  caller="$(cat "$op/caller")"
  stash="$(cat "$op/stash" 2>/dev/null || true)"
  atomic_write "$op/journal" "operation=restack
status=$status
current_step=$index
total_steps=$total
branch=$branch
new_parent=$parent
executor_path=$executor
temporary_executor=$temporary
old_branch_oid=$old_oid
old_parent_oid=$old_parent_oid
caller_path=$caller
stash_path=$stash"
}

write_restack_journal() {
  write_restack_journal_at "$(operation_dir)" "$@"
}

mark_step_complete() {
  local step="$(operation_dir)/steps/$1" value
  value="$(sed 's/^completed=.*/completed=yes/' "$step")"
  atomic_write "$step" "$value"
}

create_executor_worktree() {
  local branch="$1" path
  path="$(mktemp -d "${TMPDIR:-/tmp}/gs-executor.XXXXXX")"
  rmdir "$path"
  if ! git worktree add --quiet "$path" "$branch"; then
    die "could not create a temporary executor worktree for '$branch'"
  fi
  printf '%s\n' "$path"
}

remove_executor_worktree() {
  local path="$1" temporary="$2"
  [[ "$temporary" == "1" ]] || return 0
  git worktree remove --force "$path" >/dev/null 2>&1 ||
    warn "could not remove temporary executor worktree '$path'"
}

finish_restack_operation() {
  local outcome="${1:-success}" op stash_path stash_oid stash_ref
  op="$(operation_dir)"
  stash_path="$(cat "$op/stash" 2>/dev/null || true)"
  if [[ -n "$stash_path" ]]; then
    stash_oid="$(cat "$op/stash_oid" 2>/dev/null || true)"
    if [[ "$(journal_value status)" == "autostash_conflict" ]]; then
      [[ -z "$(git -C "$stash_path" ls-files -u)" ]] || {
        warn "autostash conflicts remain in '$stash_path'; resolve them before continuing"
        return 1
      }
      stash_ref="$(git -C "$stash_path" stash list --format='%gd %H' | awk -v oid="$stash_oid" '$2 == oid { print $1; exit }')"
      [[ -z "$stash_ref" ]] || git -C "$stash_path" stash drop --quiet "$stash_ref"
      : > "$op/stash"
      : > "$op/stash_oid"
    elif [[ -n "$stash_oid" ]] && git -C "$stash_path" stash apply --quiet "$stash_oid"; then
      stash_ref="$(git -C "$stash_path" stash list --format='%gd %H' | awk -v oid="$stash_oid" '$2 == oid { print $1; exit }')"
      [[ -z "$stash_ref" ]] || git -C "$stash_path" stash drop --quiet "$stash_ref"
    else
      warn "autostash restore hit a conflict in '$stash_path'; the recorded stash remains available"
      write_restack_journal autostash_conflict "$(journal_value current_step)"
      warn "the gs operation journal was retained; resolve the worktree and run 'gs restack --continue'"
      return 1
    fi
  fi
  run_operation_finalizer "$outcome"
  rm -rf "$op"
}

run_operation_finalizer() {
  local outcome="$1" op finalizer type branch parent parent_old_oid owner cleanup_done tracking_done restored
  op="$(operation_dir)"
  finalizer="$op/finalizer"
  [[ -f "$finalizer" ]] || return 0
  type="$(sed -n 's/^type=//p' "$finalizer" | head -1)"
  case "$type" in
    fold|land) ;;
    *) die "unknown operation finalizer '$type'" ;;
  esac
  branch="$(sed -n 's/^branch=//p' "$finalizer" | head -1)"
  parent="$(sed -n 's/^parent=//p' "$finalizer" | head -1)"
  parent_old_oid="$(sed -n 's/^parent_old_oid=//p' "$finalizer" | head -1)"

  if [[ "$outcome" == "abort" ]]; then
    if [[ "$type" == "fold" ]] && [[ "$(finalizer_value local_mutation_done)" == "yes" ]]; then
      restored="$(finalizer_value local_restore_done)"
      if [[ "$restored" != "yes" ]]; then
        restore_branch_tip "$parent" "$parent_old_oid"
        set_finalizer_value local_restore_done yes
      fi
    elif [[ "$type" == "land" ]] && [[ "$(finalizer_value remote_merge_done)" == "yes" ]]; then
      warn "the PR for '$branch' was already merged remotely; abort restored local restacks only and cannot undo that merge"
    fi
    return 0
  fi

  owner="$(branch_owner_path "$branch" 2>/dev/null || true)"
  cleanup_done="$(finalizer_value branch_cleanup_done)"
  if [[ "$cleanup_done" != "yes" ]]; then
    if [[ -n "$owner" ]]; then
      info "left '$branch' and its worktree intact at '$(display_worktree_path "$owner")'; removed gs tracking"
    elif branch_exists "$branch"; then
      delete_unowned_branch "$branch" "$parent" || die "could not delete $type branch '$branch'"
    fi
    set_finalizer_value branch_cleanup_done yes
  fi

  tracking_done="$(finalizer_value tracking_cleanup_done)"
  if [[ "$tracking_done" != "yes" ]]; then
    remove_tracking "$branch"
    set_finalizer_value tracking_cleanup_done yes
  fi
}

preflight_restack_plan() {
  local plan="$1" caller="$2" autostash="$3" child parent owner owner_display dirty
  while IFS=$'\t' read -r child parent; do
    [[ -n "$child" ]] || continue
    owner="$(branch_owner_path "$child" 2>/dev/null || true)"
    [[ -n "$owner" ]] || continue
    owner_display="$(display_worktree_path "$owner")"
    if worktree_has_git_operation "$owner"; then
      printf "${RED}error:${RESET} cannot restack '%s': Git operation already in progress at '%s'\n" "$child" "$owner_display" >&2
      return 1
    fi
    dirty="$(git -C "$owner" status --porcelain --untracked-files=normal 2>/dev/null)"
    if [[ -n "$dirty" ]] && ! { [[ "$autostash" == "1" ]] && [[ "$owner" == "$caller" ]]; }; then
      printf "${RED}error:${RESET} cannot restack '%s': owning worktree is dirty at '%s'\n" "$child" "$owner_display" >&2
      return 1
    fi
  done < "$plan"
}

prepare_restack_operation() {
  local root="$1" autostash="$2" source_plan="${3:-}" finalizer_content="${4:-}"
  local op tmp plan caller child parent fork old_oid parent_oid old_parent old_base index=0 step
  local old_parent_present old_base_present
  op="$(operation_dir)"
  [[ ! -e "$op" ]] || die "a gs operation is already in progress; run 'gs status'"
  tmp="${op}.tmp.$$"
  mkdir "$tmp" 2>/dev/null || die "could not create gs operation journal"
  mkdir -p "$tmp/steps"
  plan="$tmp/plan"
  if [[ -n "$source_plan" ]]; then
    cp "$source_plan" "$plan"
  else
    collect_restack_plan "$root" > "$plan"
  fi
  caller="$(pwd -P)"
  printf '%s\n' "$caller" > "$tmp/caller"
  : > "$tmp/stash"
  : > "$tmp/stash_oid"

  if ! preflight_restack_plan "$plan" "$caller" "$autostash"; then
    rm -rf "$tmp"
    die "restack preflight failed; no branches were changed"
  fi

  while IFS=$'\t' read -r child parent; do
    [[ -n "$child" ]] || continue
    old_oid="$(git rev-parse "$child")"
    parent_oid="$(git rev-parse "$parent")"
    if is_tracked "$child"; then
      old_parent_present=yes
      old_parent="$(get_parent "$child")"
    else
      old_parent_present=no
      old_parent=""
    fi
    old_base="$(get_base_oid "$child" 2>/dev/null || true)"
    if [[ -n "$old_base" ]]; then old_base_present=yes; else old_base_present=no; fi
    fork="$old_base"
    if [[ -z "$fork" ]]; then
      if git merge-base --is-ancestor "$parent" "$child" 2>/dev/null; then
        fork="$parent_oid"
      else
        rm -rf "$tmp"
        die "no recorded base for '$child'. Refusing to guess after '$parent' changed history. Re-track the branch after verifying its parent."
      fi
    fi
    index=$((index + 1))
    printf -v step '%06d' "$index"
    atomic_write "$tmp/steps/$step" "branch=$child
parent=$parent
fork=$fork
old_branch_oid=$old_oid
old_parent_oid=$parent_oid
old_parent_present=$old_parent_present
old_parent_name=$old_parent
old_base_present=$old_base_present
old_base_oid=$old_base
completed=no"
  done < "$plan"

  if [[ -n "$finalizer_content" ]]; then
    atomic_write "$tmp/finalizer" "$finalizer_content"
  fi
  write_restack_journal_at "$tmp" prepared 1
  mv "$tmp" "$op" || { rm -rf "$tmp"; die "could not publish gs operation journal"; }

  if [[ "$autostash" == "1" ]] && [[ -n "$(git status --porcelain --untracked-files=normal)" ]]; then
    git stash push -u --quiet -m "gs-restack-autostash" || die "autostash failed; the operation journal was retained"
    printf '%s\n' "$caller" > "$op/stash"
    git rev-parse refs/stash > "$op/stash_oid"
  fi
  write_restack_journal running 1
}

execute_restack_steps() {
  local index total step child parent fork old_oid old_parent_oid executor temporary
  index="$(journal_value current_step)"
  total="$(journal_value total_steps)"
  while [[ "$index" -le "$total" ]]; do
    printf -v step '%06d' "$index"
    child="$(step_value "$step" branch)"
    parent="$(step_value "$step" parent)"
    fork="$(step_value "$step" fork)"
    old_oid="$(step_value "$step" old_branch_oid)"
    old_parent_oid="$(step_value "$step" old_parent_oid)"

    if git merge-base --is-ancestor "$parent" "$child" 2>/dev/null; then
      info "'$child' is already up to date with '$parent'"
      set_parent "$child" "$parent"
      set_base_oid "$child" "$(git rev-parse "$parent")"
      mark_step_complete "$step"
      index=$((index + 1))
      write_restack_journal running "$index"
      continue
    fi

    executor="$(branch_owner_path "$child" 2>/dev/null || true)"
    temporary=0
    if [[ -z "$executor" ]]; then
      executor="$(create_executor_worktree "$child")"
      temporary=1
    fi
    write_restack_journal running "$index" "$child" "$parent" "$executor" "$temporary" "$old_oid" "$old_parent_oid"
    info "rebasing '$child' onto '$parent' in '$executor'..."

    if ! git -C "$executor" rebase --onto "$parent" "$fork" --quiet; then
      write_restack_journal conflict "$index" "$child" "$parent" "$executor" "$temporary" "$old_oid" "$old_parent_oid"
      printf "\n${RED}conflict detected${RESET} while rebasing '${YELLOW}$child${RESET}' onto '${YELLOW}$parent${RESET}'\n"
      echo "Resolve conflicts in: $executor"
      echo "Then run 'gs restack --continue' from any linked worktree."
      return 1
    fi

    git merge-base --is-ancestor "$parent" "$child" 2>/dev/null ||
      die "rebase finished but '$child' is not based on '$parent'"
    set_parent "$child" "$parent"
    set_base_oid "$child" "$(git rev-parse "$parent")"
    mark_step_complete "$step"
    remove_executor_worktree "$executor" "$temporary"
    index=$((index + 1))
    write_restack_journal running "$index"
  done
  finish_restack_operation
}

run_operation_prerequisites() {
  local type branch parent parent_old_oid executor strategy pr_state
  [[ -f "$(operation_dir)/finalizer" ]] || return 0
  type="$(finalizer_value type)"
  branch="$(finalizer_value branch)"
  parent="$(finalizer_value parent)"

  case "$type" in
    fold)
      [[ "$(finalizer_value local_mutation_done)" != "yes" ]] || return 0
      parent_old_oid="$(finalizer_value parent_old_oid)"
      executor="$(branch_owner_path "$parent" 2>/dev/null || true)"
      local temporary=0
      if [[ -z "$executor" ]]; then
        executor="$(create_executor_worktree "$parent")"
        temporary=1
      fi
      if [[ "$(git rev-parse "$parent")" != "$parent_old_oid" ]]; then
        remove_executor_worktree "$executor" "$temporary"
        set_finalizer_value local_mutation_done yes
        return 0
      fi
      info "merging '$branch' into '$parent' in '$executor'..."
      if [[ -z "$(git -C "$executor" status --porcelain --untracked-files=normal)" ]]; then
        git -C "$executor" merge --squash "$branch" --quiet || {
          git -C "$executor" reset --hard "$parent_old_oid" --quiet >/dev/null 2>&1 || true
          remove_executor_worktree "$executor" "$temporary"
          warn "could not squash-merge '$branch' into '$parent'; the operation journal was retained"
          return 1
        }
      fi
      if ! git -C "$executor" commit --no-edit --quiet; then
        git -C "$executor" reset --hard "$parent_old_oid" --quiet >/dev/null 2>&1 || true
        remove_executor_worktree "$executor" "$temporary"
        warn "could not squash-merge '$branch' into '$parent'; the operation journal was retained"
        return 1
      fi
      remove_executor_worktree "$executor" "$temporary"
      set_finalizer_value local_mutation_done yes
      ;;
    land)
      if [[ "$(finalizer_value remote_merge_done)" != "yes" ]]; then
        pr_state="$(gh pr view "$branch" --json state --jq '.state' 2>/dev/null || true)"
        if [[ "$pr_state" == "MERGED" ]]; then
          set_finalizer_value remote_merge_done yes
        else
          [[ "$pr_state" == "OPEN" ]] || { warn "cannot resume land: PR for '$branch' has state '${pr_state:-unknown}'"; return 1; }
          strategy="$(finalizer_value strategy)"
          executor="$(create_detached_executor_worktree "$parent")"
          info "merging PR for '$branch' into '$parent' ($strategy)..."
          if ! git -C "$executor" status --short >/dev/null ||
             ! (cd "$executor" && gh pr merge "$branch" "$strategy" --delete-branch 2>&1 | sed 's/^/  /'); then
            remove_executor_worktree "$executor" 1
            warn "failed to merge PR for '$branch'; the operation journal was retained"
            return 1
          fi
          remove_executor_worktree "$executor" 1
          set_finalizer_value remote_merge_done yes
        fi
      fi
      if [[ "$(finalizer_value parent_update_done)" != "yes" ]]; then
        info "updating '$parent'..."
        if ! update_branch_from_origin "$parent"; then
          warn "PR for '$branch' is merged remotely, but '$parent' could not be fast-forwarded"
          warn "the remote merge is irreversible here; the operation journal was retained for 'gs restack --continue'"
          return 1
        fi
        set_finalizer_value parent_update_done yes
      fi
      ;;
  esac
}

restack_upstack() {
  prepare_restack_operation "$1" 0
  execute_restack_steps
}

restack_continue() {
  local op status executor child parent temporary index step
  op="$(operation_dir)"
  [[ -f "$op/journal" ]] || die "no restack in progress"
  status="$(journal_value status)"
  if [[ "$status" == "autostash_conflict" ]]; then
    finish_restack_operation
    success "restack continued and completed"
    return
  fi
  run_operation_prerequisites || return 1

  executor="$(journal_value executor_path)"
  child="$(journal_value branch)"
  parent="$(journal_value new_parent)"
  temporary="$(journal_value temporary_executor)"
  index="$(journal_value current_step)"
  printf -v step '%06d' "$index"
  if [[ "$(step_value "$step" completed)" == "yes" ]]; then
    [[ -z "$executor" ]] || remove_executor_worktree "$executor" "$temporary"
    index=$((index + 1))
    write_restack_journal running "$index"
    execute_restack_steps
    success "restack continued and completed"
    return
  fi
  if [[ -z "$child" ]]; then
    execute_restack_steps
    success "restack continued and completed"
    return
  fi
  [[ -n "$executor" && -d "$executor" ]] || die "recorded restack executor is missing: '$executor'"

  if worktree_has_git_operation "$executor"; then
    git -C "$executor" rebase --continue || {
      echo "Conflicts remain in '$executor'. Resolve them and retry."
      return 1
    }
  elif ! git merge-base --is-ancestor "$parent" "$child" 2>/dev/null; then
    die "no rebase is active in '$executor', and '$child' is not based on '$parent'"
  fi

  set_parent "$child" "$parent"
  set_base_oid "$child" "$(git rev-parse "$parent")"
  mark_step_complete "$step"
  remove_executor_worktree "$executor" "$temporary"
  index=$((index + 1))
  write_restack_journal running "$index"
  execute_restack_steps
  success "restack continued and completed"
}

restore_step_metadata() {
  local step="$1" branch old_parent_present old_parent_name old_base_present old_base_oid
  branch="$(sed -n 's/^branch=//p' "$step" | head -1)"
  old_parent_present="$(sed -n 's/^old_parent_present=//p' "$step" | head -1)"
  old_parent_name="$(sed -n 's/^old_parent_name=//p' "$step" | head -1)"
  old_base_present="$(sed -n 's/^old_base_present=//p' "$step" | head -1)"
  old_base_oid="$(sed -n 's/^old_base_oid=//p' "$step" | head -1)"
  if [[ "$old_parent_present" == "yes" ]]; then
    set_parent "$branch" "$old_parent_name"
  else
    rm -f "$(gs_dir)/branches/$(encode_branch "$branch")"
  fi
  if [[ "$old_base_present" == "yes" ]]; then
    set_base_oid "$branch" "$old_base_oid"
  else
    rm -f "$(gs_dir)/bases/$(encode_branch "$branch")"
  fi
}

restore_branch_tip() {
  local branch="$1" oid="$2" owner executor temporary=0
  owner="$(branch_owner_path "$branch" 2>/dev/null || true)"
  if [[ -n "$owner" ]]; then
    [[ -z "$(git -C "$owner" status --porcelain --untracked-files=normal)" ]] ||
      die "cannot restore '$branch': owning worktree became dirty at '$owner'"
    git -C "$owner" reset --hard "$oid" --quiet || die "could not restore '$branch' in '$owner'"
    return 0
  fi
  executor="$(create_executor_worktree "$branch")"
  temporary=1
  git -C "$executor" reset --hard "$oid" --quiet || die "could not restore '$branch'"
  remove_executor_worktree "$executor" "$temporary"
}

restack_abort() {
  local op executor temporary child old_oid step completed branch index current_step_restored=0
  op="$(operation_dir)"
  [[ -f "$op/journal" ]] || die "no restack in progress"
  executor="$(journal_value executor_path)"
  temporary="$(journal_value temporary_executor)"
  child="$(journal_value branch)"
  old_oid="$(journal_value old_branch_oid)"

  if [[ -n "$executor" && -d "$executor" ]] && worktree_has_git_operation "$executor"; then
    git -C "$executor" rebase --abort || die "could not abort rebase in '$executor'"
  fi
  if [[ -n "$child" && -n "$old_oid" ]] && [[ "$(git rev-parse "$child" 2>/dev/null)" != "$old_oid" ]]; then
    restore_branch_tip "$child" "$old_oid"
    index="$(journal_value current_step)"
    printf -v step '%06d' "$index"
    restore_step_metadata "$op/steps/$step"
    current_step_restored=1
  fi
  [[ -n "$executor" ]] && remove_executor_worktree "$executor" "$temporary"

  # Restore completed branches from the top of the stack downward. Using each
  # owning worktree keeps checked-out refs under Git's normal safety rules.
  for step in $(find "$op/steps" -type f -maxdepth 1 2>/dev/null | sort -r); do
    completed="$(sed -n 's/^completed=//p' "$step" | tail -1)"
    [[ "$completed" == "yes" ]] || continue
    branch="$(sed -n 's/^branch=//p' "$step" | head -1)"
    old_oid="$(sed -n 's/^old_branch_oid=//p' "$step" | head -1)"
    if [[ "$current_step_restored" == "1" ]] && [[ "$branch" == "$child" ]]; then continue; fi
    restore_branch_tip "$branch" "$old_oid"
    restore_step_metadata "$step"
  done
  finish_restack_operation abort
  success "restack aborted"
}

cmd_restack() {
  ensure_gs_init
  local mode="upstack" autostash=0 action=start
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --upstack) mode="upstack" ;;
      --all) mode="all" ;;
      --autostash) autostash=1 ;;
      --continue) action=continue ;;
      --abort) action=abort ;;
      *) die "unknown argument: $1" ;;
    esac
    shift
  done
  case "$action" in
    continue) restack_continue; return ;;
    abort) restack_abort; return ;;
  esac
  if [[ "$mode" == "all" ]]; then
    prepare_restack_operation "$(trunk_branch)" "$autostash"
  else
    prepare_restack_operation "$(current_branch)" "$autostash"
  fi
  execute_restack_steps
  success "restack complete"
}

cmd_status() {
  ensure_gs_init
  local journal="$(operation_dir)/journal"
  if [[ ! -f "$journal" ]]; then
    echo "no gs operation in progress"
    return 0
  fi
  cat "$journal"
}

guard_command_against_active_operation() {
  local command="$1" action="${2:-}" op
  git rev-parse --git-dir >/dev/null 2>&1 || return 0
  op="$(operation_dir)"
  [[ -d "$op" ]] || return 0
  case "$command:$action" in
    status:*|ls:*|list:*|log:*|diff:*|help:*|-h:*|--help:*|restack:--continue|restack:--abort) return 0 ;;
  esac
  die "a gs operation is already in progress; run 'gs status', 'gs restack --continue', or 'gs restack --abort'"
}

command_mutates_repository() {
  case "$1" in
    init|create|track|stack|commit|restack|move|insert|untrack|fold|split|land|delete|rename|sync) return 0 ;;
  esac
  return 1
}

release_mutation_lock() {
  if [[ -n "${GS_MUTATION_LOCK:-}" ]] && [[ "$(cat "$GS_MUTATION_LOCK/pid" 2>/dev/null || true)" == "$$" ]]; then
    rm -f "$GS_MUTATION_LOCK/pid"
    rmdir "$GS_MUTATION_LOCK" 2>/dev/null || true
  fi
}

acquire_mutation_lock() {
  local command="$1" lock
  command_mutates_repository "$command" || return 0
  git rev-parse --git-dir >/dev/null 2>&1 || return 0
  lock="$(git_common_dir)/gs-mutation.lock"
  if ! mkdir "$lock" 2>/dev/null; then
    local owner_pid
    owner_pid="$(cat "$lock/pid" 2>/dev/null || true)"
    if [[ -n "$owner_pid" ]] && ! kill -0 "$owner_pid" 2>/dev/null; then
      rm -f "$lock/pid"
      rmdir "$lock" 2>/dev/null || die "could not recover stale gs mutation lock at '$lock'"
      mkdir "$lock" || die "another gs mutation is running in this repository"
    else
      die "another gs mutation is running in this repository"
    fi
  fi
  printf '%s\n' "$$" > "$lock/pid"
  GS_MUTATION_LOCK="$lock"
  trap release_mutation_lock EXIT INT TERM
}

checkout_navigation_target() {
  local branch="$1" owner
  owner="$(branch_owner_path "$branch" 2>/dev/null || true)"
  if [[ -n "$owner" && "$owner" != "$(pwd -P)" ]]; then
    die "branch '$branch' is already checked out in worktree '$owner'"
  fi
  git checkout "$branch" --quiet
}

cleanup_restack_tips() {
  :
}

cmd_move() {
  ensure_gs_init
  local target="" cur old_parent fork descendants=() child
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --onto) shift; target="${1:-}"; [[ -n "$target" ]] || die "--onto requires a branch" ;;
      *) die "usage: gs move --onto <target>" ;;
    esac
    shift
  done
  [[ -n "$target" ]] || die "usage: gs move --onto <target>"
  branch_exists "$target" || die "branch '$target' does not exist"
  cur="$(current_branch)"
  is_tracked "$cur" || die "'$cur' is not tracked by gs"
  old_parent="$(get_parent "$cur")"
  fork="$(get_base_oid "$cur" 2>/dev/null || true)"
  [[ -n "$fork" ]] || die "no recorded base for '$cur'; re-track it after verifying '$old_parent'"
  while IFS= read -r child; do [[ -n "$child" ]] && descendants+=("$child"); done <<< "$(collect_descendants_bfs "$cur")"
  preflight_owned_branches "$cur" "${descendants[@]}" || die "move preflight failed; no branches were changed"

  info "rebasing '$cur' onto '$target'..."
  if ! git rebase --onto "$target" "$fork" "$cur" --quiet; then
    git rebase --abort >/dev/null 2>&1 || true
    die "rebase failed in '$(pwd -P)'; resolve or abort it. Stack metadata was not changed."
  fi
  set_parent "$cur" "$target"
  set_base_oid "$cur" "$(git rev-parse "$target")"
  info "restacking upstack branches..."
  restack_upstack "$cur"
  success "moved '$cur' onto '$target'"
}

# Commands below replace the legacy single-worktree implementations in gs.
# They inspect every owning worktree before the first mutation, then execute
# branch-changing Git commands where that branch is checked out.
preflight_owned_branches() {
  local branch owner owner_display dirty checked=()
  for branch in "$@"; do
    [[ -n "$branch" ]] || continue
    is_in_list "$branch" "${checked[@]}" && continue
    checked+=("$branch")
    owner="$(branch_owner_path "$branch" 2>/dev/null || true)"
    [[ -n "$owner" ]] || continue
    owner_display="$(display_worktree_path "$owner")"
    if worktree_has_git_operation "$owner"; then
      printf "${RED}error:${RESET} cannot modify '%s': Git operation already in progress at '%s'\n" "$branch" "$owner_display" >&2
      return 1
    fi
    dirty="$(git -C "$owner" status --porcelain --untracked-files=normal 2>/dev/null)"
    if [[ -n "$dirty" ]]; then
      printf "${RED}error:${RESET} cannot modify '%s': owning worktree is dirty at '%s'\n" "$branch" "$owner_display" >&2
      return 1
    fi
  done
}

# Some commands intentionally consume changes in the caller, or only rename
# its checked-out ref. They still need every other owner clean before the first
# mutation, but rejecting the caller's expected changes would break the command.
preflight_owned_branches_allow_dirty_path() {
  local allowed_path="$1" branch owner owner_display dirty checked=()
  shift
  for branch in "$@"; do
    [[ -n "$branch" ]] || continue
    is_in_list "$branch" "${checked[@]}" && continue
    checked+=("$branch")
    owner="$(branch_owner_path "$branch" 2>/dev/null || true)"
    [[ -n "$owner" ]] || continue
    owner_display="$(display_worktree_path "$owner")"
    if worktree_has_git_operation "$owner"; then
      printf "${RED}error:${RESET} cannot modify '%s': Git operation already in progress at '%s'\n" "$branch" "$owner_display" >&2
      return 1
    fi
    dirty="$(git -C "$owner" status --porcelain --untracked-files=normal 2>/dev/null)"
    if [[ -n "$dirty" && "$owner" != "$allowed_path" ]]; then
      printf "${RED}error:${RESET} cannot modify '%s': owning worktree is dirty at '%s'\n" "$branch" "$owner_display" >&2
      return 1
    fi
  done
}

create_detached_executor_worktree() {
  local ref="$1" path
  path="$(mktemp -d "${TMPDIR:-/tmp}/gs-executor.XXXXXX")"
  rmdir "$path"
  if ! git worktree add --detach --quiet "$path" "$ref"; then
    die "could not create a temporary executor worktree at '$ref'"
  fi
  printf '%s\n' "$path"
}

update_branch_from_origin() {
  local branch="$1" executor temporary=0
  executor="$(branch_owner_path "$branch" 2>/dev/null || true)"
  if [[ -z "$executor" ]]; then
    executor="$(create_executor_worktree "$branch")"
    temporary=1
  fi
  if ! git -C "$executor" pull --ff-only --quiet origin "$branch"; then
    remove_executor_worktree "$executor" "$temporary"
    return 1
  fi
  remove_executor_worktree "$executor" "$temporary"
}

rebase_branch_in_executor() {
  local branch="$1" parent="$2" fork="$3" executor temporary=0
  executor="$(branch_owner_path "$branch" 2>/dev/null || true)"
  if [[ -z "$executor" ]]; then
    executor="$(create_executor_worktree "$branch")"
    temporary=1
  fi
  info "rebasing '$branch' onto '$parent' in '$executor'..."
  if ! git -C "$executor" rebase --onto "$parent" "$fork" --quiet; then
    git -C "$executor" rebase --abort >/dev/null 2>&1 || true
    remove_executor_worktree "$executor" "$temporary"
    warn "could not rebase '$branch' onto '$parent'; the rebase was aborted"
    return 1
  fi
  remove_executor_worktree "$executor" "$temporary"
  git merge-base --is-ancestor "$parent" "$branch" 2>/dev/null
}

delete_unowned_branch() {
  local branch="$1" fallback="$2" executor
  executor="$(create_detached_executor_worktree "$fallback")"
  if ! git -C "$executor" branch -D "$branch" --quiet; then
    remove_executor_worktree "$executor" 1
    return 1
  fi
  remove_executor_worktree "$executor" 1
}

resolved_parent_after_merges() {
  local branch="$1" trunk="$2" parent
  shift 2
  parent="$(get_parent "$branch" 2>/dev/null || true)"
  [[ -n "$parent" ]] || parent="$trunk"
  while is_in_list "$parent" "$@"; do
    parent="$(get_parent "$parent" 2>/dev/null || true)"
    [[ -n "$parent" ]] || parent="$trunk"
  done
  printf '%s\n' "$parent"
}

cmd_create() {
  ensure_gs_init
  local name="" message="" parent trunk caller
  while [[ $# -gt 0 ]]; do
    case "$1" in
      -m) shift; message="${1:-}"; [[ -n "$message" ]] || die "-m requires a message" ;;
      -*) die "unknown flag: $1" ;;
      *) name="$1" ;;
    esac
    shift
  done
  [[ -n "$name" ]] || die "usage: gs create <name> [-m \"message\"]"
  branch_exists "$name" && die "branch '$name' already exists"

  parent="$(current_branch)"
  caller="$(pwd -P)"
  preflight_owned_branches_allow_dirty_path "$caller" "$parent" ||
    die "create preflight failed; no branches were changed"

  git checkout -b "$name" --quiet ||
    die "could not create and check out '$name' in '$caller'; gs metadata was not changed"
  if [[ -n "$message" ]]; then
    if ! git commit -m "$message" --allow-empty --quiet; then
      git checkout "$parent" --quiet >/dev/null 2>&1 || true
      git branch -D "$name" --quiet 2>/dev/null || true
      die "commit failed; branch '$name' was removed and gs metadata was not changed"
    fi
  fi

  track_branch "$name" "$parent"
  trunk="$(trunk_branch)"
  if [[ "$parent" != "$trunk" ]] && ! is_tracked "$parent"; then
    track_branch "$parent" "$trunk"
    info "auto-tracked parent '$parent' onto '$trunk'"
  fi
  success "created branch '$name' stacked on '$parent'"
}

cmd_track() {
  ensure_gs_init
  local onto="" trunk parent initial_parent b fork i
  local branches=() parents=() forks=() old_oids=() completed=() affected=() descendants=()
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --onto) shift; onto="${1:-}"; [[ -n "$onto" ]] || die "--onto requires a branch name" ;;
      -*) die "unknown flag: $1" ;;
      *) branches+=("$1") ;;
    esac
    shift
  done
  [[ ${#branches[@]} -gt 0 ]] || die "usage: gs track <branch1> [branch2] ... [--onto <branch>]"

  trunk="$(trunk_branch)"
  parent="${onto:-$trunk}"
  initial_parent="$parent"
  [[ "$parent" == "$trunk" ]] || branch_exists "$parent" || die "branch '$parent' does not exist"

  # Capture every fork before any lower branch can be rewritten. A recorded
  # base is the durable boundary; merge-base is safe only for new tracking.
  for b in "${branches[@]}"; do
    branch_exists "$b" || die "branch '$b' does not exist"
    parents+=("$parent")
    if is_tracked "$b"; then
      fork="$(get_base_oid "$b" 2>/dev/null || true)"
      [[ -n "$fork" ]] || die "no recorded base for '$b'; re-track it after verifying its current parent"
    else
      fork="$(git merge-base "$b" "$parent" 2>/dev/null || true)"
      [[ -n "$fork" ]] || die "could not determine where '$b' forks from '$parent'"
    fi
    forks+=("$fork")
    old_oids+=("$(git rev-parse "$b")")
    affected+=("$b")
    while IFS= read -r fork; do [[ -n "$fork" ]] && affected+=("$fork"); done <<< "$(collect_descendants_bfs "$b")"
    parent="$b"
  done
  preflight_owned_branches "${affected[@]}" || die "track preflight failed; no branches were changed"

  for ((i = 0; i < ${#branches[@]}; i++)); do
    b="${branches[$i]}"
    parent="${parents[$i]}"
    fork="${forks[$i]}"
    if ! git merge-base --is-ancestor "$parent" "$b" 2>/dev/null; then
      rebase_branch_in_executor "$b" "$parent" "$fork" ||
        {
          local j
          for ((j = ${#completed[@]} - 1; j >= 0; j--)); do
            restore_branch_tip "${completed[$j]}" "${old_oids[$j]}"
          done
          die "could not track '$b' onto '$parent'; earlier rebases were restored and gs metadata was not changed"
        }
    fi
    completed+=("$b")
  done

  for ((i = 0; i < ${#branches[@]}; i++)); do
    b="${branches[$i]}"
    parent="${parents[$i]}"
    set_parent "$b" "$parent"
    set_base_oid "$b" "$(git rev-parse "$parent")"
    info "tracked '$b' onto '$parent'"
  done

  info "restacking tracked branches..."
  restack_upstack "$initial_parent"
  success "tracked ${#branches[@]} branch(es)"
}

cmd_stack() {
  ensure_gs_init
  local branch="${1:-}" cur
  [[ -n "$branch" ]] || die "usage: gs stack <branch>"
  branch_exists "$branch" || die "branch '$branch' does not exist"
  cur="$(current_branch)"
  [[ "$branch" != "$cur" ]] || die "cannot stack '$branch' onto itself"
  would_create_stack_cycle "$branch" "$cur" && die "stacking '$branch' onto '$cur' would create a cycle"
  git merge-base "$branch" "$cur" >/dev/null 2>&1 || die "branches '$branch' and '$cur' do not share history"
  preflight_owned_branches "$branch" || die "stack preflight failed; gs metadata was not changed"
  track_branch "$branch" "$cur"
  success "stacked '$branch' onto '$cur'"
}

cmd_commit() {
  ensure_gs_init
  local cur caller branch
  local args=() affected=()
  while [[ $# -gt 0 ]]; do
    args+=("$1")
    shift
  done
  cur="$(current_branch)"
  caller="$(pwd -P)"
  affected+=("$cur")
  while IFS= read -r branch; do [[ -n "$branch" ]] && affected+=("$branch"); done <<< "$(collect_descendants_bfs "$cur")"
  preflight_owned_branches_allow_dirty_path "$caller" "${affected[@]}" ||
    die "commit preflight failed; no commit was created"
  validate_restack_bases "$cur" || die "commit preflight failed; no commit was created"

  git commit "${args[@]}"
  info "restacking upstack branches..."
  restack_upstack "$cur"
  success "commit done and upstack restacked"
}

cmd_insert() {
  ensure_gs_init
  local name="" parent="" child="" trunk actual_parent fork caller branch
  local affected=()
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --between)
        shift; parent="${1:-}"; shift; child="${1:-}"
        [[ -n "$parent" && -n "$child" ]] || die "--between requires two branches: <parent> <child>"
        ;;
      -*) die "unknown flag: $1" ;;
      *) name="$1" ;;
    esac
    shift
  done
  [[ -n "$name" && -n "$parent" && -n "$child" ]] || die "usage: gs insert <name> --between <parent> <child>"
  branch_exists "$name" && die "branch '$name' already exists"
  trunk="$(trunk_branch)"
  [[ "$parent" == "$trunk" ]] || branch_exists "$parent" || die "branch '$parent' does not exist"
  branch_exists "$child" || die "branch '$child' does not exist"
  is_tracked "$child" || die "'$child' is not tracked by gs"
  actual_parent="$(get_parent "$child" 2>/dev/null || true)"
  [[ "$actual_parent" == "$parent" ]] || die "'$child' is stacked on '$actual_parent', not '$parent' — use 'gs move --onto' if you want to reparent it"

  fork="$(get_base_oid "$child" 2>/dev/null || true)"
  if [[ -z "$fork" ]]; then
    git merge-base --is-ancestor "$parent" "$child" 2>/dev/null ||
      die "no recorded base for '$child'; re-track it after verifying '$parent'"
    fork="$(git rev-parse "$parent")"
  fi
  caller="$(current_branch)"
  affected+=("$caller" "$child")
  while IFS= read -r branch; do [[ -n "$branch" ]] && affected+=("$branch"); done <<< "$(collect_descendants_bfs "$child")"
  preflight_owned_branches "${affected[@]}" || die "insert preflight failed; no branches were changed"

  git branch "$name" "$parent" --quiet || die "could not create branch '$name'; gs metadata was not changed"
  if ! rebase_branch_in_executor "$child" "$name" "$fork"; then
    git branch -D "$name" --quiet 2>/dev/null || true
    die "could not rebase '$child' onto '$name'; the new branch was removed and gs metadata was not changed"
  fi
  set_parent "$name" "$parent"
  set_base_oid "$name" "$(git rev-parse "$parent")"
  set_parent "$child" "$name"
  set_base_oid "$child" "$(git rev-parse "$name")"
  info "restacking descendants of '$child'..."
  restack_upstack "$child"
  checkout_navigation_target "$name"
  success "inserted '$name' between '$parent' and '$child'"
}

cmd_untrack() {
  ensure_gs_init
  local branch="${1:-$(current_branch)}" parent child
  local children=() affected=()
  is_tracked "$branch" || die "'$branch' is not tracked by gs"
  parent="$(get_parent "$branch")"
  affected+=("$branch")
  while IFS= read -r child; do
    [[ -n "$child" ]] || continue
    children+=("$child")
    affected+=("$child")
  done <<< "$(get_children "$branch")"
  preflight_owned_branches "${affected[@]}" || die "untrack preflight failed; gs metadata was not changed"

  for child in "${children[@]}"; do
    set_parent "$child" "$parent"
    info "reparented '$child' to '$parent'"
  done
  remove_tracking "$branch"
  success "untracked '$branch' (git branch still exists)"
}

cmd_fold() {
  ensure_gs_init
  local cur parent trunk child fork branch reparent_plan finalizer
  local children=() affected=() parent_old_oid
  cur="$(current_branch)"
  is_tracked "$cur" || die "'$cur' is not tracked by gs"
  parent="$(get_parent "$cur")"
  trunk="$(trunk_branch)"
  [[ "$cur" != "$trunk" ]] || die "cannot fold trunk"

  if [[ "${GS_DRY_RUN:-0}" == "1" ]]; then
    echo -e "${CYAN}[dry-run]${RESET} would squash-merge '${YELLOW}$cur${RESET}' into '$parent'"
    while IFS= read -r child; do [[ -n "$child" ]] && echo "  would reparent '$child' to '$parent'"; done <<< "$(get_children "$cur")"
    echo "  would delete branch '$cur' and restack children"
    return 0
  fi

  affected+=("$cur" "$parent")
  while IFS= read -r child; do
    [[ -n "$child" ]] || continue
    children+=("$child")
    fork="$(get_base_oid "$child" 2>/dev/null || true)"
    if [[ -z "$fork" ]]; then
      git merge-base --is-ancestor "$cur" "$child" 2>/dev/null ||
        die "no recorded base for '$child'; re-track it after verifying '$cur'"
      fork="$(git rev-parse "$cur")"
    fi
    affected+=("$child")
    while IFS= read -r branch; do [[ -n "$branch" ]] && affected+=("$branch"); done <<< "$(collect_descendants_bfs "$child")"
    validate_restack_bases "$child" || die "fold preflight failed; no branches were changed"
  done <<< "$(get_children "$cur")"
  preflight_owned_branches "${affected[@]}" || die "fold preflight failed; no branches were changed"
  parent_old_oid="$(git rev-parse "$parent")"
  reparent_plan="$(mktemp "${TMPDIR:-/tmp}/gs-fold-plan.XXXXXX")"
  collect_reparent_plan "$cur" "$parent" > "$reparent_plan"
  finalizer="type=fold
branch=$cur
parent=$parent
parent_old_oid=$parent_old_oid
local_mutation_done=no
local_restore_done=no
branch_cleanup_done=no
tracking_cleanup_done=no"
  prepare_restack_operation "$parent" 0 "$reparent_plan" "$finalizer"
  rm -f "$reparent_plan"
  run_operation_prerequisites || die "fold did not complete; the operation journal was retained for 'gs restack --continue' or '--abort'"
  execute_restack_steps
  for child in "${children[@]}"; do info "reparented '$child' to '$parent'"; done
  success "folded '$cur' into '$parent'"
}

cmd_split() {
  ensure_gs_init
  local commit="${1:-}" new_name="${2:-}" cur parent old_tip child
  local children=() affected=()
  [[ -n "$commit" && -n "$new_name" ]] || die "usage: gs split <commit> <new-branch-name>"
  git rev-parse --verify "$commit" >/dev/null 2>&1 || die "'$commit' is not a valid commit"
  cur="$(current_branch)"
  is_tracked "$cur" || die "'$cur' is not tracked by gs"
  branch_exists "$new_name" && die "branch '$new_name' already exists"
  parent="$(get_parent "$cur" 2>/dev/null || trunk_branch)"
  local base
  base="$(get_base_oid "$cur" 2>/dev/null || git rev-parse "$parent")"
  git merge-base --is-ancestor "$commit" HEAD 2>/dev/null || die "'$commit' is not an ancestor of HEAD"
  git merge-base --is-ancestor "$base" "$commit" 2>/dev/null || die "'$commit' is below the recorded base of '$cur'"
  [[ "$(git rev-parse "$commit")" != "$(git rev-parse HEAD)" ]] || die "split commit is HEAD — nothing to split"
  [[ "$(git rev-parse "$commit")" != "$(git rev-parse "$parent")" ]] || die "split commit is same as parent '$parent' — nothing to keep"

  affected+=("$cur")
  while IFS= read -r child; do
    [[ -n "$child" ]] || continue
    children+=("$child")
    affected+=("$child")
  done <<< "$(get_children "$cur")"
  preflight_owned_branches "${affected[@]}" || die "split preflight failed; no branches were changed"

  old_tip="$(git rev-parse "$cur")"
  git branch "$new_name" "$old_tip" --quiet || die "could not create '$new_name'; gs metadata was not changed"
  if ! git reset --hard "$commit" --quiet; then
    git branch -D "$new_name" --quiet 2>/dev/null || true
    die "could not reset '$cur'; the new branch was removed and gs metadata was not changed"
  fi
  set_parent "$new_name" "$cur"
  set_base_oid "$new_name" "$(git rev-parse "$cur")"
  for child in "${children[@]}"; do
    set_parent "$child" "$new_name"
    info "reparented '$child' to '$new_name'"
  done
  success "split '$cur' at $(git rev-parse --short "$commit"): new branch '$new_name'"
}

cmd_rename() {
  ensure_gs_init
  local new_name="${1:-}" cur trunk caller parent old_base child
  local children=() affected=()
  [[ -n "$new_name" ]] || die "usage: gs rename <new-name>"
  cur="$(current_branch)"
  trunk="$(trunk_branch)"
  [[ "$cur" != "$trunk" ]] || die "cannot rename trunk branch"
  branch_exists "$new_name" && die "branch '$new_name' already exists"
  affected+=("$cur")
  while IFS= read -r child; do
    [[ -n "$child" ]] || continue
    children+=("$child")
    affected+=("$child")
  done <<< "$(get_children "$cur")"
  caller="$(pwd -P)"
  preflight_owned_branches_allow_dirty_path "$caller" "${affected[@]}" ||
    die "rename preflight failed; no branches were changed"

  git branch -m "$cur" "$new_name" || die "could not rename '$cur'; gs metadata was not changed"
  if is_tracked "$cur"; then
    parent="$(get_parent "$cur")"
    old_base="$(get_base_oid "$cur" 2>/dev/null || true)"
    set_parent "$new_name" "$parent"
    [[ -z "$old_base" ]] || set_base_oid "$new_name" "$old_base"
    remove_tracking "$cur"
  fi
  for child in "${children[@]}"; do
    set_parent "$child" "$new_name"
  done
  success "renamed '$cur' to '$new_name'"
}

cmd_delete() {
  ensure_gs_init
  local branch="${1:-$(current_branch)}" trunk parent children child owner
  trunk="$(trunk_branch)"
  [[ "$branch" == "$trunk" ]] && die "cannot delete trunk branch"
  parent="$(get_parent "$branch" 2>/dev/null || true)"
  [[ -n "$parent" ]] || parent="$trunk"
  children="$(get_children "$branch")"

  if [[ "${GS_DRY_RUN:-0}" == "1" ]]; then
    echo -e "${CYAN}[dry-run]${RESET} would delete branch '${YELLOW}$branch${RESET}'"
    for child in $children; do
      echo "  would reparent '$child' to '$parent'"
    done
    owner="$(branch_owner_path "$branch" 2>/dev/null || true)"
    [[ -n "$owner" ]] && echo "  would keep its owning worktree at '$owner' and only untrack the branch"
    return 0
  fi

  local affected=("$branch")
  for child in $children; do affected+=("$child"); done
  preflight_owned_branches "${affected[@]}" || die "delete preflight failed; no branches were changed"

  owner="$(branch_owner_path "$branch" 2>/dev/null || true)"
  if [[ -z "$owner" ]] && branch_exists "$branch"; then
    delete_unowned_branch "$branch" "$parent" || die "could not delete branch '$branch'; metadata was not changed"
  fi

  for child in $children; do
    set_parent "$child" "$parent"
    info "reparented '$child' to '$parent'"
  done
  is_tracked "$branch" && remove_tracking "$branch"

  if [[ -n "$owner" ]]; then
    info "left checked-out branch '$branch' and its worktree intact at '$owner'"
    success "untracked branch '$branch'"
  else
    success "deleted branch '$branch'"
  fi
}

cmd_land() {
  ensure_gs_init
  local branch="" strategy="--squash"
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --squash) strategy="--squash" ;;
      --merge) strategy="--merge" ;;
      --rebase) strategy="--rebase" ;;
      -*) die "unknown flag: $1" ;;
      *) branch="$1" ;;
    esac
    shift
  done
  [[ -n "$branch" ]] || branch="$(find_bottom "$(current_branch)")"
  [[ -n "$branch" ]] || die "could not determine bottom branch"
  is_tracked "$branch" || die "'$branch' is not tracked by gs"
  command -v gh >/dev/null 2>&1 || die "gh CLI is required for 'gs land'"

  local pr_state review trunk parent children child descendant reparent_plan finalizer
  pr_state="$(gh pr view "$branch" --json state --jq '.state' 2>/dev/null || true)"
  [[ -n "$pr_state" ]] || die "no PR found for '$branch'"
  [[ "$pr_state" == "OPEN" ]] || die "PR for '$branch' is not open (state: ${pr_state})"
  review="$(gh pr view "$branch" --json reviewDecision --jq '.reviewDecision' 2>/dev/null || true)"
  case "$review" in
    APPROVED|"") ;;
    CHANGES_REQUESTED) die "PR for '$branch' has changes requested — cannot land" ;;
    REVIEW_REQUIRED) die "PR for '$branch' still needs review approval" ;;
  esac
  trunk="$(trunk_branch)"
  parent="$(get_parent "$branch" 2>/dev/null || true)"
  [[ -n "$parent" ]] || parent="$trunk"
  children="$(get_children "$branch")"

  if [[ "${GS_DRY_RUN:-0}" == "1" ]]; then
    echo -e "${CYAN}[dry-run]${RESET} would merge PR for '${YELLOW}$branch${RESET}' into '$parent' ($strategy)"
    [[ "$review" == "APPROVED" ]] && echo "  review: ${GREEN}APPROVED${RESET}"
    echo "  would update '$parent', rebase children past merged commits, and clean up '$branch'"
    return 0
  fi

  reparent_plan="$(mktemp "${TMPDIR:-/tmp}/gs-land-plan.XXXXXX")"
  collect_reparent_plan "$branch" "$parent" > "$reparent_plan"
  local affected=("$branch" "$parent")
  while IFS=$'\t' read -r descendant child; do
    [[ -n "$descendant" ]] && affected+=("$descendant")
  done < "$reparent_plan"
  preflight_owned_branches "${affected[@]}" || die "land preflight failed; no branches were changed"
  finalizer="type=land
branch=$branch
parent=$parent
parent_old_oid=
strategy=$strategy
remote_merge_done=no
parent_update_done=no
branch_cleanup_done=no
tracking_cleanup_done=no"
  prepare_restack_operation "$parent" 0 "$reparent_plan" "$finalizer"
  rm -f "$reparent_plan"
  run_operation_prerequisites || die "land is incomplete; the remote merge may already be complete and the operation journal was retained for 'gs restack --continue'"
  execute_restack_steps
  success "landed '$branch' into '$parent'"
}

cmd_sync() {
  ensure_gs_init
  local scope="current"
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --all) scope="all" ;;
      --current) scope="current" ;;
      *) die "unknown argument: $1" ;;
    esac
    shift
  done

  local trunk original sync_root branch child parent merged_tip owner
  trunk="$(trunk_branch)"
  original="$(current_branch)"
  sync_root="$trunk"
  if [[ "$scope" == "current" ]]; then
    [[ "$original" != "$trunk" ]] || die "on trunk — no current stack to sync. Switch to a stacked branch, or pass --all."
    is_tracked "$original" || die "current branch '$original' is not tracked. Switch to a stacked branch, or pass --all."
    sync_root="$(find_bottom "$original")"
    info "syncing current stack rooted at '$sync_root'"
  fi

  local all_branches=()
  if [[ "$sync_root" != "$trunk" ]]; then all_branches+=("$sync_root"); fi
  while IFS= read -r branch; do
    [[ -n "$branch" ]] && all_branches+=("$branch")
  done <<< "$(collect_descendants_bfs "$sync_root")"

  if [[ "${GS_DRY_RUN:-0}" == "1" ]]; then
    echo -e "${CYAN}[dry-run]${RESET} would fetch, update '$trunk', and check for merged PRs..."
    local found=0
    for branch in "${all_branches[@]}"; do
      branch_exists "$branch" || continue
      if branch_is_merged "$branch"; then echo "  ${YELLOW}would clean up${RESET} merged branch '$branch'"; found=1; fi
    done
    [[ $found -eq 0 ]] && echo "  no merged branches found"
    echo "  ${YELLOW}would restack${RESET} remaining branches under '$sync_root'"
    return 0
  fi

  local affected=("$trunk")
  for branch in "${all_branches[@]}"; do affected+=("$branch"); done
  preflight_owned_branches "${affected[@]}" || die "sync preflight failed; no branches were changed"

  info "fetching from origin..."
  git fetch origin --prune --quiet
  info "updating trunk '$trunk'..."
  update_branch_from_origin "$trunk" || die "could not fast-forward '$trunk'. Resolve manually and retry."

  [[ ${#all_branches[@]} -gt 0 ]] || { success "no tracked branches; nothing to sync"; return 0; }
  local merged=()
  info "checking ${#all_branches[@]} tracked branch(es) for merged PRs..."
  for branch in "${all_branches[@]}"; do
    branch_exists "$branch" || continue
    if branch_is_merged "$branch"; then info "  '$branch' is merged"; merged+=("$branch"); fi
  done

  local cleanup_failed=0 children
  for branch in "${merged[@]}"; do
    parent="$(resolved_parent_after_merges "$branch" "$trunk" "${merged[@]}")"
    merged_tip="$(git rev-parse "$branch" 2>/dev/null || true)"
    children="$(get_children "$branch")"
    for child in $children; do
      is_in_list "$child" "${merged[@]}" && continue
      branch_exists "$child" || continue
      if [[ -n "$merged_tip" ]] && rebase_branch_in_executor "$child" "$parent" "$merged_tip"; then
        set_parent "$child" "$parent"
        set_base_oid "$child" "$(git rev-parse "$parent")"
        info "reparented '$child' onto '$parent'"
      else
        cleanup_failed=1
      fi
    done
    [[ $cleanup_failed -eq 0 ]] || continue
    owner="$(branch_owner_path "$branch" 2>/dev/null || true)"
    if [[ -n "$owner" ]]; then
      remove_tracking "$branch"
      info "left merged branch '$branch' checked out at '$owner'; removed gs tracking only"
    elif branch_exists "$branch"; then
      if delete_unowned_branch "$branch" "$parent"; then
        remove_tracking "$branch"
        success "deleted merged branch '$branch'"
      else
        warn "could not delete merged branch '$branch'; it remains tracked"
        cleanup_failed=1
      fi
    else
      remove_tracking "$branch"
    fi
  done
  [[ $cleanup_failed -eq 0 ]] || die "sync cleanup is incomplete; resolve the reported worktree and retry"

  info "restacking remaining branches under '$sync_root'..."
  if [[ "$sync_root" == "$trunk" ]] || ! is_in_list "$sync_root" "${merged[@]}"; then
    restack_upstack "$sync_root"
  else
    for branch in "${all_branches[@]}"; do
      branch_exists "$branch" || continue
      is_tracked "$branch" || continue
      parent="$(get_parent "$branch" 2>/dev/null || true)"
      is_in_list "$parent" "${all_branches[@]}" || restack_upstack "$branch"
    done
  fi
  cleanup_restack_tips

  if ! branch_exists "$original"; then
    info "original branch '$original' was deleted; its worktree remains on its current checkout"
  fi
  success "sync complete"
}
