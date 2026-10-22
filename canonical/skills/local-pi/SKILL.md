---
name: local-pi
description: Delegate one bounded coding or investigation task to the local Pi worker.
---

# Local Pi worker

Use the local worker for bounded repository reading, focused implementation, test repair, and
small review tasks. Keep the task specific and include its acceptance criteria.

Before a first task in a session, check the worker:

```bash
local-pi doctor
local-pi status
```

Run one task at a time, preferably in a dedicated worktree or throwaway directory:

```bash
local-pi run --cwd /path/to/worktree "Inspect the failing test, make the smallest fix, run the tests, and report the diff."
```

The worker is single-slot. If it reports that another task is running, wait and retry. If it
returns an `error:` followed by `fix:`, follow the correction rather than inventing flags or
passing arguments through to Pi.

After a write task, inspect the diff and test results yourself. The worker reports execution
failure, but the calling agent owns review, Beads status, and any commit decision.
