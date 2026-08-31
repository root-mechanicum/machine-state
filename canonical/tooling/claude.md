# Claude Code

## Function

An interactive agent harness: a terminal CLI with tool access, hooks, skills, and MCP support.

## Role

A **resident agent** — a tenant of this substrate, not part of it. The substrate must not depend
on any single harness, and this record exists so that swapping or adding one is a documented act
rather than an archaeological dig.

## Ownership

VENDOR for the harness itself and its own state (`~/.claude/**`: sessions, history, plugins,
credentials). Never ours to project into wholesale.

Ours by narrow region only:

| Path | Ours |
| --- | --- |
| `./CLAUDE.md` | the `MACHINE-STATE POLICY` marker region |
| `~/.claude/skills/machine-state` | this one subdirectory, never the `skills/` parent |

## Intent

- Canonical policy reaches this harness by splice, never by rendering `CLAUDE.md` whole — a
  whole-file render would delete bd's block and start a rewrite war.
- Shared skills are linked per-skill, so another installer can populate `~/.claude/skills/`
  alongside us.
- `~/.claude/settings.json` stays hand-owned; see `canonical/tooling/dcg.md`.

## Verification

Presence and version from the binary; integration health from bd's own recipe check.

```toml
group      = "Harnesses"
version    = "claude --version"
version_re = "([0-9][0-9.]*)"
check      = "bd setup claude --check"
ok         = "integrated"
fail       = "integration stale"
missing    = "not installed"
```
