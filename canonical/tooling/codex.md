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

Ours by narrow region only: the `MACHINE-STATE POLICY` region of `./AGENTS.md`, and the linked
skill directory `~/.codex/skills/machine-state` — a sibling of Codex's own `.system/`, never the
`skills/` parent.

`~/.codex/config.toml` deserves separate mention: `bd setup codex --global` writes it, but **Codex
itself then rewrites it**, expanding 24 bytes into a trust store. It is app-written in the same
sense as Noctalia's config, and not a projection candidate.

**Not installed on this machine.** `~/.codex/` does not exist, which is why the adapter has a
single in-repo target and no home layout. We do not invent paths for absent software; the manifest
grows when the software arrives.

## Intent

- When Codex is installed, two things must follow before it is trusted here: the safety guard is
  wired for it, and its adapter grows whatever home-directory targets are then real.
- **Codex is installed and NOT dcg-guarded.** The `wiring` check below fails deliberately, so
  `ms status` reports it rather than staying quiet about a live gap.

  **dcg works with Codex — this was proven, not assumed.** On 2026-09-01, with a `PreToolUse`
  entry in an isolated `CODEX_HOME`, `codex exec` fired the hook and the command landed in
  `dcg history` tagged `agent_type = "codex-cli"`. The journal is therefore genuinely
  agent-neutral, not a field with one value: it now holds both `claude-code` and `codex-cli`.

  **The blocker is hook trust, not placement.** Codex records a per-hook SHA-256 in
  `~/.codex/config.toml` under `[hooks.state."<file>:<event>:0:0"]`, written when a hook is
  approved interactively. An untrusted hook is **skipped silently** — no warning, no log line. The
  first probe failed for exactly this reason and looked like a protocol failure;
  `--dangerously-bypass-hook-trust` is what distinguished the two.

  Two obstacles remain, both narrow:

  1. `bd setup codex` owns both hooks files, so an entry we add may be dropped by its next run,
     and `ms diff` would not notice — the file is not a managed target.
  2. The trust hash is content-keyed, so editing the entry requires re-approval. That is a
     feature, but it means the wiring cannot be silently reprojected.

  Ways out: dcg gains a `--codex` installer that merges rather than replaces; bd's recipe leaves
  room for a foreign `PreToolUse`; or the intent in `canonical/tooling/dcg.md` is amended to
  accept `codex sandbox` as Codex's boundary. The last is an honest fallback rather than a
  workaround — Codex is not unguarded, only unguarded by *ours*.
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
