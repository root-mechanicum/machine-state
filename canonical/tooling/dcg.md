# dcg — Destructive Command Guard

## Function

A pre-execution shell hook that intercepts potentially destructive commands before an agent can
run them. Supports Claude Code, Codex CLI, Gemini CLI, Copilot CLI, Cursor, Hermes, OpenCode and
omp, and speaks each one's hook protocol.

## Role

The **safety boundary beneath the agent harnesses**. It sits below the harness rather than inside
it, and applies regardless of which supported agent is operating. That is what lets agents be
interchangeable here without renegotiating safety each time one is swapped in.

It is not a substitute for judgement, and it is not this repository's authority: `bin/ms` has its
own refusal rules, and dcg guards the shell beneath both.

## Ownership

VENDOR. Not ours to configure without a recorded decision:

| Path | Owner |
| --- | --- |
| the `dcg` binary | its installer / `dcg update` |
| the hook entry in `~/.claude/settings.json` | `dcg install` |
| `~/.config/dcg/**` | dcg |

`~/.claude/settings.json` is additionally hand-written and holds this hook — the FOREIGN case in
`SUBSTRATE.md` §6, and the first thing the projector's refusal path must protect. We record intent
and verify; we do not project into it.

A project-level `.dcg.toml` would be ours, and dcg treats it as **enforcement-only** — it can
tighten but never loosen. A projected file that can only increase restriction cannot become an
attack on the safety boundary, which is what would make it safe to manage from `canonical/`. None
exists yet; see `machine-state-3r1`.

## Intent

- Every supported harness installed on this machine is dcg-wired. Wiring is currently a separate
  manual `dcg install` step, so this is the intent most at risk of silently lapsing.
- The guard is never disabled to get a command through. A refusal is answered by narrowing the
  command or by an explicit, reasoned allowlist entry.
- The posture itself — fail-open versus fail-closed, and which of the 103 packs are enabled — is
  **undecided**. It is currently inherited defaults, not a choice. Tracked in `machine-state-3r1`.

## Verification

`dcg doctor` checks binary, hook registration, wiring, build provenance, config, packs, and runs a
smoke test. All checks must pass, and hook wiring must report exactly one dcg hook registered.

`dcg doctor` passing means *correctly installed*, **not** *configured as intended* — it reports
`USING DEFAULTS` as a pass. Until `machine-state-3r1` is answered, a green line here is a weaker
claim than it looks.

```toml
group      = "Safety"
version    = "dcg --version"
check      = "dcg doctor"
ok         = "active"
fail       = "degraded"
missing    = "not installed"
```
