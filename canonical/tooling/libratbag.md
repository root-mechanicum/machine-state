# libratbag

## Function

`ratbagd`, a D-Bus daemon that configures gaming mice — DPI, report rate, button mapping and LEDs —
with `ratbagctl` on the command line. `piper` is the optional GTK front-end to the same daemon.

**Here it exists for one device: the Logitech G203 LIGHTSYNC** (`046d:c092`), attached and, until
this record, unaddressable from this machine. Nothing else on this workstation speaks Logitech.

## Role

An application, and — like `asusctl` — a **device owner**. That is the whole reason this stack was
chosen over the obvious alternative.

**Why not OpenRGB, stated as a decision rather than an omission.** OpenRGB (`1.0rc3`, packaged and
signed) is the cross-vendor answer to "sync all the lighting", and it also drives ASUS laptop
lighting. `asusd` already owns `0b05:19b6` on this machine and persists its state to `/etc/asusd`.
Two controllers on one device means the last writer wins and neither says so — `machine-state-t0u.8`
ruled that out before the hardware was even probed, and the probe only strengthened it.

`libratbag` cannot reach the laptop's Aura at all. That limitation is the feature: **one controller
per device, and the boundary is structural rather than a convention someone has to remember.**

So "sync" here is not vendor sync. It is this repository setting two devices to the same colour with
two explicit calls — one `asusctl`, one `ratbagctl`. For `machine-state-bru.11` that is the better
shape anyway: a signal that means something needs a writer that knows it wrote.

## Ownership

`extra/libratbag 0.18-1`, packaged by `Robin Candau <antiz@archlinux.org>`, MIT, upstream
`https://github.com/libratbag/libratbag`. Signature enforced.

| | |
| --- | --- |
| Download | 2.65 MiB |
| Installed | 3.96 MiB |
| Built | 2024-09-24 |
| Depends | `glib2`, `libevdev`, `libudev.so`, `libunistring`, `json-glib`, `python`, `python-evdev`, `python-gobject` |
| Provides | `ratbagd`, `liblur` |
| Conflicts | `ratbagd`, `liblur` |

`piper 0.8-5` is the optional GTK front-end, `any` architecture, 285 KiB, pulling `gtk3`,
`python-lxml` and `python-cairo`.

**Note the build date: 2024-09-24.** This is the oldest package recorded here by a wide margin —
roughly two years — which matters for a stack whose entire job is knowing specific device models.
Whether it knows *this* device is the first question below, not an assumption.

## Intent

**Root daemon, `ratbagd`.** Unit name, activation route and whether it enables itself on install are
all **unverified** until it is on the machine. `asusctl` taught the lesson that makes this worth
writing down: installing a device daemon is a configuration change, and that one silently moved the
machine to a different power profile on first start.

**The device support question, which is the whole risk.** The G203 comes in two generations —
Prodigy (`046d:c084`) and LIGHTSYNC (`046d:c092`) — with different LED handling, and the attached
device is the **LIGHTSYNC**. Whether `libratbag 0.18` drives its zones is **unverified and not
assumed**. Three outcomes are possible and all are acceptable as findings: full LED control, DPI and
buttons but no usable LEDs, or the device not recognised at all.

**Nothing here depends on it**, and no colour set through it is load-bearing.

**Uninstall:** `pacman -R libratbag` (plus `piper`), remove any device profile it wrote outside the
package — path unverified — and delete this record.

## Verification

**Unverified: this block is a draft.** The `asusctl` record predicted a `--version` flag that does
not exist and *exits 0* while saying so, which is exactly the kind of check that looks healthy
forever. So this one asks pacman, and the CLI's own surface is settled after the install rather than
guessed at.

```toml
group      = "Applications"
version    = "pacman -Q libratbag"
version_re = "([0-9][0-9.]*)"
presence   = "pacman -Q libratbag"
check      = "pacman -Qkk libratbag"
ok         = "files intact"
fail       = "files altered or missing"
missing    = "not installed"
```

The `presence` / `check` split is `machine-state-q4r`'s: `pacman -Q` answers *installed*,
`pacman -Qkk` answers *intact*, and one exit code cannot carry both. The altered-file path is proven
without root, in a mount namespace, under `canonical/tooling/proton-pass.md`.

**A device probe is deliberately not the check.** `ratbagctl list` depends on a mouse being plugged
in; a check that fails when a peripheral is unplugged reports a fact about the desk, not about the
machine's state. If a liveness assertion is wanted later it belongs in its own label, the same open
question `canonical/tooling/asusctl.md` records for `asusd`.
