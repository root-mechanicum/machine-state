# SUBSTRATE.md

The contract for how this repository governs the machine it describes.

`machine-state` is the canonical source of truth for this workstation's configuration and agent
policy. The resident agents are Claude Code, Codex, and whatever local agents come later; this
repo is not one of them. It is the ground they stand on. Everything they read elsewhere on this
machine is either a **projection** of what lives here, or is owned by another tool and merely
**recorded** here.

**Extending the substrate:**

| To add | Do this | Never do this |
| --- | --- | --- |
| an agent | add `adapters/<agent>.toml` | change `bin/ms` |
| managed config | add a directory under `canonical/` | special-case it in the projector |
| a substrate tool | add `canonical/tooling/<tool>.md` | copy its generated files into `canonical/` |

Status: v0.01 contract, established 2026-08-31.

---

## 1. Canonical

The repository is the source of truth. Canonical content is what a human authored here.

```
canonical/policy/      agent-neutral operating rules, as ordered fragments
canonical/policy/agents/   agent-specific rules — still canonical, selected by one adapter
canonical/skills/      agent-neutral skill trees
canonical/tooling/     one record per substrate tool
canonical/desktop/     managed desktop config (Hyprland; Noctalia pending)
```

Policy is **ordered fragments rather than one file** because two harnesses must share most rules
and differ in a few without anybody hand-mirroring text between files. That mirroring is exactly
what rotted the pre-substrate `CLAUDE.md` and `AGENTS.md`.

## 2. Ownership

Every path falls in exactly one class.

| Class | Meaning | Written by |
| --- | --- | --- |
| **CANONICAL** | authored here | a human |
| **VENDOR** | owned by another tool's installer | that tool |
| **PROJECTED** | derived from canonical | `bin/ms` |

Current assignment:

| Path | Class | Note |
| --- | --- | --- |
| `README.md`, `BASELINE.md` | CANONICAL | the only human-authored files as of v0.01 |
| `SUBSTRATE.md` | CANONICAL | this file |
| `canonical/**` | CANONICAL | |
| `CLAUDE.md` | VENDOR | `bd setup claude`; we co-own one marker region |
| `AGENTS.md` | VENDOR | `bd setup codex`; carries two bd blocks |
| `.claude/settings.json` | VENDOR | `bd setup claude`, whole-file JSON |
| `.codex/config.toml`, `.codex/hooks.json` | VENDOR | `bd setup codex` |
| `.agents/skills/beads/**` | VENDOR | bd owns `beads/`, **not** the `skills/` parent |
| `.beads/**` | VENDOR | bd's data dir, incl. generated `issues.jsonl` |
| `.gitignore` | VENDOR | written by `bd init`; **no marker pair**, see below |
| `state/**`, `adapters/**`, `bin/**` | PROJECTED / ours | |
| `~/.config/hypr/config/machine-state.lua` | PROJECTED | a module we create, loaded last |
| `~/.config/hypr/hyprland.lua` | VENDOR | CachyOS skel; we co-own one marker region |
| the rest of `~/.config/hypr/**` | VENDOR | pristine copy of `/etc/skel`, package-maintained |

Two paths need care:

- **`.gitignore`** is vendor-authored but carries only a comment header, not a marker pair. It is
  co-owned by convention rather than protocol. Append a commented section; never rewrite it whole.
- **`.beads/issues.jsonl`** is untracked, not gitignored, and regenerated automatically
  (`export.auto: true`). It will keep reappearing in `git status`. The substrate does not manage it.

A VENDOR file is **not ours to own, but may be ours to touch** — see §4.

## 3. Adapters

`adapters/<name>.toml`. A manifest, never content. Adding an agent — or any other managed target
system, such as a desktop compositor — is adding a manifest; it must never require editing
`bin/ms`.

```toml
[[target]]
kind    = "render" | "link" | "splice"
path    = "./CLAUDE.md"
sources = ["canonical/policy/10-identity.md", "..."]
marker  = "MACHINE-STATE POLICY"   # splice only
comment = "html" | "hash" | "dash" # splice only
```

Three keys on every target, plus two on `splice`. `comment` is stated explicitly rather than
inferred from the file extension: guessing a comment syntax from a filename is precisely the
content-awareness §4 forbids. The projector composes its delimiters from `marker` and `comment`
alone — `<!-- BEGIN … -->` for `html`, `# BEGIN …` for `hash`, `-- BEGIN …` for `dash`.

No conditionals, no templating language, no per-agent code paths. If an adapter needs logic, the
design is wrong. The full schema, with a worked example, is in `adapters/README.md`.

## 4. Projection

One way, canonical → target. Three mechanisms, and only three:

| kind | owns | use for |
| --- | --- | --- |
| `render` | the whole file | files we create |
| `link` | a symlinked directory | skill trees |
| `splice` | the bytes between two literal markers | files we co-own with a vendor |

The projector is **content-agnostic**: it concatenates fragments, symlinks directories, and
replaces bytes between literal delimiters. It never parses Markdown, Lua, or TOML. That is what
lets Hyprland's `.lua` files and Noctalia's `.toml` join later without changing it.

### Governing principle

> **Own the smallest addressable region, never the container.**
>
> - Within a file: our marker pair, never the whole file.
> - Within a directory: our own subdirectory, never the shared parent.

This is not a style preference; it is the reason co-tenancy works at all. `bd` follows the same
rule — it owns `.agents/skills/beads/`, not `.agents/skills/` — and that is the only reason its
installers and this substrate can write to the same file without a rewrite war.

Verified 2026-08-31 against bd 1.2.2: `bd setup` replaces only its own marker pair, appends at
end-of-file when its markers are absent, removes only its own block on `--remove`, and leaves
foreign blocks and all out-of-marker content untouched.

**Corollary:** never `render` a vendor file. A whole-file render would delete the vendor's block,
the vendor would re-append it on its next install, and `ms diff` would report drift forever.

### The seam

| Agent | kind | target | marker |
| --- | --- | --- | --- |
| Claude | `splice` | `./CLAUDE.md` | `MACHINE-STATE POLICY` |
| Codex | `splice` | `./AGENTS.md` | `MACHINE-STATE POLICY` |
| Hyprland | `splice` | `~/.config/hypr/hyprland.lua` | `MACHINE-STATE` |

The same marker name for both harnesses, so each receives identical canonical policy through an
identical mechanism. That is the interchangeability this substrate exists to buy.

Hyprland is seamed differently and it is worth saying why. Its spliced region is a single
`require` line; the content lives in a module we render alongside the template and load **last**,
so what we set overrides what CachyOS ships. Of roughly a thousand template lines, two were ever
ours. Canonicalising the rest would have forked a package-maintained template into `canonical/` —
the same mistake as absorbing a vendor's boilerplate as policy. Verified on 2026-09-01: with both
template files reverted to pristine `/etc/skel`, the live keyboard layout and monitor mode are
held by our module alone.

## 5. Drift

Every realised target is recorded in `state/projection.json` with source and target hashes.

`ms diff` compares each target against what canonical would produce now and exits non-zero on any
difference. A hand-edit is a **detectable, reportable condition — never a merge**. Canonical wins;
`ms project` restores.

`ms status` reports one line per target and per tool, grouped. Every line is the result of running
a declared check, never a hardcoded string. A check that cannot run reports `unknown`, never `ok`.

**Its exit code carries a narrower meaning than the output.** Only a safety failure is fatal: a
harness that is installed but not covered by the command guard prints `** UNGUARDED **` and exits
non-zero. Health failures — a tracker that will not answer, a stale vendor integration, a tool
present but not responding — are reported on their line and exit `0`. The distinction is
deliberate: an agent operating without a guard is a different class of problem from an integration
that has drifted. Read the output, not just the status.

Every `check` in a tooling record must be **verified to fail**, not merely to pass. A check that
cannot fail reports green for the wrong reason, which is the exact failure these records exist to
prevent — and one that has already happened here once, when a record used a command that exits `0`
even when its own checks fail.

## 6. Promotion

The reverse path — a target edit becoming canonical — is **manual and human-initiated**. The
substrate never guesses that a hand-edit was intentional.

`bin/ms` writes a target only if it is:

1. absent, or
2. a symlink this repo owns, or
3. byte-identical to what `state/projection.json` records, or
4. *(splice only)* a file where our marker pair is the only region touched.

Anything else is refused and reported with its class:

- **FOREIGN** — a human wrote it. Remedy: promote into canonical, or retarget.
- **VENDOR** — another installer owns it. Remedy: leave it to that tool, or claim a region via `splice`.

First contact with a file we did not create must never be a silent overwrite.

## 7. Tooling

Tools that are part of the substrate get a record at `canonical/tooling/<tool>.md`. We record what
a tool is for and what we require of it. We never absorb its generated files as canonical policy.

Five sections: **Function, Role, Ownership, Intent, Verification.**

`Verification` names a runnable command and its success condition — a tooling record is a
**declared check, not prose**, and `ms status` runs it. A tool with no such check gets a record
saying `none available`, so the gap stays visible rather than papered over.

Versions do not belong here. `state/tooling.json` is derived by `ms status`. `BASELINE.md` is a
frozen point-in-time capture and is **not** maintained as an inventory — it already omits `bd`,
having been written twelve minutes before `bd init` ran.

## 8. Boundary

- Runs as the login user. **Never root, never `sudo`.**
- Writes only paths declared as targets in `adapters/*.toml`. No wildcard writes.
- **No network. No package installation. No system mutation.**
- **Never invokes git.** `bin/ms` produces files; a human commits them.
- `ms unproject` removes every target this repo owns and leaves nothing behind. A substrate you
  cannot cleanly remove is not something to install on a working machine.

`dcg` is the command-safety boundary beneath the agent harnesses. It is not part of this repo's
authority and this repo does not configure it; see `canonical/tooling/dcg.md`.

## 9. Non-goals (v0.01)

Deliberately out of scope. Each is a decision, not an oversight.

- No reverse auto-sync. Promotion is manual, always.
- No agent-initiated git: no commit, no push, no Dolt remote sync.
- No root, no `sudo`, no privileged execution.
- No network access.
- No package installation or system mutation.
- No Noctalia. Hyprland is managed as of 2026-09-01; Noctalia is deferred because it has no
  include mechanism, TOML forbids the duplicate keys an override would need, and its config is
  likely app-written. See `machine-state-uvc`.
- No multi-machine or cross-machine sync.
- No secrets management.
- No LLM in the projection loop. `bin/ms` is deterministic; that is the point.
- No daemon, no timer, no background process. `ms` runs when invoked.
- No `~/.codex/` layout while Codex is not installed. Manifests grow when software does.
- No adoption of the global `~/.claude/settings.json`. It is hand-written and holds the `dcg`
  hook — the FOREIGN case, and the first thing the refusal path must protect.
- No machine telemetry. It may return later as a tenant of this substrate, never as its foundation.
