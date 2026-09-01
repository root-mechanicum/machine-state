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
- **There is no `wiring` check in this record, and that is a real gap, not an oversight.**
  `dcg install` has flags for Claude, Grok, agy, OpenCode and omp — but none for Codex, and
  `dcg doctor` only inspects Claude's hook registration. So nothing can currently verify that
  Codex is guarded. Establish the wiring by hand when Codex arrives, work out what command proves
  it, and add `wiring` here. Until then this record reports presence only.
- Until then this record exists to make its absence explicit rather than an oversight.

## Verification

The version command doubles as the presence check: if the binary is absent it cannot run, and
`ms status` reports the record's `missing` label rather than a failure.

```toml
group      = "Harnesses"
version    = "codex --version"
version_re = "([0-9][0-9.]*)"
check      = "codex --version"
ok         = "installed"
fail       = "present but not responding"
missing    = "not installed"
```
