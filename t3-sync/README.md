# Sync T3 Personal

The canonical command is `t3-sync/sync-personal`. The local `t3-draft/t3d` shell setup also exposes it as `t3d-sync`; preview/pairing commands are unchanged.

## Sync Personal

```sh
t3d-sync --dry-run   # Show the committed Draft revision and incoming commits.
t3d-sync             # Queue merge, backup, rebuild and relaunch in Terminal.
```

The command pins `personal-draft` to its current commit and uses **`git merge --ff-only`** in Personal's `main` checkout. Draft's uncommitted files are ignored. No per-file source copying, stashing, reset, rebase or force push.

`main` must have no tracked/index changes. If branches diverge, merge `main` into Draft and test/commit there before syncing. Keep implementation work in Draft; `main` is the release checkout.

The Terminal-owned run waits up to 20 minutes for active Personal turns to finish, backs up its database through a read-only SQLite connection, merges the pinned commit, stops the verified Personal app, saves its current build, rebuilds and relaunches using the existing Personal profile. Build failure restores the previous binaries and relaunches them. The Git branch stays advanced; profiles are never copied or restored over.

Progress and backups are under `opencodex/local/t3code-personal/backups/git-sync-<UTC timestamp>/`. Keep that Terminal tab open while the foreground launcher is running.

The old manual syncs left `main` with uncommitted copied source. That needs a one-time cleanup before this Git-only command can run. It deliberately refuses to guess which local edits are disposable.
