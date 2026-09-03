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
installed cannot be unguarded.

**This intent is currently unmet, but reachable.** Claude is wired. Codex, installed 2026-09-01,
is not: `ms status` reports it `** UNGUARDED **` and exits non-zero.

Capability is not the problem — dcg is *proven* to work with Codex, firing as a `PreToolUse` hook
with the command reaching the journal tagged `codex-cli`. Two narrower things stand in the way:
Codex will not run a hook whose SHA-256 it has not recorded as trusted, and `bd setup codex` owns
both files a hook could go in. Neither is a dead end; both are recorded in
`canonical/tooling/codex.md`.

Note the narrower true claim while it stands. Codex is not unguarded in the absolute — it ships
its own `codex sandbox`. It is not guarded by *this* boundary, which is a lesser thing than the
Role section above otherwise implies.

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
| added packs | `system.permissions`, `system.services` | proven by probe: recursive permission changes against `$HOME`, and service disabling |
| added, narrower than its name | `package_managers` | covers a `pip` install from an untrusted index. **It does not cover pacman**; see below |
| added, dormant by design | `secret_disclosure` | 11 rules, all for secret-manager CLIs — infisical, `op`, doppler, vault, `aws secretsmanager`/`ssm`. **None of those five is installed**, so it has no surface here. Kept at `warn`; it is correct if one is ever installed |
| added, ours | `machinestate.secrets` | the gap `secret_disclosure` was mistakenly enabled to cover: key and credential *file* reads, and `printenv` of a credential-shaped variable |
| not enabled | cloud, kubernetes, containers, database, infrastructure, windows, cicd | none of that software is installed; rules for absent software protect nothing and only misfire |
| new packs' mode | three now deny, one still `warn` | the staged rollout was reviewed 2026-09-03; see below |

`core` (filesystem + git) is always on and cannot be disabled; `system.disk` is on by default.
Both keep denying.

**The staged rollout was reviewed on 2026-09-03, and did not end the way it was planned to.**

After 452 commands the log showed 7 denies and **zero warns** — the four staged packs had never
fired. Zero warns is ambiguous evidence (quiet coverage, or no coverage?), so the decision was made
on 30 `dcg test` probes rather than on elapsed time. Three packs were promoted by removing their
lines; one was not.

| pack | probe | promoted |
| --- | --- | --- |
| `system.permissions` | blocks recursive world-writable and root-ownership changes against `$HOME`; passes `chmod +x` and `chmod 644` | yes |
| `system.services` | blocks `systemctl disable --now sshd`; passes `systemctl --user status` and `journalctl` | yes |
| `package_managers` | blocks `pip install --index-url http://…`; **allows** every `pacman` and `paru` form probed, including unattended removal and full upgrade | yes, for what it does cover |
| `secret_disclosure` | 18 probes, all ALLOWED | **no** |

**Two of these packs were enabled for reasons that turned out to be false**, and the config said so
in its own comments until this review. `package_managers` was enabled because "pacman is the real
package manager here" — it does not match pacman at all. `secret_disclosure` was enabled because
"reading private keys and tokens is unguarded today", which it does not address at all.

**Resolved 2026-09-03 (`machine-state-00j`), and the pack turned out not to be broken.**
`dcg pack info secret_disclosure` shows 11 rules, every one targeting a secret-manager CLI:
infisical, `op`, doppler, vault, and the AWS secrets and parameter-store subcommands. **None of
those five tools is installed here**, so the pack has no surface. It was enabled against the very
principle two rows above — that rules for absent software protect nothing — and the 18 probes
passed because it was never going to match them. Correctly built, wrongly chosen.

The real gap was closed by a custom pack instead; see `machinestate.secrets` below.

**Testing a guard from inside a guarded shell needs care.** `dcg test "<dangerous literal>"` is
itself blocked, because the hook scans the whole shell block — which is how `system.disk` was
confirmed to deny, and how `system.permissions` was confirmed after promotion when a *documentation
edit quoting the rule* was refused. Probe strings are assembled from fragments and fed through
`dcg test --stdin`.

**`dcg history analyze` remains unreliable in both directions.** On 2026-09-03 it recommended
disabling `system.services`, `system.disk` and `package_managers` for inactivity — including
`system.disk`, which had blocked a command minutes earlier — and reported `python3` heredocs as
"SQL DROP statement" coverage gaps. Logging being on is necessary for its advice to be worth
anything; it is not sufficient.

**One custom pack, `machinestate.secrets`.** `~/.config/dcg/packs/local-secrets.yaml`, loaded via
`custom_paths`. It closes the gap the built-in `secret_disclosure` does not cover: reading a private
key or a credential file, and `printenv` of a credential-shaped variable. Four rules, 26/26 on a
probe suite of 12 dangerous and 14 legitimate commands, zero false positives, and proven by a
negative control — pointing `custom_paths` at an empty directory leaves all four unguarded.

**Its one known limit, stated because a rule that quietly does nothing is the failure this record
exists to prevent.** `echo` and `printf` are matched by *nothing* in dcg 0.13.9. Established across
every form tried: `/usr/bin/echo` with an absolute path, a literal word instead of a variable, and
`echo` piped onward. Variable references are not the obstacle — a reader with `$HOME` in the path
blocks correctly. So `echo $GITHUB_TOKEN` cannot be guarded, and the rule lists `printenv` only
rather than naming `echo` and failing silently.

Three things about custom packs that cost time to learn and are documented nowhere local:

- **A pack with no `keywords` matches nothing at all.** `dcg pack validate` reports the absence as a
  performance *suggestion*; it is in fact load-bearing. Keywords are a quick-reject filter, so they
  must be the executables the rules act on, which are always present and always lower case — not the
  secret-shaped words, which are neither.
- **The `enabled` list does not gate a custom pack.** Removing `machinestate.secrets` from it changes
  nothing; the pack is active because `custom_paths` loads it. The load path is the only control,
  which is why the negative control above targets that.
- **`dcg packs --enabled` and `dcg pack info` disagree** about a custom pack: the first lists it, the
  second reports it not found. Trust `dcg test`.

**Layer.** The posture lives in `~/.config/dcg/config.toml`, the only layer that applies to every
directory rather than one repository. It is authored by hand and **deliberately not projected**:
that layer has full control and can *loosen* as well as tighten, so a bad edit in `canonical/`
would let `ms project` silently weaken the boundary.

**Be precise about what that buys, because it is less than it sounds.** Not projecting this file
keeps `ms` out of it. It does **not** keep an agent out of it: the file is owned by this user and
mode 644, and a write setting `fail_closed = false` tests as `ALLOWED` — dcg does not guard its own
configuration. So this is a convention that prevents *systematic* weakening through projection, not
a boundary that prevents deliberate weakening. The only real boundary on this machine is root
ownership; see `CAPABILITIES.md` §6. A project-level `.dcg.toml` is different — dcg treats it as
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
