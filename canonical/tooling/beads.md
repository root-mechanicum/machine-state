# beads (bd)

## Function

Durable issue tracking and shared work memory. Issues live in a local Dolt database under
`.beads/`; cross-machine sync rides `refs/dolt/data` on the git remote. `.beads/issues.jsonl` is a
passive export, not the wire protocol.

## Role

The **coordination layer** of this substrate: the one task system every resident agent shares, so
work survives a session ending, a compaction, or a switch from one agent to another.

## Ownership

VENDOR. `bd setup` recipes own everything below, and regenerate it:

| Path | Recipe |
| --- | --- |
| `CLAUDE.md` marker block | `claude` |
| `AGENTS.md` marker blocks (two) | `codex` |
| `.claude/settings.json` | `claude` |
| `.codex/config.toml`, `.codex/hooks.json` | `codex` |
| `.agents/skills/beads/**` | `codex` |
| `.beads/**` | `bd init` |
| `.gitignore` | `bd init` — no marker pair; append only, never rewrite |

We own our own `MACHINE-STATE POLICY` region in the two instruction files, and nothing else. Their
contents are not our policy and are never copied into `canonical/`.

## Intent

- bd stays the sole task system; no parallel TODO files.
- Its blocks stay bd's to regenerate. We co-exist by marker, never by rewriting its region.
- No automatic Dolt remote sync; pushing is an explicit human action.

## Verification

This record verifies that the **tracker itself** is operational — the database opens and answers.
Whether a given harness is wired to it is that harness's own record, so one fact is not reported
twice under two names.

```toml
group      = "Coordination"
version    = "bd version"
version_re = "([0-9][0-9.]*)"
check      = "bd stats"
ok         = "operational"
fail       = "database unreachable"
missing    = "not installed"
```

Per-harness integration is checked with `bd setup <recipe> --check`, which reports installed,
stale, or absent. Two traps when using it: **the global `-C` flag is ignored** and it inspects the
real working directory instead, and it **exits non-zero when an integration is merely stale**, so
a failing check is not proof of absence. `bd doctor` is unavailable here — this workspace runs
Dolt in embedded mode, which `doctor` does not yet support.
