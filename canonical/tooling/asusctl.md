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

## Lighting, as the machine reports it

Probed 2026-09-06 against the running daemon, with every visible change confirmed by eye and the
whole state restored afterwards (`machine-state-t0u.8`).

**`asusd` claims six interfaces on this board** — `Anime`, `Aura`, `AsusArmoury`, `Backlight`,
`FanCurves`, `Platform` — and *not* `Slash`, the Zephyrus ledbar, which it reports as absent rather
than pretending. `Platform` carries `ChargeControlEndThreshold` and `ThrottlePolicy`.

**One Aura device, not two.** `/xyz/ljones/aura/19b6_2_4` is the N-KEY HID (`0b05:19b6`). The other
ASUS HID on this machine, `0b05:193b` (ITE 8295), is **not claimed by asusd at all**.

**Through named effects, the model is one colour, many surfaces, independent power** — which is not
what the property names suggest and had to be established by testing. *That qualifier matters: it is
a limit of the named-effect path, not of the hardware. See the correction below.*

- `SupportedBasicModes` lists twelve effects; `SupportedBasicZones` is `0`. So a named effect paints
  the whole keyboard at once.
- Zone-specific effects are **refused**, demonstrated rather than assumed:
  `NotSupported: AuraEffect { mode: Static, zone: Logo, … }` and the same for `BarLeft`.
- `SupportedPowerZones` is `1, 2, 0`, each with `boot` / `awake` / `sleep` / `shutdown` flags.
  Powering zone 2 off **darkened the front edge while the keyboard stayed lit**, and powering it back
  on restored it. Confirmed by eye.

So *through named effects* surfaces share a colour and differ only in whether they are lit.

**Correction, 2026-10-22: the surfaces do not share a colour in hardware.** The earlier conclusion
generalised from `asusd`'s effect API to the device, and the user, who had seen far richer lighting
than that model allows, challenged it. `asusd`'s own data contradicts it:

- `/usr/share/asusd/aura_support.ron` lists `G835L` with `advanced_type: PerKey` and
  `layout_name: "g814ji-per-key"`. `basic_zones: []` only means that *named effects* have no zones.
- `/usr/share/rog-gui/layouts/g814ji-per-key_US.ron` (from `rog-control-center`) addresses the rim as
  **six separate LEDs**: `LightbarLeft`, `LightbarLeftCorner`, `LightbarLeftBottom`,
  `LightbarRightBottom`, `LightbarRightCorner`, `LightbarRight`. **No logo LED** appears in that layout.
- The Aura interface exposes `DirectAddressingRaw (aay)`, which sends raw per-LED frames.

So per-LED colour, including a rim coloured differently from the keys, is a hardware capability that
is reached through direct addressing, not through `asusctl aura effect`. Global brightness
(`Brightness`, 0–3) is still a single value, but a rim LED given a darker colour *is* a dimmer rim.

**The frame format, read from upstream source** (`rog-aura/src/keyboard/advanced.rs` on asusctl's
GitLab `main`, 2026-06-02; there is no `6.4.0` tag there, because the project moved to
`github.com/opengamingcollective/asusctl`). Each HID packet is 64 bytes:

```
5d bc 00 01 01 01 <start LED> <count> 00 | r g b × count
```

There are 16 LEDs per packet, and `<start LED>` is the group number × 16. In upstream's per-key map,
LED **176 is `LidLogo`**, **178–183 are the rim** (`LightbarRight`, `…RightCorner`, `…RightBottom`,
`…LeftBottom`, `…LeftCorner`, `LightbarLeft`), and 185/186 are `LidLeft`/`LidRight`. They sit in a
twelfth packet (start `0xb0`), which upstream's own `new_per_key()` never allocates (it builds 11),
so its per-key path cannot actually reach the rim. On the first packet `asusd` sends an init message
(`5d bc` and zeros) that clears the board, so **per-key mode owns every LED**, and dimming one surface
means sending the whole board.

**Driven once, 2026-10-22.** The frame sent was 12 packets, all with count `0x10`, every LED
`#002040` except 178–183 at `#000810`. It went through `busctl call … DirectAddressingRaw aay`, and
`asusd` accepted it. The user reported the keyboard unchanged and the rim effectively **gone**: a
quarter of `#002040` is below what the eye registers on that diffuser. Because the init clears every
LED, a dark rim does *not* prove that 178–183 are the right indices; an unaddressed rim would also go
dark. A brighter rim colour, such as `#001020`, would settle it. Logo at 176 was not separately checked.

**Not persistent.** `asusd` does not save per-key frames, and on resume it reloads the stored
`Static` effect. So the dim rim lasts until the next sleep or reboot unless something resends it.
`machine-state-bru.11` is the larger reason to drive this properly.

**The second ASUS HID, `0b05:193b` (ITE 8295), is still unexplained.** `asusd` does not claim it, and
nothing here shows whether it drives any lighting.

**AniMe Vision is a genuinely separate device**, `/xyz/ljones/aura/anime`, with its own `Write`
method and power rules: `OffWhenLidClosed`, `OffWhenSuspended`, `OffWhenUnplugged`, all `true`. Found
already running — `EnableDisplay true`, brightness `2`, `BuiltinsEnabled true`, cycling
`GlitchConstruction`, `BinaryBannerScroll`, `BannerSwipe`, `GlitchOut` — since the install, without
anyone asking for it.

**One flag, two properties, and it will bite a script.** `asusctl anime --brightness off` sets
`Brightness 0` *and* flips `EnableDisplay` to `false`. Coming back needs both: `--enable-display true`
then `--brightness med`. Dimming to nothing and switching off are the same command at the bottom of
the range.

**Turning every surface off:** `asusctl leds set off` for the keyboard and everything sharing its
colour, `asusctl aura power <zone>` with no flags for a single surface, and
`asusctl anime --brightness off` for the lid. Each was demonstrated independently.

**ORDER MATTERS WHEN RESTORING, and getting it wrong is visible.** The restore here re-enabled the
light bar's power zone, set the colour back to its original red while brightness was still `1`, and
only then set brightness to off — producing a **short red burst on the edge**, spotted by the user. A
sequence meant to leave no trace emitted a signal instead.

Set brightness to zero **first**, then colour, then power zones. This is not cosmetic for
`machine-state-bru.11`: a channel that flashes during its own cleanup is indistinguishable, to the
person reading it, from a channel that means something.

**Configuration lives in `/etc/asusd/`**, root-owned: `asusd.ron`, `aura_19b6.ron`, `anime.ron`,
`fan_curves.ron`. Per-device files, so removing a device's config does not disturb the others.

## Current settings

Chosen by the user on 2026-10-22. `asusd` persists each of these to `/etc/asusd/` as it is set; the
files were read back after every change. Not yet confirmed across a reboot.

| Surface | Setting | Why |
| --- | --- | --- |
| Colour / effect | `Static`, `#002040` (deep blue) | the user likes it; left as found |
| Keyboard power | on at boot, awake, sleep, shutdown | unchanged — with the lid closed it cannot be seen, so its sleep state was left alone |
| Lightbar (rim) power | **awake only** | the rim was wanted subtler, and power state is the only rim-specific setting `asusctl`'s CLI offers |
| Lightbar (rim) colour | `#000810` through a per-key frame, so effectively dark. **Lost on sleep or reboot**, when it returns to `#002040` | the rim was wanted subtler. The user accepted "gone" for now; making it stick is open work |
| Logo power | **awake only** | it pulsed **red** during sleep (see below) |
| AniMe display | **off** (`display_enabled false`, `display_brightness Off`) | not wanted for now |
| AniMe builtins | **off** (`builtin_anims_enabled false`) | the firmware plays its own boot/shutdown animations outside `asusd`'s control; disabling the display alone would not stop them |

Set with `asusctl anime --brightness off`, `asusctl anime --enable-powersave-anim false`,
`asusctl aura power lightbar --awake`, `asusctl aura power logo --awake`. For `aura power`, the flags
given are the states that are **on**; any state left out is off.

**The sleep effect is the firmware's, not ours.** With the logo powered during sleep it pulsed red
while the configured colour was static blue — the same red as the builtins' default `colour1`
(`166,0,0`). Whatever is set for awake does not carry into sleep, so a surface powered during sleep
should be assumed to show the firmware's choice, not the user's.

**Saved and live brightness disagree.** `aura_19b6.ron` says `brightness: Low`; `asusctl leds get`
says `High`. Something — the keyboard's brightness keys are the likely candidate — raised it at
runtime without the file following. Unresolved: which one wins at boot.

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
