# codex-local-context

Load a Git repository's root-level `AGENTS.local.md` into Codex session context.

The hook runs on `startup`, `clear`, and `compact`. It skips `resume` because the
existing context already contains the local instructions. It prints nothing when
the file is absent or the working directory is not inside a Git repository.

## Install

Copy the `SessionStart` entry from `hooks.json` into the project's
`.codex/hooks.json`. Replace the example command with the absolute path to the
`codex-local-context` script.

Open `/hooks` in Codex and trust the hook after installation.

## Test

```sh
./test.sh
```
