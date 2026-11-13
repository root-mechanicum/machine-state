# cass

## Function

`cass` (coding_agent_session_search), one index over every coding agent's session history on
this machine: search, timelines, context for a path, answer packs for agent handoffs. Rust CLI,
one binary. It reads each agent's own files and never writes to them.

## Role

**The machine's memory of what agents did.** `cm` (canonical/tooling/cm.md) learns from it, and
retention depends on it: a conversation may be dropped only once cass has indexed it.

## Ownership

Upstream `https://github.com/Dicklesworthstone/coding_agent_session_search` (Jeffrey Emanuel's
Agent Flywheel, like `dcg` and `ee`). Not packaged for Arch or CachyOS.

| | |
| --- | --- |
| Version | `v0.11.0` |
| Asset | `cass-linux-amd64.tar.gz`, 40,786,866 bytes |
| SHA-256 | `d7b3804847c0b39dd3831e82e4a40d85549147147196810805638f211c5c9812` |
| Data | `~/.local/share/coding-agent-search/` (the index; private, like the histories it holds) |

Installed 2026-11-13 the `ee` way: `gh release download`, checked against the release's
`.sha256` and `SHA256SUMS`, `cass` copied to `~/.local/bin/cass`. Not upstream's installer.

## Intent

**Everything any agent does is readable by cass** (machine-state-rrt). Where each one's history
is, and what keeps it:

| Agent | History | Kept by |
| --- | --- | --- |
| Claude Code | `~/.claude/projects` | `cleanupPeriodDays: 36500` in `~/.claude/settings.json`; the default deletes after 30 days, and history before 2026-10-20 was already gone when this was found |
| Codex | `~/.codex/sessions` | Codex's default (no cleanup) |
| Pi, interactive | `~/.pi/agent/sessions/<workspace>` | Pi's default |
| local-pi (worker) | `~/.pi/agent/sessions/<workspace>` | local-agent-harness no longer passes `--no-session` (7721252) |
| cap's threads (/ask, discussions) | `~/.pi/agent/sessions/--cap-threads--` | bin/cap, moved there from `~/.local/state/agents/threads` |
| cap's direct model calls | `--cap-model--`, and `--cap-untrusted--` for input strangers wrote | bin/cap writes each as a Pi v3 session |

**Nothing is dropped before cass has it.** No agent here deletes its own history now. Pruning
old conversations is allowed only after an index that includes them; not built yet.

`~/.cursor` holds only dcg's hook (written by `dcg install`, 2026-08-30). Cursor is not
installed; cass's "1 cursor session" is that folder.

**Uninstall:** delete `~/.local/bin/cass`, `~/.local/share/coding-agent-search/`, this record.

## Verification

```toml
group      = "Applications"
version    = "cass --version"
version_re = "cass ([0-9][0-9.]*)"
presence   = "test -x /home/klaas/.local/bin/cass"
check      = "cass --version"
ok         = "runs"
fail       = "binary present but does not run"
missing    = "not installed"
```
