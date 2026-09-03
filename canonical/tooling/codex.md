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

  **Re-checked 2026-09-03: one of the two obstacles is gone, and the other is smaller than it
  looked.** What was recorded on 09-01 as two blockers now reads:

  1. ~~`bd setup codex` owns both hooks files~~ — **false as of bd 1.2.2.** Its Codex recipe merges
     by event key rather than rewriting the file. Proven with a negative control: a foreign
     `PreToolUse` entry was added *and* bd's own `SessionStart` entry was corrupted, so bd had to
     rewrite. It repaired its own entry and left the foreign one byte-identical. Without breaking
     bd's entry first the test would have proved nothing, since bd might simply not have written.
  2. The trust hash is content-keyed, so editing the entry requires re-approval. Still true, and
     still a feature — it just means the wiring cannot be silently reprojected.

  **Codex's side is ready.** `[features] hooks = true` is set, `pre_tool_use` is a real event in
  0.151.0 (`hooks/src/events/pre_tool_use.rs`), the shell tool is named `bash`, and bd occupies only
  `PostCompact`, `PreCompact`, `SessionStart` and `UserPromptSubmit` — the `PreToolUse` slot is
  free.

  **dcg's side is not.** `dcg install` wires Claude by default and has `--grok`, `--agy`,
  `--opencode` and `--omp`. There is still **no `--codex`**, so the entry has to be written by hand
  even though dcg speaks the protocol. dcg 0.13.9's own help lists Codex CLI among supported
  harnesses and says compatible agents "including Codex" receive protocol-specific stdout JSON;
  that describes the runtime, not an installer.

  So the remaining work is a hand-written `PreToolUse` entry plus one interactive trust approval,
  rather than an upstream change. The honest fallback — amending `canonical/tooling/dcg.md` to
  accept `codex sandbox` as Codex's boundary — is no longer the only way out.
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
