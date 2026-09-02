# Cohesion alongside `machine-state-bru`

This is a review of the plan in the `machine-state-bru` epic and all of its children. It is written
for the model that produced that plan, with one additional requirement in view: this workstation
should eventually have the kind of internal cohesion where one theme drives every application,
one authoritative registry drives both live `SUPER` bindings and their preview, and menus, keys,
agents and events all speak the same vocabulary.

**Status: perspective and design input only.** This document does not amend the epic, authorize
implementation, or settle the schemas described below.

## 1. The intent of `bru` is right

The epic correctly identifies a missing runtime layer. The machine has hundreds of commands across
Hyprland, Noctalia, Beads, dcg and `ms`, but they do not form one discoverable, governed interface.
A capability broker as a peer to `ms` is a coherent answer.

The separation from `ms` is especially important and should remain permanent:

- `ms` governs durable desired state, projection and drift.
- The broker governs runtime discovery, invocation, events, authority and provenance.

Combining those jobs would give a resident runtime the projector's write surface and make a small,
content-agnostic tool responsible for application behavior. The epic is right to reject that.

The five phases also form a defensible progression:

1. The registry establishes a namespaced vocabulary and a query/propose/act contract.
2. The desktop provider proves that vocabulary against real windows and workspaces, including
   stable object resolution rather than title guessing.
3. Provenance makes every invocation observable at the point where its outcome is known.
4. Typed events and declared bindings introduce reactive and scheduled operation.
5. Root-owned grants and consequence enforcement permit bounded unattended operation last.

The mechanical tests and agent evaluations are a particular strength. The JSON catalogue is an
interface to a model, so schema tests alone cannot establish that its descriptions lead an agent to
the right operation. Keeping TEST and EVAL separate recognizes that correctly.

## 2. The concern is not a defect in `bru`; it is an adjacent missing layer

The epic deliberately leaves application roles, modes, a human action palette, context capture,
notification integration and extension manifests outside its nucleus. That is good scope control.
However, the plan also leaves out a different category of authority: the declarations that make
the workstation feel like one system rather than a collection of correctly governed tools.

Examples of that missing authority are:

- one semantic theme definition from which application-specific themes are derived;
- one keybinding registry from which both Hyprland configuration and the shortcut preview are
  derived;
- one action vocabulary shared by keys, menus, agents, notifications and event bindings;
- one application-role registry for concepts such as `browser`, `mail`, `terminal` and `editor`;
- one account of which bindings are ours, which belong to a vendor, and which conflict;
- one validation surface proving that the rendered applications agree with their source.

Call this **experience cohesion**. It is not merely visual polish. It is the property that every
surface tells the same truth.

Without it, the capability broker could be excellent while the workstation remained incoherent:
an agent might discover `desktop.window.focus`, a key might run an unrelated shell command, the
Noctalia menu might carry a third name for the same action, and the shortcut preview might document
a binding that no longer exists. All four could work independently while the system as a whole
lied to its user.

## 3. Do not fold cohesion into the capability epic

The answer should not be a sixth `bru` phase. Cohesion spans durable state and runtime action, while
the broker is intentionally about runtime capabilities. Making the broker own themes or generate
Hyprland configuration would violate the same separation that keeps it out of `ms`.

A better decomposition is:

```text
machine-state
├── state governance
│   └── ms: canonical projection, propose, drift and status
├── experience cohesion
│   ├── semantic theme
│   ├── key bindings
│   ├── application roles
│   └── human action catalogue
└── runtime capability broker (`machine-state-bru`)
    ├── capability registry and invocation
    ├── providers and object resolution
    ├── events and event bindings
    ├── provenance
    └── grants and consequence enforcement
```

The cohesion work should become a sibling epic when it is ready to be planned. Its declarations
would be canonical state and its generated files would continue to flow through adapters and `ms`.
It should consume capability names where runtime behavior is needed, but it should not own the
broker or be owned by it.

## 4. The narrow seam: one action identity

The layers meet at a stable, namespaced action or capability identifier:

```text
key binding ───┐
menu entry  ───┼──> desktop.application.open
agent call  ───┤
notification ──┤
event binding ─┘
```

This is the most valuable part of the Omarchy comparison: one operation can be reached from a
command, menu and hotkey because those are interfaces over the same underlying vocabulary. The
local design should extend that coherence to agents and events without granting every interface
the same authority.

The identity may come from the `bru` capability catalogue. The experience registry should refer to
it rather than reproduce its command. For example:

```toml
[[binding]]
id       = "desktop.terminal.open"
keys     = ["SUPER", "RETURN"]
label    = "Open terminal"
action   = "desktop.application.open"
args     = { role = "terminal" }
category = "Applications"
```

The same declaration can supply a Hyprland binding and a row in the authoritative shortcut
preview. A Noctalia menu entry can use the same label, action and arguments. The broker remains
responsible for what `desktop.application.open` means at runtime and whether it may run in the
calling context.

### Two different kinds of binding

`bru` uses *binding* to mean:

```text
event -> capability
```

The experience layer also needs:

```text
key chord -> action
```

These must not share an ambiguous schema or loader merely because both end at a capability. Name
them explicitly, for example `event_binding` and `key_binding`. They have different validation,
ownership and conflict rules.

## 5. Canonical semantic theme

A cohesive theme should describe meaning rather than copy the configuration vocabulary of one
application:

```toml
[color]
background = "#1e1e2e"
surface    = "#313244"
foreground = "#cdd6f4"
accent     = "#89b4fa"
warning    = "#f9e2af"
error      = "#f38ba8"

[appearance]
radius    = 8
opacity   = 0.94
font_ui   = "Inter"
font_mono = "JetBrainsMono Nerd Font"
```

Application adapters translate those tokens into the formats supported by Noctalia, Hyprland,
terminals, GTK, Qt, browsers, editors and TUIs. The canonical theme must not pretend every target
has the same expressive power. An adapter should report unsupported tokens, deliberate mappings
and losses rather than silently guess.

Theme projection belongs to the durable side of the architecture:

```text
canonical semantic tokens -> target adapter -> ms propose/project -> application configuration
```

A runtime `theme.activate` capability may eventually select among already-declared themes, but it
must not become the source of their content.

## 6. Authoritative keys and preview

The shortcut preview is trustworthy only if the same declaration produces the live binding. A
separately maintained help screen, generated documentation, or parser that scrapes part of the
Hyprland configuration will eventually disagree with the actual keys.

The registry should distinguish at least three origins:

| Origin | Meaning | Treatment |
| --- | --- | --- |
| `owned` | declared canonically by machine-state | generate binding and preview |
| `observed` | supplied by CachyOS, Noctalia or another vendor | display with provenance; do not rewrite |
| `conflicted` | more than one action claims the chord | report and refuse ambiguous generation |

This is the binding equivalent of CANONICAL, VENDOR and PROJECTED ownership. It preserves the
substrate's smallest-addressable-region rule while allowing the preview to describe the whole
desktop rather than only the portion machine-state owns.

An authoritative `SUPER + K` view should therefore answer:

- what the key does;
- who owns it;
- which semantic action it invokes;
- whether that action is currently available;
- where its declaration lives;
- whether another binding conflicts with it.

## 7. Application roles

Actions should depend on roles, not executable names:

```toml
[role]
browser  = "firefox"
mail     = "proton-mail"
terminal = "foot"
editor   = "codex"
```

The exact schema is open, but the principle matters. A binding opens the `mail` role. A workspace
layout waits for the application filling the `mail` role. A menu labels it consistently. A theme
adapter knows which configured terminal is active. Replacing an application then changes one
authoritative association instead of every workflow.

Roles also give stable semantics to the desktop provider. Window resolution can combine the role's
declared application identity with the provider's observed `class`, `initialClass`, PID and other
properties rather than distributing Proton Mail matching logic across agents and scripts.

## 8. How cohesion changes the resulting system

### It removes duplicated truth

Theme colors, key labels, executable choices and action names stop being copied independently into
Hyprland, Noctalia, documentation, agent instructions and application files. A change is made once,
projected deliberately and checked for drift.

### It makes human and agent interfaces agree

The person sees the same action name in the shortcut preview and Noctalia menu that the agent sees
in the JSON catalogue. Conversation becomes simpler because “open mail” names a shared operation,
not an interpretation that each interface implements separately.

### It makes the system inspectable

A future status view can answer questions that are otherwise expensive:

- Which applications follow the active theme, and which cannot?
- Which `SUPER` chords are unassigned, vendor-owned or conflicting?
- What action does this menu row invoke?
- Which application currently fills the `mail` role?
- Is the corresponding runtime capability available and authorized?

### It makes substitution real

The substrate already aims to make agent harnesses interchangeable. Semantic actions and
application roles extend that property to desktop applications and human interfaces. Changing the
agent, terminal or mail client should not require redesigning the workstation around the new
executable.

### It creates safer composition

A keybinding or menu entry no longer embeds an opaque shell command. It refers to a declared action
whose effects, consequence class and availability are known. The experience layer decides where an
action appears; the broker decides whether and how it may run. Neither can silently assume the
other's authority.

### It makes partial adoption useful

The theme registry can provide value before the broker exists. The key registry can generate a
truthful preview before events or unattended grants exist. Conversely, `bru` can prove its first
desktop provider without waiting for a polished Noctalia palette. The layers can mature
independently while converging on common identifiers.

## 9. Suggested shape of a future cohesion epic

This is sequencing guidance, not an implementation plan:

1. Define the semantic theme vocabulary and prove one narrow Noctalia/Hyprland projection.
2. Define keybinding and action references, including owned and observed provenance.
3. Generate one live Hyprland binding and the corresponding preview entry from one declaration.
4. Add collision detection and prove it can fail.
5. Define application roles and connect one role to desktop object resolution.
6. Render the same action catalogue into a Noctalia human surface.
7. Add cross-surface consistency tests and human/agent evaluations.

As with `bru`, each phase should produce something useful before the next begins. The first vertical
slice should be deliberately small: one theme token set, two targets, one binding, one preview and
one role are enough to establish whether the decomposition is sound.

## 10. Guidance back to the `bru` planner

Keep the epic's current scope discipline. In particular:

- Do not add theme generation to the broker.
- Do not make the broker own Hyprland or Noctalia configuration.
- Keep application roles and the action palette out until their sibling authority is defined.
- Preserve capability names as stable integration identifiers.
- Ensure the registry schema can be referenced externally without copying implementation details.
- Reserve distinct terminology for event bindings and key bindings.
- Do not assume every caller has the same authority merely because every caller names the same
  action.

The capability plan and the cohesion plan are complementary. `bru` makes actions discoverable,
bounded and accountable. Cohesion makes those actions legible and consistent everywhere the person
or an agent encounters them. Together they produce something neither layer can provide alone: a
workstation with one vocabulary, one visible truth and explicit authority at the point of action.
