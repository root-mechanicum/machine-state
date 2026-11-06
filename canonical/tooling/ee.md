# ee

## Function

Eidetic Engine (`ee`), a local-first memory store for agents: typed memories with provenance URIs,
confidence and decay, hybrid lexical and semantic search, token-budgeted context packs (`ee pack`),
explanations (`ee why`), sealed pre-registration (`--seal`) and attempt families (`--family`,
`--of-n`). Rust CLI, one binary.

**Here it exists for one workspace: `~/src/research_library`**, as the research agents' memory of
verbatim evidence, claims and experiment results. The library itself — originals, text, reading
documents, catalog — stays the source of truth; `ee` is rebuilt from it and is not versioned
(`.ee/` is gitignored there).

## Role

An application with per-workspace state. The database lives in `<workspace>/.ee/`; the embedding
model lives once per user in `~/.local/share/ee/models/`.

## Ownership

Upstream `https://github.com/Dicklesworthstone/eidetic_engine_cli`, MIT with an OpenAI/Anthropic
rider. Not packaged for Arch or CachyOS. Distributed as release tarballs with `.sha256` and
`.minisig` files; SLSA provenance is not yet published for this version.

| | |
| --- | --- |
| Version | `v0.18.0` |
| Asset | `ee-x86_64-unknown-linux-gnu.tar.xz`, 33.7 MB |
| SHA-256 | `a8c78867c10855cff4914b673bd3075fc4d7bc912065a8dcfbf9971dfb8890fc` |
| Embedding model | `potion-multilingual-128M`, 512 MB, `F32 [500353, 256]`, downloaded by `ee` itself |

## Intent

**Install the pinned binary by hand, not with upstream's installer.** `install.sh --easy-mode`
also edits `PATH` and installs shell completions; here `~/.local/bin` is already on `PATH`, so the
install is: download the tarball with `gh release download`, check it against the `.sha256`,
extract `ee` to `~/.local/bin/ee`.

**The model downloads once per machine and cannot be seeded.** Tested 2026-10-24 in a throwaway
`HOME`: `ee model fetch embedding-default --from-file` is refused ("only supported for rerank
artifacts"), and copied model files — with or without their `.verified` record — are ignored and
re-downloaded. The first download took about ten minutes of one-minute retries before a 512 MB
attempt completed. After it, set `EE_EMBED_DOWNLOAD=off` for agent runs so a timeout can never
start a re-download mid-run.

**Model registration is per workspace; the files are per user.** A workspace initialised after
the download starts with the model "registered, available: 0" and silently uses hash vectors
(`ee model status` reads `hash_fallback`, packs say `embed_backend: hash_fallback`).
`ee model fetch embedding-default --workspace <ws>` registers the files already on disk in under
a second, with no download; then `ee index rebuild`. Found 2026-10-24 after rebuilding the
library's store.

**The reranker must be supplied by hand.** `ee model fetch rerank-default` refuses network
fetch in this build, and the manifest's Hugging Face fallback returns 401. The primary source
works: the `rerank-default-v1` release of eidetic_engine_cli, `rerank-default-v1.tar.zst`,
82,767,464 bytes, SHA-256 `adaada3ccc15ae535e9bea238d2ec05e4f39726bdcad07dd87cba9f85dc10edb`
(matches `src/data/rerank_model_manifest.json`). Register it per workspace with
`--from-file`; it is ms-marco-MiniLM-L-6-v2. On the library's 30-question eval it raised hit@5
from 0.20 to 0.60.

**Workspace init must not touch bd's files.** In a workspace that already has `AGENTS.md` and
`CLAUDE.md` (both owned by `bd setup`), `ee init` refuses without `--force`;
`ee init --workspace . --force --skip-boilerplate` initialises `.ee/` and leaves both files
byte-identical (verified by checksum in a throwaway copy).

**Decay is set per workspace.** Defaults forget unclassified memories on a 30-day half-life; the
library's `.ee/config.toml` sets `[learn.decay] default_half_life_days` and
`semantic_fact_half_life_days` to 36500.

**Not done: harness hooks.** `ee hook claude-code --install` would write into `~/.claude`, which
this repository projects. Decide that separately.

**Uninstall:** delete `~/.local/bin/ee`, `~/.local/share/ee/`, and each workspace's `.ee/`; delete
this record.

## Verification

Installed 2026-10-24: tarball checked against the pinned SHA-256 and the release `.sha256`, `ee`
copied to `~/.local/bin/ee`, `ee --version` reads `ee 0.18.0`. Workspace initialised in
`~/src/research_library` with `--force --skip-boilerplate`; bd's `AGENTS.md` and `CLAUDE.md`
checksummed identical before and after. Model fetched with `ee model fetch embedding-default` in
3 min 37 s this time (530,977,691 bytes, `blake3:868e96c7…`), registered as available;
`ee model status` reads `neural_local`, `semantic=true`.

```toml
group      = "Applications"
version    = "ee --version"
version_re = "ee ([0-9][0-9.]*)"
presence   = "test -x /home/klaas/.local/bin/ee"
check      = "ee --version"
ok         = "runs"
fail       = "binary present but does not run"
missing    = "not installed"
```

There is no package manager to ask whether the files are intact, so the check is that the binary
runs and reports the pinned version; the SHA-256 above is what was installed.
