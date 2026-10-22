# local-pi

## Function

Small agent-facing CLI wrapper around the local Pi worker. It keeps the command surface narrow,
serializes GPU-bound work to one active task, and reports corrective `error:`/`fix:` diagnostics.

## Installation

The standalone source lives at `/home/klaas/src/local-agent-harness` and is installed in the
isolated environment `/home/klaas/.local/share/local-agent-harness/.venv`. The user command is
`/home/klaas/.local/bin/local-pi`.

## Commands

```text
local-pi doctor
local-pi status
local-pi run "one focused task"
local-pi run --cwd /path/to/worktree "one focused task"
```

`run` accepts one task, an optional workspace, and an optional timeout. It does not pass arbitrary
arguments through to Pi. It invokes the declared local vLLM model through Pi and uses a user-state
lock so a second task receives a repairable busy error.

## Boundaries

Use a dedicated worktree or throwaway directory for write tasks. The CLI reports Pi failures and
does not decide Beads status or commits; the calling agent owns review and acceptance.
