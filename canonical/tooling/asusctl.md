# asusctl

## Function

Daemon (`asusd`) and CLI (`asusctl`) for ASUS ROG laptops, from the ASUS-Linux project: Aura
keyboard and chassis lighting, AniMe Matrix / AniMe Vision lid displays, platform profiles, fan
curves, battery charge limit and related firmware controls.

**On this machine it is needed for exactly one of those things: lighting.** Everything thermal is
already in the kernel and was measured there before this record was written (`machine-state-t0u.9`):
`platform_profile` offers `quiet balanced performance`, `power-profiles-daemon` selects them over
D-Bus with no root, hwmon `asus` reports `cpu_fan` / `gpu_fan` / `mid_fan`, and hwmon
`asus_custom_fan_curve` exposes `pwm1..pwm3` with eight `auto_point` temperature/PWM pairs each.
`asusd` writes those same eight points; it does not unlock them.

What the kernel does **not** expose is colour. `/sys/class/leds` carries one ASUS entry,
`asus::kbd_backlight`, with `max_brightness 3` and nothing else — no zones, no per-key, no light bar,
no AniMe. The hardware is enumerated as HID (`0b05:19b6` N-KEY Device, `0b05:193b` ITE 8295) and
driven from userspace, which is what this daemon is for.

**This record was drafted before the install**, which is the order `machine-state-t0u.4` used and the
order that found `machine-state-q4r`. Everything below marked *unverified* is a claim about a package
that is not yet on this machine, and must be checked against it rather than tidied up.

## Role

An application, and a **device owner**. That second part is what makes it different from the other
applications recorded here: `asusd` claims the lighting HID interfaces, so a second controller —
OpenRGB is the obvious candidate — must not run against the same hardware. Nothing in this
repository depends on it, and the thermal work explicitly does not.

## Ownership

`cachyos/asusctl 6.4.0-1`, packaged by `CachyOS <admin@cachyos.org>`, MPL-2.0, upstream
`https://asus-linux.org`. Signature enforced by the repository's `SigLevel = Required` — the same
trust root as `steam`, `proton-mail-bin` and `proton-pass`, and unlike `proton-drive`.

| | |
| --- | --- |
| Download | 7.10 MiB |
| Installed | 26.55 MiB |
| Built | 2026-08-16 |
| Depends | `glibc`, `libgcc`, `libusb`, `systemd`, `systemd-libs` |
| Optional | `acpi_call` (fan control), `asusctltray`, `rog-control-center` |
| Conflicts | `gnome-shell-extension-asusctl-gnome` |

`rog-control-center 6.4.0-1` is the optional GUI, same repository and version, and pulls a graphical
stack of its own (`libinput`, `libxkbcommon`, `mesa`, `seatd`, `fontconfig`, `freetype2`,
`libayatana-appindicator`, `hicolor-icon-theme`).

**Hardware this must match:** ROG Strix SCAR 18 `G835LXG`. Upstream added G835L-family support in
6.3.0 and corrected its supported lighting modes in 6.3.1, so 6.4.0 should cover it — *should*, and
only the daemon's own device probe settles which zones and modes it claims for this model.

## Intent

**Root, and a system daemon.** Unlike every other application recorded here, this one installs a
service that runs as root and holds a device. Installed 2026-09-06: the unit is `asusd.service`,
marked `static` — it is not enabled and does not need to be, because it is activated on demand and
was **already `active` immediately after installation**, with no manual start. `asus-shutdown.service`
also arrives, and is `disabled`.

**IT CHANGED THE MACHINE THE MOMENT IT STARTED, and that is the most important fact in this record.**
`asusd` keeps its own profile per power source and applied them at first start. The machine had been
`balanced` all session; seconds after the install it was `performance`:

| | before | after |
| --- | --- | --- |
| `platform_profile` | `balanced` | `performance` |
| `powerprofilesctl get` | `balanced` | `performance` |
| `gpu_fan` | 1600 rpm | 2100 rpm |
| CPU package | 38 °C | 41 °C |

Same idle load, 500 rpm louder, because a daemon restored a stored preference nobody on this machine
had ever set. Restored with `asusctl profile set Balanced`, and made durable with
`asusctl profile set -a Balanced` — the profile is now `Balanced` on AC and `Quiet` on battery.
**Installing a device daemon is a configuration change, not just an addition**, and this one arrived
with opinions.

**It must not fight the kernel it sits on.** `pwm1_enable`, `pwm2_enable` and `pwm3_enable` currently
read `2`, the firmware curve. Anything `asusd` writes replaces that; when the two disagree the last
writer wins and neither announces itself. One controller at a time, and the same rule applies with
more force to OpenRGB.

**Lighting is the reason it is here.** Fan curves stay expressible without it, which means a broken
or removed `asusd` must never take the thermal work with it.

**Uninstall:** `pacman -R asusctl` (plus `rog-control-center` if installed), then remove whatever
configuration it created outside the package — path unverified — and delete this record.

## Verification

**The draft was wrong, which is why it said so.** This record predicted `asusctl --version` would
print a version. There is no such flag: it answers `Unrecognized argument: --version` and — worth
noting for anything that checks exit codes — **exits 0 while doing it**. The version comes from
`asusctl info`, which also identifies the hardware:

```
asusctl v6.4.0
  Product family: ROG Strix SCAR 18
      Board name: G835LXG
```

So the daemon recognises this exact board rather than falling back to a generic profile. The check
block below still asks pacman rather than the CLI, because the package's integrity and the daemon's
health are different questions.

```toml
group      = "Applications"
version    = "pacman -Q asusctl"
version_re = "([0-9][0-9.]*)"
presence   = "pacman -Q asusctl"
check      = "pacman -Qkk asusctl"
ok         = "files intact"
fail       = "files altered or missing"
missing    = "not installed"
```

The `presence` / `check` split is the one `machine-state-q4r` established: `pacman -Q` answers
*installed*, `pacman -Qkk` answers *intact*, and one exit code cannot carry both. The altered-file
path for `pacman -Qkk` is proven — in a mount namespace, without root — under
`canonical/tooling/proton-pass.md`.

**A daemon check is deliberately not in that block yet.** Whether `ms status` should also assert that
`asusd` is running is a real question and a different one: a stopped daemon is a lighting outage, not
a missing package, and the two deserve different labels. Decided after the install shows what `asusd`
actually reports.
