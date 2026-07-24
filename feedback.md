# gs feedback — observations from a 14-PR stack migration

Context: I used gs (git-stack) extensively to manage the v1→v2 nanoclaw migration as a 14-PR stack with multiple mid-flight reorganizations (folding PR 9 into PR 5, splitting OSV into its own PR + reordering thread-collision/auto-deploy/sandbox, then sandwiching a new sandbox-deny PR into the middle). The tool was load-bearing — pleasant to use overall, but I hit some thorns. This is candid; pick what's worth fixing.

A second round of stack work after the original feedback was written (test-tightening across 4 branches, docs-split bug fix touching 3 branches with cherry-picks-and-rebase, plus several other content cleanups) confirmed most of the original observations and added one new one — section #11 at the bottom.

## Real bugs

### 1. `cmd_rename` is implemented but not in the dispatch table

Confirmed in `gs` lines 1461–1491. The function exists, but the case statement in `main()` (around line 1551) doesn't include `rename) cmd_rename "$@" ;;`. Calling `gs rename foo` exits with `unknown command: rename. Run 'gs help' for usage.` The help output also doesn't list `rename` in the Commands block.

Fix is two lines:
```bash
# In main()'s case statement
rename)   cmd_rename "$@" ;;
# In cmd_help() Commands block
  rename <new-name>       Rename current branch and update gs metadata
```

I worked around it manually by `git branch -m` then renaming the metadata file at `.git/worktrees/<wt>/gs/branches/<encoded-name>` — discoverable but only because I read your source.

### 2. Worktree-pinned ref errors when scripting branch updates

When iterating branches in a loop and running `git rebase --onto X Y` followed by `git branch -f $branch HEAD`, I hit `fatal: cannot force update the branch '<name>' used by worktree at <path>` for whichever branch I was checked out on. Standard git behavior, but it's surprising in scripts because the rebase itself updates the branch ref in-place when the branch is checked out. The `branch -f` was redundant but I didn't know that until I traced through.

Not a gs bug per se but worth a note in the README about how to script around it.

## Documentation gaps

### 3. The `gs commit` vs `git commit` contract isn't loud enough

The README says `gs commit auto-restacks for you. Use gs restack when you've used raw git commands.` What's not obvious until it bites you: `gs commit` saves an `old_tips/<branch>` file at HEAD^ before committing, and `restack_upstack` uses that as the fork point for descendants. If you `git commit` directly, no old-tip is saved, and `restack_upstack` falls back to merge-base — which may go further back than the real fork and cause "duplicate commits or unexpected conflicts" (your warning's wording, accurate).

I used `git commit` throughout (because I had a pre-commit hook that needed PATH manipulation that I forgot to apply via `gs commit` — minor friction). Result: every subsequent `gs restack` warned per-branch:

```
warning: no saved old-tip for 'migrate/X' (gs commit wasn't used). Falling back to merge-base.
```

Cumulative noise across a 14-branch stack. The warning is technically correct but defensive — if the actual restack would be a no-op (descendants have no new commits to replay), the warning is just noise.

Suggestions:
- Loud README warning: "If you don't use `gs commit`, you'll need to think about merge-base fallback. Multi-commit branches should be especially careful."
- Suppress the warning when restack_upstack determines there's nothing to do for that branch.
- Or: detect when the user uses `git commit` on a tracked branch and write the old-tip retroactively from `HEAD^`.

### 4. `gs push --all` is undocumented in the README/help

I was using `gs top && gs push` to push the entire stack — which works because `gs push` pushes downstack from current. But `gs push --all` exists (saw it in `cmd_push`) and uses BFS from trunk, which is more semantically correct. The `gs push` help line doesn't mention `--all`. The README only says "Push from current branch downward through stack to remote".

Fix: one-line README/help mention of `gs push --all`.

## UX friction (not bugs, just sharp edges)

### 5. Inserting a new branch between two existing branches is multi-step

To insert a new branch B between existing parent A and existing child C, you do:

```
gs co A
gs create B
# implement and commit on B
gs co C
gs move --onto B
```

This is fine, but I caught myself wishing for `gs insert B --between A C` for the common "I forgot to make X its own PR" case. Probably not worth implementing, but flagging the want.

### 6. Stack reorganization can leave duplicate commits behind

When I did the PR 9→PR 5 fold + PR 8 OSV split + auto-deploy reorder, several intermediate restacks left "stale" copies of earlier commits in descendant branches. Example: after dropping the global.md commit from PR 5 via `git rebase --onto`, I had to walk up the stack and drop the commit (which had been propagated to multiple descendants with different SHAs each time) from each branch individually. `gs restack --all` didn't always detect the duplicates because their SHAs differed (cherry-picked across rebases).

The "patch contents already upstream" detection that `gs restack` has IS doing the right thing when it kicks in — but it only fired some of the time. Felt nondeterministic.

This is partly because I didn't use `gs commit` (see #3) so old-tips weren't saved, and partly because cherry-pick history made each propagation a fresh SHA. I'm not sure there's a clean fix, but maybe a `gs cleanup` or `gs deduplicate` command that walks the stack and offers to drop commits whose contents already exist on a parent.

### 7. No `gs status` for "is my stack consistent?"

After a series of rebases, force-pushes, and conflict resolutions, I wanted a single command that would tell me: "your local stack matches your gs metadata, here's any drift between local and origin." `gs ls` is great for tree shape, but doesn't tell me about working-tree dirtiness vs metadata vs origin status in one glance.

A `gs status` showing per-branch:
- working tree clean?
- ahead/behind origin?
- ahead/behind tracked parent?
- any duplicate-content commits with parent?

…would have saved me debugging time.

### 8. `gs restack` after a conflict mid-rebase can be hard to recover from

Twice during this work, a `gs restack --all` hit a conflict, I fixed it manually, ran `gs restack --continue`, and got "fatal: no rebase in progress / Still have conflicts." Investigation showed the rebase had finished but gs still thought it was in progress. Workaround was running plain `gs restack --all` again. The state file at `.git/gs/restack_state` may have stale entries.

I didn't have time to repro reliably, but flagging in case it's known.

### 9. The pre-commit hook ran into PATH issues during `gs commit`

The repo's husky pre-commit hook runs `pnpm run format:fix`. pnpm is loaded via NVM as a shell function, so it's not in PATH for non-interactive shells. `gs commit` invokes git which runs the hook — and the hook fails on the first invocation, leaving format drift on files. Not gs's problem (it's a misconfigured pre-commit hook in the consumer repo) but the cumulative effect was that I had unstaged format drift propagating across restacks, which sometimes blocked them with "cannot rebase: you have unstaged changes."

A README note about "if your pre-commit hook leaves dirty files, expect restack pain" could help.

### 10. Format-drift on the same file across restacks accumulates noise

Related to #9. When `src/host-sweep.test.ts` got prettier-reformatted at every restack pass, the drift on disk never made it into a commit (was always discarded with `git checkout -- src/host-sweep.test.ts` before the next restack). But the drift kept reappearing because the file's content didn't match what prettier wanted, and the format hook re-reformatted on every pre-commit run.

I ended up running `git checkout --` on that file before nearly every `gs restack --all`. Sometimes I forgot and the restack hit a "cannot rebase: you have unstaged changes" error.

A `gs restack --autostash` flag (analogous to `git rebase --autostash`) would have eliminated this noise — autostash before the rebase chain starts, restore after. Bonus: works even if the dirty state IS something the user wants to keep.

### 11. (NEW — second round) Content-shape changes during stack reorganization propagate as duplicates

Hit this during a docs-split refactor that touched 4 stacked PRs. Original state: each of PR 11, 13, 14, 15 had a commit appending a section to `docs/operations.md`. Goal: split each section into its own per-feature file under `docs/operations/`.

The sub-agent doing the split:
1. On PR 11, deleted `docs/operations.md` and created `docs/operations/thread-collisions.md` with that PR's content. ✓
2. On PR 13, created `docs/operations/auto-compact.md` with that PR's content. ✓
3. But PR 13's ORIGINAL commit (the one that appends to `docs/operations.md`) still tried to apply during restack — and since `docs/operations.md` no longer existed but `docs/operations/thread-collisions.md` did, the appended content landed in **`thread-collisions.md`** instead of failing or being a no-op. Same cascaded into PR 14, PR 15.

End state: each of PR 13/14/15 had its content duplicated in TWO places (the new per-feature file AND `thread-collisions.md`). Took a second pass with `git checkout migrate/thread-collision-instrumentation:docs/operations/thread-collisions.md` per branch to restore the canonical file across all 5 branches.

This isn't strictly a gs bug — git's rebase is doing the locally-correct thing (replay the patch, which adds lines to whatever file matches). But the consumer-level symptom is "stack reorganization that changes a file's shape leaves silent content duplication in unrelated files." Possible angles:

- **Warn on suspicious patch application during restack**: if a patch's diff context is "0 lines of context match," that's evidence the file was reshaped and the patch is applying in a wildly different location than intended.
- **`gs restack --strict`**: a mode that fails the restack if any commit's patch needed >N lines of fuzzy context to apply, forcing the user to inspect.
- **README note in the section on stack reorganizations**: "If you reshape a file in an early PR (rename, split, move sections), later PRs that touched that file may silently apply their patches in unexpected places. Verify content after restack."

The third is cheapest and probably enough — sophisticated detection would be expensive for the value.

## What gs got right

- `gs ls` tree visualization is cleanly readable and a clear improvement over `git log --graph`.
- `gs delete` reparenting children is exactly what I want when extracting a branch.
- `gs move --onto` is the right primitive for the common "I created this on the wrong base" case.
- "patch contents already upstream" auto-skip during restack saved me from manual `--skip` invocations several times.
- The metadata format (one file per branch, contents = parent name, URL-encoded for slashes) is simple, debuggable, and editable by hand when needed.
- Force-with-lease on `gs push` is the right default — saved me from at least one accidental clobber.
- `gs init --trunk <branch>` accepting a non-`main` trunk let me use this on a worktree where the `migrate/v2-base` branch was the effective trunk.

### Second-round additions

- **`gs delete <branch>` and `gs move --onto <branch>` worked clean** during stack reorganizations. The fold-PR-9-into-PR-5 operation involved cherry-picking + `gs delete` for the redundant branch + restack — descendants reparented correctly with no manual fixup.
- **The `gs restack --all` cherry-pick-aware skip** ("patch contents already upstream — dropping") fired multiple times during the test-tightening pass when commits were already applied via the chain. Saved several manual `--skip` invocations.
- **Force-with-lease on `gs push`** caught one scenario where I was about to push stale state after a partial rebase. Safety net worked as designed.

## Suggested priority

If you're doing a small fix pass:
1. **#1 (rename dispatch) — actual bug, two-line fix.**
2. #4 (document `gs push --all`).
3. #3 (gs commit contract README clarity).
4. #10 (`gs restack --autostash` flag).

If you're doing a bigger UX pass:
5. #7 (gs status).
6. #6 (stack cleanup/dedupe).
7. #8 (restack-state recovery).
8. #11 (warn on file-shape-change duplication during restack).

Net: I'd use gs again for the next stacked migration. Second round of work (test-tightening across 4 branches, docs-split bug fix, this very PR-description batch) confirmed the original thorns and added one (#11). Everything navigable. Cumulative time lost to gs friction over the whole project: maybe 90 minutes — most of that on #1 and #3.


# AMBITIOUS
Make GS work across the whole computer so it can work across worktrees. Not sure if this is even possible
