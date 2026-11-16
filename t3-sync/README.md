# Sync T3 Personal

The canonical command is `t3-sync/sync-personal`. The local `t3-draft/t3d` shell setup also exposes it as `t3d-sync`; preview/pairing commands are unchanged.

## Sync Personal

```sh
t3d-sync --dry-run   # Show the committed Draft revision and incoming commits.
t3d-sync             # Queue merge, backup, rebuild and relaunch in Terminal.
```

The command pins `personal-draft` to its current commit and uses **`git merge --ff-only`** in Personal's `main` checkout. Draft's uncommitted files are ignored. No per-file source copying, stashing, reset, rebase or force push.

`main` must have no tracked/index changes. If branches diverge, merge `main` into Draft and test/commit there before syncing. Keep implementation work in Draft; `main` is the release checkout.

The Terminal-owned run waits up to one hour for T3 to report no active threads across all projects, including child agents. It calls `t3_project_list` and `t3_thread_list` over MCP; it never queries database tables for activity. After four idle checks it merges the pinned commit, stops the verified Personal app, backs up its database and current build, rebuilds and relaunches using the existing Personal profile. Build failure restores the previous binaries and relaunches them. The Git branch stays advanced; profiles are never copied or restored over.

## Running it from an agent

Run the command from a Personal agent with `T3_MCP_URL` and `T3_MCP_BEARER_TOKEN` available. The command hands those credentials to Terminal through a private temporary file, removed after the idle check. Missing access or failed API calls never count as idle.

Fire the command and end the turn. A Personal-hosted agent's own active turn blocks the sync. Report that it is queued, and check the result from a later message. The wait logs blocking thread names and statuses on change and every 30 seconds. Status polling does not prevent a new turn from starting just before shutdown; an atomic drain would require server support.

Progress and backups are under `opencodex/local/t3code-personal/backups/git-sync-<UTC timestamp>/`. The sync uses a temporary Terminal for the build. Once Personal has launched, closing that tab does not stop it: the GUI app has its own process session.

Keep Personal’s `main` clean and do implementation work in Draft. The command deliberately refuses to guess which local edits are disposable.

## Launch without a Terminal window

```sh
node t3-sync/launch-app.mjs personal
node t3-sync/launch-app.mjs draft
```

Both start detached GUI processes with explicit, separate profile settings, file-backed output and no controlling terminal. The short launcher exits while the app stays running. Logs go to the copy’s local `logs/personal.log` or `logs/draft.log`, not a visible Terminal window. The existing local `launch-personal.mjs` and `launch-draft.mjs` paths forward here.

For Draft feedback, run `t3d-start` in an existing chat terminal. It opens Draft and follows its log there. Closing the terminal stops the log viewer, not Draft. Chat terminal sessions themselves are stopped when their hosting T3 backend shuts down; this is why they should not own another GUI app.

Instances started by the old foreground launchers remain Terminal-owned until they are quit and relaunched once.
