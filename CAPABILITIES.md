# CAPABILITIES.md

**Status: design. Nothing here is implemented.** This is the design pass `machine-state-yxb`
asked for — the capability model, event semantics, and authority boundaries for reactive and
scheduled operation on this workstation.

`SUBSTRATE.md` governs **state**: what should be true, who owns it, how drift is found. This
governs **action**: what can be done, on what trigger, under whose authority.

---

## 1. What this is, and what it must never become

A **capability broker**: a peer to `bin/ms`, never part of it.

`ms` stays content-agnostic and concerned only with canonical projection and drift. The broker
runs, listens, invokes, and records. Folding the second into the first would give the projector a
runtime, and give the runtime the projector's write access — see §6.

The relationship is the one this repository already has with `dcg`: **recorded under
`canonical/tooling/`, verified by a declared check, never owned.**

## 2. Event model

### Sources, all verified present on this machine

| Source | Reaches | Transport |
| --- | --- | --- |
| Hyprland `.socket2.sock` | windows, workspaces, monitors | UNIX socket, `name>>payload` lines |
| `org.freedesktop.Notifications` | notifications | D-Bus, session |
| `org.freedesktop.UPower` + `BAT0` | battery, AC | D-Bus, system |
| `org.freedesktop.NetworkManager` | connectivity | D-Bus, system |
| `org.freedesktop.login1` | session, idle, lock | D-Bus, system |
| `org.freedesktop.systemd1` | unit state, crashes | D-Bus, system |
| `dev.noctalia.Mpris` | media | D-Bus, session |
| `systemd --user` timers | scheduled | timer units |

Hyprland's socket was read with nothing but Python's `socket` module — 40 typed events in nine
seconds. Every source above is reachable from the stdlib or `busctl`. **No new runtime is
required**, which matters on a machine with no node, go, or rust toolchain.

### A timer is an event

`time.daily` differs from `mail.received` only in what produced it. One model covers both, so
scheduling needs no scheduler — a systemd timer emits an event like anything else. This is the
single largest simplification available, and it is why "scheduled" costs almost nothing once
"reactive" exists.

### Envelope

Every event is normalised into one typed shape before policy sees it:

```
event      hypr.window.opened          namespaced, source-prefixed
source     hypr | dbus | timer | agent | fs
observed   2026-09-01T16:42:11.204Z
payload    { ... }                     typed per event name, never a raw string
provenance { socket, instance, pid }   how we came to believe this
```

**Provenance is not optional.** An event that cannot say where it came from cannot be trusted to
authorise anything, and the record it leaves is worth little for later analysis.

### Bindings are declared, not discovered

A binding maps an event to a capability. Bindings live in manifests. **Nothing is executed because
it was dropped in a directory** — the pattern `yxb` explicitly rejects, and rightly: a
drop-in directory is an execution path with no declared authority.

## 3. Capability model

A capability is a **named, bounded operation with declared effects**. Not a script — a contract.

```toml
[capability."mail.triage"]
description = "Classify unread mail and propose actions as a bead"
inputs      = { since = "duration", limit = "int" }
effects     = ["reads mail", "creates a bead"]
consequence = "report"
implement   = { kind = "command", run = "ms-mail triage" }
```

`implement.kind` may be a command, an MCP tool, or a local service **without changing the policy
model**. That indirection is the point: how a capability is built must not determine what it is
allowed to do.

### One capability, several interfaces

The same declaration serves an agent, a CLI, a Noctalia menu entry, and optionally a Hyprland
binding. Human and agent automation must not become separate systems with separate authority —
that is how the two drift apart and only one stays governed.

### Discoverable, not memorised

The broker emits its own catalogue as JSON: names, inputs, effects, consequence class, and whether
a capability may currently run unattended. An agent inspects rather than recalls. This is the
machine-readable half of `yxb` item 3; the human half is the same data rendered as a menu.

## 4. Consequence classes — the authority model

`SUBSTRATE.md` and the `machine-state` skill currently express authority as *free / ask-first /
never*. **That cannot survive unattended operation**, because "ask" needs someone to answer.
Unattended, it degrades into blocking forever or proceeding anyway, and neither is what the words
meant.

The replacement is a class declared on the capability, before it ever runs:

| Class | Changes | Unattended |
| --- | --- | --- |
| `observe` | nothing | always |
| `report` | adds a record a human will read — a bead, a notification | always |
| `adjust` | reversible session or desktop state — layout, volume, theme | only where a binding grants it |
| `commit` | durable or outward — files, packages, anything leaving the machine | never; raises for a human |

Two properties decide the class: **reversibility** and **whether the effect leaves the machine**.

This is what reconciles wanting unattended operation with `yxb`'s rejection of auto-approved
agents. **Unattended is not auto-approved.** An `observe` capability firing at 3am holds no
blanket permission; it is safe because its class was declared and its scope was bounded by the
event that triggered it.

`commit` never runs unattended. It raises — which on this machine means a bead, labelled for a
human, exactly as `bd human` is used today. Asynchronous supervision, not absent supervision.

## 5. Provenance — the record, emitted rather than harvested

Every invocation emits `agent.action.completed`:

```
binding     dbus.notification.received -> notify.classify
capability  notify.classify
consequence report
inputs      { ... }
outcome     ok | refused | failed | escalated
started     2026-09-01T16:42:11.204Z
duration_ms 340
actor       claude-code | codex-cli | broker
```

This is the piece `dcg history` cannot give us. That journal records **shell commands and whether
they were allowed** — a safety log being read sideways as an action log. It has no intent, no
outcome, and its `session_id` is unique per invocation rather than per session, so it cannot even
group one agent's work together.

Emitting the record at the point of action, structured, removes the need for anything to own agent
lifecycle in order to know what happened. That is how this machine gets a corpus without acquiring
an orchestrator.

**A partial record is worse than none for analysis.** The journal today is almost entirely
`claude-code`; the only `codex-cli` entry is a probe, because Codex is installed but not
dcg-wired. Any conclusion drawn from that corpus about "what agents do here" would really be
"what Claude does here", and would be silently wrong — internally consistent, and biased.
Selection bias in a record is invisible from inside it. Every capability invocation emits, or the
corpus is not worth analysing.

## 6. Boundaries

**Information may flow up from `canonical/`. Authority may never.**

This is the rule that keeps the broker honest, and it is not hypothetical: `canonical/` is
**agent-writable by design** — that is the whole point of `ms project`. So an agent that could
edit its own grants could widen its own authority, which is the failure `dispatch` avoids by
compiling its role table into the binary.

There is no daemon here to compile into, so the split is by file:

| Artifact | Writable by | Holds |
| --- | --- | --- |
| capability manifests | agents, via `canonical/` | what a capability *is* — inputs, effects, class |
| **grants** | **not agents** | which bindings may run unattended, at which class |

A capability declaring itself `observe` means nothing unless a grant outside agent reach agrees.

**Grants live at `/etc/machine-state/grants.toml`, root-owned.** That is the only boundary
available on this machine, and it was chosen after establishing what the alternatives actually are
rather than by preference:

- Everything under `$HOME` is agent-writable — *including dcg's own config*. A write setting
  `fail_closed = false` tests as `ALLOWED`. Not projecting a file keeps `ms` out of it; it does not
  keep an agent out of it.
- dcg's config layering cannot substitute. Its system layer, `/etc/dcg/config.toml`, is the
  **lowest** priority, so a user-writable `~/.config/dcg/config.toml` overrides it. Only the
  project-level `.dcg.toml` is enforcement-only, and that lives in the agent-writable repository.
- `sudo` requires a password here (`sudo -n true` exits 1). Root is therefore a real boundary, and
  the only one, absent new machinery.

The **directory** must be root-owned too, not merely the file. Deleting a file needs write
permission on its directory, so a user-writable directory would let an agent replace the grants
wholesale while the file itself still looked correctly owned.

**Fail-closed, and absence is the safe initial state.** No grants file means nothing runs
unattended. That is not a degraded condition to be fixed; it is where the machine should start.

**The substrate verifies its own boundary.** `ms status` reports the grants state and exits
non-zero if the file or its directory has become writable by this user. A boundary that cannot
report its own compromise is not one.

Also inherited, unchanged:

- **`dcg` remains beneath everything.** The broker invokes capabilities; the guard still sees the
  commands. Neither replaces the other, and the broker must never be a way to run commands that
  would otherwise be refused.
- **Own the smallest addressable region.** A capability touches what its declaration names.
- **Transactional where it can be** — preview, capture before-state, apply, validate, keep a
  rollback. `ms` already does this for projection; `adjust` and `commit` should inherit it.

## 7. What this deliberately does not do

- **No admission control, scope freezing, budgets, or death interpretation.** Those are properties
  of long-lived agents. This model has none: an invocation is bounded by the event that caused it.
- **No sustained autonomous work.** Explicitly out of scope per `SUBSTRATE.md` §Purpose. A machine
  for unattended grinding is a different system and should stay one.
- **No agent spawning.** The broker invokes capabilities. It does not start agents, which is what
  would drag every one of the above back in.

## 8. Open questions, in the order they matter

1. ~~Where do grants live so agents cannot widen them?~~ **Answered 2026-09-02** — see §6. Root
   ownership, verified as a real boundary, with the substrate checking its own boundary and the
   check proven able to fail.
2. **Does the broker need to be resident?** Listening to a socket implies a process, and a process
   implies exactly the lifecycle concerns this design avoids elsewhere. A systemd user unit is the
   obvious answer; `Linger=no` on this machine means it lives only inside the login session, which
   may be acceptable or may not.
3. **What is the first capability?** It should be `observe` or `report` class, and should prove the
   whole path end to end. Mail triage is the motivating case but depends on `machine-state-yr5`.
4. **Does Noctalia emit, or only receive?** Its `plugin ... <event>` dispatches events *to* plugins;
   whether it can be subscribed *to* is unverified. Hyprland and D-Bus are confirmed either way.
5. **How do capabilities reach a human?** Beads is the obvious channel and already carries a
   `human` label. Notifications are more immediate but less durable. Probably both, by class.
