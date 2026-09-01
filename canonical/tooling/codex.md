# Codex CLI

## Function

An interactive agent harness from OpenAI, reading `AGENTS.md` for repository instructions and
supporting native hooks from 0.129.0.

## Role

A **resident agent**, and the second tenant that makes "interchangeable" a claim this substrate
can actually test. Every canonical policy fragment that reaches Claude reaches Codex through the
same mechanism and the same marker.

## Ownership

VENDOR. Currently limited to what `bd setup codex` writes: the `AGENTS.md` marker blocks,
`.codex/config.toml`, `.codex/hooks.json`, and `.agents/skills/beads/**`.

Ours by narrow region only: the `MACHINE-STATE POLICY` region of `./AGENTS.md`.

**Not installed on this machine.** `~/.codex/` does not exist, which is why the adapter has a
single in-repo target and no home layout. We do not invent paths for absent software; the manifest
grows when the software arrives.

## Intent

- When Codex is installed, two things must follow before it is trusted here: the safety guard is
  wired for it, and its adapter grows whatever home-directory targets are then real.
- **Codex is installed and NOT dcg-guarded.** The `wiring` check below fails deliberately, so
  `ms status` reports it rather than staying quiet about a live gap.

  The obstacle is structural, not an installer gap as first recorded. Codex *does* support
  pre-execution hooks — its binary carries `PreToolUse` with `permissionDecision` /
  `permissionDecisionReason`, the same protocol shape Claude Code uses, and dcg emits
  Codex-format JSON. But Codex reads hooks from exactly two files, project `.codex/hooks.json`
  and user `~/.codex/hooks.json`, and `bd setup codex` owns **both**. JSON carries no comment
  syntax, so `splice` cannot co-own either one, and no `hooks.d` drop-in exists. There is
  therefore no seam.

  Three ways out, none taken yet: dcg gains a `--codex` installer that merges rather than
  replaces; bd's recipe grows room for a foreign `PreToolUse` entry; or we accept that Codex is
  guarded by its own `codex sandbox` instead and amend the intent in
  `canonical/tooling/dcg.md`. The third is the honest fallback, not a workaround — Codex is not
  unguarded, just not guarded by *our* boundary.
- Until then this record exists to make its absence explicit rather than an oversight.

## Verification

The version command doubles as the presence check: if the binary is absent it cannot run, and
`ms status` reports the record's `missing` label rather than a failure.

```toml
group      = "Harnesses"
version    = "codex --version"
version_re = "([0-9][0-9.]*)"
check      = "codex --version"
wiring     = "grep -q dcg /home/klaas/.codex/hooks.json"
ok         = "installed"
fail       = "present but not responding"
missing    = "not installed"
```
