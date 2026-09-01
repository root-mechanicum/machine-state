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
| `~/.config/dcg/config.toml` | **us, by authorship — but hand-applied, never projected** |
| the rest of `~/.config/dcg/**` | dcg |

`~/.claude/settings.json` is additionally hand-written and holds this hook — the FOREIGN case in
`SUBSTRATE.md` §6, and the first thing the projector's refusal path must protect. We record intent
and verify; we do not project into it.

A project-level `.dcg.toml` would be ours, and dcg treats it as **enforcement-only** — it can
tighten but never loosen. A projected file that can only increase restriction cannot become an
attack on the safety boundary, which is what would make it safe to manage from `canonical/`. None
exists yet; see `machine-state-3r1`.

## Intent

**Wiring.** Every supported harness installed on this machine is dcg-wired. Wiring is a separate
manual step per harness, so this is the intent most at risk of silently lapsing. It is now checked
rather than merely stated: a harness record may declare a `wiring` command, and a harness that is
installed but unwired makes `ms status` exit non-zero. Absent harnesses are skipped — what is not
installed cannot be unguarded. The check exists for Claude; see `canonical/tooling/codex.md` for
why it does not yet exist for Codex.

**Never disabled to get a command through.** A refusal is answered by narrowing the command, or by
an explicit allowlist entry with a recorded reason. Not by turning a pack off.

**Observability before tuning.** Both the log file and the history database are opt-in and were
off, so `dcg history analyze` was reading an empty database — and recommending that `core` be
disabled for inactivity on the same day `core` blocked two real commands. Advice from that command
is worthless until logging has run.

**Posture.** Fail-closed, and packs enabled by installed surface:

| Setting | Value | Why |
| --- | --- | --- |
| `fail_closed` | `true` | a fail-open bypass is silent; a fail-closed error is loud and recoverable |
| `log_file`, `history.enabled` | on | every other decision here is empirical |
| added packs | `package_managers`, `system.services`, `system.permissions`, `secret_disclosure` | pacman, systemd `--user` units, `$HOME`, and private keys are all real here |
| not enabled | cloud, kubernetes, containers, database, infrastructure, windows, cicd | none of that software is installed; rules for absent software protect nothing and only misfire |
| new packs' mode | `warn` | staged: proven packs keep denying while the log shows what the new ones actually match |

`core` (filesystem + git) is always on and cannot be disabled; `system.disk` is on by default.
Both keep denying.

The four new packs are set to `warn` in `[policy.packs]` deliberately. Removing those four lines,
once the log justifies it, is the last step of this decision — not a separate one.

**Layer.** The posture lives in `~/.config/dcg/config.toml`, the only layer that applies to every
directory rather than one repository. It is authored by hand and **deliberately not projected**:
that layer has full control and can *loosen* as well as tighten, so a bad edit in `canonical/`
would let `ms project` silently weaken the boundary. The substrate does not get authority over the
guard that sits beneath it. A project-level `.dcg.toml` is different — dcg treats it as
enforcement-only, able to tighten but never loosen — and would therefore be safe to manage from
`canonical/` if per-repo tightening is ever wanted.

## Verification

`dcg doctor` checks binary, hook registration, wiring, build provenance, config, packs, and runs a
smoke test. All checks must pass, and hook wiring must report exactly one dcg hook registered.

**A green line here is a weaker claim than it looks.** `dcg doctor` verifies *installation*, not
*posture*. With no config file it reports `USING DEFAULTS` as a pass; with one it reports
`OK (1 file source)` — which confirms a config loaded, not that it says the right things. Nothing
checks that `fail_closed` is true or that the intended packs are enabled; the table above is the
record of what *should* be true, and `dcg config` is how you confirm it by hand.

`--strict` is not optional here. Plain `dcg doctor` exits 0 **even when its checks fail**, so a
record using it would report this guard as healthy no matter what went wrong.

```toml
group      = "Safety"
version    = "dcg --version"
check      = "dcg doctor --strict"
ok         = "active"
fail       = "degraded"
missing    = "not installed"
```
