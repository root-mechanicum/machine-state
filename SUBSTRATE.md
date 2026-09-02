# SUBSTRATE.md

## Purpose

This workstation is meant to be **operated** by agents — not merely to run them.

The difference is the whole point. An agent delivered as an application is a tool you open
alongside your other tools. An agent as a control surface is something the machine is arranged
around: it holds window and workspace control, application use, services and notifications, and
whatever comes after, as a policy-governed layer over the OS and the user session rather than a
window on the desktop.

Everything below serves that. Canonical policy, adapters, safety boundaries, provenance and
auditability are kept independent of any single harness precisely so that *the agent* can be
swapped without renegotiating how the machine is governed. If replacing the agent means
re-deciding what it may touch, the substrate has failed.

### What "operated" means here, and what it does not

Operated means **reactive and scheduled**: an agent acts because something happened — mail
arrived, a process crashed, a monitor was connected, a timer fired — and it acts through a
bounded capability whose authority is declared in advance. A timer is just another event, so
one model covers both.

It does **not** mean sustained autonomous work: an agent turned loose on a backlog for hours,
unsupervised. That is a real thing to want and a genuinely different problem — it needs admission
control, scope freezing, budgets, and an answer for what an agent's death means. It belongs on a
machine dedicated to it, as its own system, and this repository should not grow toward it.

The distinction is load-bearing rather than fussy. Reactive and scheduled work needs no admission
control, because the event *is* the admission decision and the payload bounds the scope. The
failure modes that dominate sustained autonomy — an agent running for an hour producing nothing,
or dying with uncommitted work — are properties of long-lived agents and simply do not arise
here. Conflating the two would import all of that machinery to solve problems this machine does
not have.

Note also that **unattended is not the same as auto-approved.** A capability that runs on an event
without a human present is not an agent holding blanket permission; what makes it safe is that its
consequence class was declared before it ran.

## The contract

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
derived/               produced here by a tool from canonical declarations — see §2
```

Policy is **ordered fragments rather than one file** because two harnesses must share most rules
and differ in a few without anybody hand-mirroring text between files. That mirroring is exactly
what rotted the pre-substrate `CLAUDE.md` and `AGENTS.md`.

## 2. Ownership

Every path falls in exactly one class.

| Class | Meaning | Written by |
| --- | --- | --- |
| **CANONICAL** | authored here | a human |
| **DERIVED** | produced here from canonical, inside the repository | a tool in `bin/` |
| **VENDOR** | owned by another tool's installer | that tool |
| **PROJECTED** | derived from canonical, outside the repository | `bin/ms` |

**DERIVED exists because leaving it out was already causing damage.** `cap render` writes a
Hyprland fragment from the key binding declarations, and that file sat in `canonical/` and was read
by an adapter as a canonical source. So a generated intermediate held the ownership class of
authored truth, and the sentence "canonical content is what a human authored here" was false about
one of its own files. Three classes could not describe the thing, so it was filed under the nearest
one — which is how classifications quietly stop being true.

Derived is not projected. Both are generated, and they differ in the way that matters here: a
projected path is **outside** the repository, so `ms` writes it, records a hash, and can detect that
someone changed it. A derived path is **inside** the repository, so git records it, and `ms` may
read it but must never write it. Ownership of the file stays with the tool that produces it.

**Only CANONICAL and DERIVED may be adapter sources**, and `bin/ms` now enforces that rather than
merely asserting it. A vendor path as a source would project another tool's output as though it
were our decision; a path outside the repository would break §1. This rule spent months as prose
that nothing checked, and it was already broken.

A derived file is **committed**, not regenerated on demand. Otherwise `ms diff` could not answer
"does the machine match the repository" without first running every producer, and the chain from
declaration to live file would stop being auditable from a single commit.

Current assignment:

| Path | Class | Note |
| --- | --- | --- |
| `README.md`, `BASELINE.md` | CANONICAL | the only human-authored files as of v0.01 |
| `SUBSTRATE.md` | CANONICAL | this file |
| `canonical/**` | CANONICAL | |
| `derived/**` | DERIVED | `cap render` writes `derived/hypr/bindings.lua`; `ms` reads it, never writes it |
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

**The record belongs to one repository and one `$HOME`, and says so.** Its paths are absolute, so it
means nothing anywhere else — and acting on it elsewhere is not merely useless but destructive,
because orphan reconciliation removes recorded targets that no manifest claims any more. `ms` stores
the pair it was written for and ignores a record written for another.

That guard was bought. A test copied the live `state/` into its sandbox, dropped all but one adapter,
and ran `project`; the six now-unclaimed records still named the real `$HOME` and the real
repository, so a supposedly hermetic test unprojected the live workstation — `CLAUDE.md` and
`AGENTS.md` lost their regions, both skill symlinks went, and the Hyprland fragment was deleted.
Everything was restored by `ms project` and verified byte-identical, which is the one part that
worked as designed.

The lesson generalises past this file: **a copy is not a sandbox if it inherits something that
points outside itself.** The tree was faithfully copied and the one file holding absolute paths made
the copy an alias for the original.

`ms diff` compares each target against what canonical would produce now and exits non-zero on any
difference. A hand-edit is a **detectable, reportable condition — never a merge**. Canonical wins;
`ms project` restores.

**A difference has two possible causes, and they want opposite responses.** Either the target was
changed by something else, or canonical moved ahead and has not been projected yet. Reporting both
as "drifted" hides the only thing worth knowing, so every difference is annotated with its cause,
determined from the hash recorded in `state/projection.json`: a target still matching what we last
wrote differs only because canonical moved; a target matching neither was changed by something else.

`ms propose` is the review seam. It reports what `ms project` would do — the cause and the line
extent of each change — and changes nothing. It exits non-zero when anything is pending, so it
answers "is there an unapplied change" without applying one.

Note what `propose` is not. It is **review, not enforcement**: it makes a change visible before it
reaches the machine, but it cannot stop an agent editing canonical and running `project` anyway.
Since `canonical/` is agent-writable by design, an agent can still widen its own rules. Closing
that needs the grants mechanism in `CAPABILITIES.md` §8, which is unresolved.

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

**A negative control must disable exactly the mechanism under test, and demonstrate that the
positive assertion would then miss the defect.** Anything less manufactures confidence. This has
been got wrong twice here: once by disabling an existence check rather than the comparison beneath
it, so the code fell through to a different error and a problem was still reported; and once by
asserting on an exit code that two independent mechanisms could set, so the control passed for the
wrong reason. Both times the control looked correct and tested nothing. When a control passes,
confirm it passed *because* the mechanism was disabled.

### Attribution

`ms diff` answers *what* differs. For an agent acting as a control surface, the useful question is
*who* — because the right response differs entirely: your own change probably wants promoting to
canonical, a vendor's wants leaving alone, a human's wants offering rather than overwriting.

So a drifted or foreign target is annotated from the **agent action journal**: `dcg history`, which
records every command an agent runs through its hook with `agent_type`, `session_id`, `working_dir`
and `timestamp`. That is not what dcg was built for, but it is the only agent-neutral record on
this machine of what an agent actually did. Records carry `projected_at`, so the annotation can say
whether a mention came before or since the projection.

This is deliberately **evidence, not inference**. The annotation reports the most recent journal
entry naming the path, excerpted around the mention, and draws no conclusion. Three reasons, each
learned the hard way:

- dcg journals an **entire shell block as one entry**. A single record routinely holds a read of one
  file, a write to another, and the projection that followed. Which of them touched this path is
  not recoverable, so any "X changed this" claim is a guess.
- The journal **sees shell only**. A harness's own file-editing tools write elsewhere, and another
  agent's may write nowhere. Absence of a mention is not evidence a human did it.
- The timestamp is when a command was **submitted**, not when each part of it ran, so a change and
  the projection that followed it can appear in the wrong order.

A confident wrong attribution is worse than none: it names a culprit and gets believed. Show the
command; let the reader judge.

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

### 7.1 Our own tools, and why there are three

`bin/ms` projects canonical content onto the machine and reports drift from it. `bin/cap` derives
the desktop's key bindings and action surface from semantic declarations. `bin/machine` sequences
the two. They are peers; none imports another.

The third one was **built only after it was measured**, and the measurement is worth keeping because
it contradicts the obvious reason for building it. Six ordinary editing changes were made and each
was observed at three stages. Three of the six needed the two steps at all — the derived artifact
carries only *chord → action + arguments*, so labels, role commands and window classes resolve at
invocation and need nothing rendered or projected. For the three that did, this held every time:

| outstanding step | `cap check` | `ms diff` |
| --- | --- | --- |
| render | **fails** | "all targets match canonical" |
| project | ok | **fails** |

The problem was never that a forgotten step goes undetected. It is that **the other tool reports
success** — so there was no single command that answered "is the machine current with my
declarations?", and asking the wrong one returned a confident, wrong yes. A missing signal invites
checking; a reassuring one does not.

`machine status` asks both. `machine apply` runs the sequence with the render/project race closed:
fingerprint the vendor file, render, confirm the fingerprint is unchanged, project, post-check, and
on failure restore the previous projection and say so loudly.

**Recovery is whole-artifact, not per-binding.** Disabling only a newly introduced chord would mean
a tool deciding which declaration to ignore, and a projection that silently omits one binding is a
machine that disagrees with its own declarations — the failure everything here exists to prevent.
An unrelated pending change reverts along with the bad one; that is visible in the output and fixed
by editing and applying again.

`machine` must never grow logic of its own. It runs the other two as subprocesses and reports what
they say, because anything it decided for itself would be a third opinion about a machine that is
supposed to have one.

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
- No sustained autonomous agent work — no admission control, scope freezing, budgets, or death
  interpretation. Reactive and scheduled operation only; see Purpose. A machine dedicated to
  unattended grinding is a different system and should stay one.
- No secrets management.
- No LLM in the projection loop. `bin/ms` is deterministic; that is the point.
- No daemon, no timer, no background process. `ms` runs when invoked.
- No `~/.codex/` layout while Codex is not installed. Manifests grow when software does.
- No adoption of the global `~/.claude/settings.json`. It is hand-written and holds the `dcg`
  hook — the FOREIGN case, and the first thing the refusal path must protect.
- No machine telemetry. It may return later as a tenant of this substrate, never as its foundation.
