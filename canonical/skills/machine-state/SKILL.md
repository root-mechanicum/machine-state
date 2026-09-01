---
name: machine-state
description: Use when operating this workstation — changing its configuration, controlling the compositor or desktop shell at runtime, checking whether a projected file has drifted, inspecting substrate tooling, or deciding where a change belongs and whether you may make it unasked. Trigger on ms project, ms diff, ms status, hyprctl, noctalia msg, canonical/, adapters/, questions about which file is the source of truth, or any request to change how this machine looks or behaves.
---

# machine-state

Configuration and agent policy for this workstation live in the `machine-state` repository. It is
canonical; the files agents read elsewhere are one-way projections of it.

This skill answers two questions: **where a change belongs**, and **what you can actually do here**.

## Deciding where a change belongs

Ask who owns the file before editing it.

| Owner | Examples | Rule |
| --- | --- | --- |
| canonical | `canonical/**`, `SUBSTRATE.md` | edit freely, then `ms project` |
| projected | any spliced region, linked skill dirs | never edit; edit canonical instead |
| vendor | files an installer owns, e.g. anything `bd setup` writes | leave to that tool |

Editing a projection is not wrong so much as futile: `ms diff` reports it and `ms project`
overwrites it.

## Control surfaces

This machine carries roughly three hundred commands of control surface. They are all
self-describing — `<tool> --help` is authoritative and current; this table is a map, not a manual.

| Surface | Controls | Size | Start with |
| --- | --- | --- | --- |
| `ms` | canonical → projection | 4 | `ms status` |
| `hyprctl` | Hyprland at runtime | 56 | `monitors`, `clients`, `workspaces`, `getoption`, `dispatch`, `keyword` |
| `noctalia msg` | the desktop shell at runtime | 112 | `--help`; see domains below |
| `bd` | work tracking and durable memory | 114 | `bd prime` — the `beads` skill covers this, do not relearn it here |
| `dcg` | the command guard | 25 | `dcg test`, `dcg explain`, `dcg doctor` |
| `pacman` | packages | — | `pacman -Q`, `-Qo`, `-Ss` |
| `systemctl --user` | session services | — | `status`, `list-units` |

`noctalia msg` spans 37 domains — most of the desktop's behaviour, and more than half of its
commands change something:

```
bar bluetooth brightness caffeine clipboard color config desktop dock dpms
effects greeter keyboard lockscreen log media mic network nightlight
notification osd panel plugin plugins power screenshot session settings
status taskbar templates theme volume wallpaper wifi window workspace
```

Read-only forms are the exception, not the rule — there are only eight, and they are not a
consistent suffix: `bluetooth-status`, `wifi-status`, `notification-dnd-status`,
`workspace-alert-status`, `log-level-status`, `color-scheme-get`, `theme-mode-get`,
`wallpaper-get`. Everything else acts. Check `--help` before assuming a command merely reports.

## Two speeds, and why it matters

Almost every desktop change can be made two ways, and they are not interchangeable.

| | Fast | Durable |
| --- | --- | --- |
| Hyprland | `hyprctl keyword …` | edit `canonical/desktop/hypr/machine-state.lua`, `ms project` |
| Desktop shell | `noctalia msg …` | *(not yet managed — see `canonical/tooling/noctalia.md`)* |

**A runtime change is lost on the next reload, and `ms diff` will never know it happened.** Use the
fast path to try something and show the result; use the durable path to keep it. Leaving a change
only at runtime is how a machine drifts from its own description.

## What you may do unasked

The repository governs *state* — who owns which file. This governs *action*, and it is
deliberately conservative while the fuller model is still being worked out.

**Free.** Anything read-only: `ms status`, `ms diff`, `hyprctl monitors|clients|workspaces|getoption`,
`bd list|show|ready`, `dcg test|explain|doctor`, `pacman -Q*`, `systemctl --user status`, and the
eight `noctalia msg` query commands named above. These answer questions without changing anything.

**Ask first.** Anything the person will *see or feel*: moving windows or workspaces
(`hyprctl dispatch`), changing volume, brightness, bars, wallpaper, theme, or lock screen
(`noctalia msg …`), and `ms project` when it will alter something outside the repository. Being
technically reversible is not the same as being welcome.

**Never without an explicit request.** Installing or removing packages; `sudo` anything; weakening
the command guard (`dcg allow`, `dcg uninstall`, disabling a pack); `git push`; power or session
commands. Note the asymmetry: a `dcg` refusal is answered by narrowing the command, never by
removing the rule that refused it.

When unsure, prefer the read-only form first — every surface above has one, and knowing the current
state usually changes what you were about to do.

## Extending

Adding an agent is adding `adapters/<name>.toml`. Adding managed config is adding a directory under
`canonical/`. Adding a tool is adding `canonical/tooling/<tool>.md`. None of these should require
changing `bin/ms`. See `SUBSTRATE.md` for the full contract.
