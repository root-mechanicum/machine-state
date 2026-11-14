# cm

## Function

`cm` (cass_memory_system), procedural memory for agents: it reflects on sessions that cass has
indexed and distils a playbook of rules, then serves the relevant ones to an agent starting a
task (`cm context "<task>"`). TypeScript, shipped as one self-contained binary.

## Role

**What the machine has learned from its agents' work**, and, by the user's direction of
2026-11-13, also the user's preferences and background (machine-state-ewk): relevance for
digests and continuity for conversations come from here rather than from fixed prompts.

## Ownership

Upstream `https://github.com/Dicklesworthstone/cass_memory_system`. Not packaged for Arch.

| | |
| --- | --- |
| Version | `v0.5.1` |
| Asset | `cass-memory-linux-x64`, 152,508,592 bytes |
| SHA-256 | `fa2753dbe6be47e567e530eea10d62af76d1ed31012543294d8ba3b001b8f652` |
| Config | `~/.local/share/cass-memory/config.json` (written by `cm init`, then edited by hand) |
| Playbook | `~/.local/share/cass-memory/playbook.yaml` (cm resolves its `~/.cass-memory` default here) |

Installed 2026-11-13: `gh release download`, checked against the release `.sha256`, copied to
`~/.local/bin/cm`.

## Intent

**Reflection runs on the local model, never a cloud API.** `cm init` defaults to Anthropic.
Changed in config.json: `provider = "openai"`, `baseUrl = "http://127.0.0.1:8000/v1"` (whatever
model server answers there), `model = "qwen3.8-flash-next-iq3_s"`, a placeholder `apiKey`
(the endpoint ignores it; cm wants one), `disableStructuredOutputs = true` (JSON by prompt; the
local servers' structured-output support differs from OpenAI's).

**No cost budget.** cm prices every call at its provider's list rates, so local calls look
like OpenAI spend; the default `$1/day` stopped the first full pass after two sessions
(2026-11-14). `budget.dailyLimit` and `monthlyLimit` are set to 1000000: the local model costs
nothing per call, and a cloud provider would be a separate decision anyway.

**Never learn rules from text strangers wrote.** `sessionExcludePatterns` gains
`/--cap-untrusted--/`: cap's calls on newsletters, notifications and window titles stay
searchable in cass but cannot become rules that every agent later reads.

**Never learn from cap's own calls either.** `/--cap-model--/` is excluded too (2026-11-14): in
those sessions the "user" turn is cap's prompt, and the first full pass read the journal
digest's instructions ("under 300 words, ignore / watch / act") as the person's preferences.

**The person, not just procedure** (machine-state-ewk). cm keeps a diary per session, and its
`preferences` field is what the session showed about the person. `cap act profile.update`
merges new diaries into `~/.local/state/agents/profile.md`, which the person edits freely, and
digests read it in place of a hand-written context. The playbook stays agent procedure.

**Not yet decided:** cross-agent enrichment (`cm privacy`), hooks into the agents
(`cm hook`), and a regular pass through cap. The user's direction: run a first pass, look at
what it learned together, then adapt.

**Uninstall:** delete `~/.local/bin/cm`, `~/.local/share/cass-memory/`,
this record.

## Verification

```toml
group      = "Applications"
version    = "cm --version"
version_re = "([0-9][0-9.]*)"
presence   = "test -x /home/klaas/.local/bin/cm"
check      = "cm --version"
ok         = "runs"
fail       = "binary present but does not run"
missing    = "not installed"
```
