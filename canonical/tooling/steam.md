# Steam

## Function

Games client. The delivery mechanism for Valve's store, its Proton compatibility layer, and the
library of third-party software that comes with both.

Installed 2026-09-05, first launched and signed in by the user the same day. The record was written
first and these lines added after, which is the order `machine-state-t0u.4` planned and the order
that found `machine-state-q4r`.

## Role

An application, not substrate. Nothing in this repository depends on it and removing it costs
nothing here but this record. It is recorded for the reason every application is: an installed
application that nothing knows about is how an inventory stops being true.

It is, however, the **largest body of self-updating third-party code on this machine**, which the
Verification section takes seriously rather than waving at.

## Ownership

`multilib/steam 1.0.0.87-3`, packaged by `Levente Polyak <anthraxx@archlinux.org>`, upstream
`https://steampowered.com/`, licensed `LicenseRef-steam-subscriber-agreement`. Validated by SHA-256
sum and signature. `[multilib]` was already enabled in `/etc/pacman.conf` — it arrived with the
CachyOS install, not with this decision.

**Not `cachyos/steam-jupiter-stable 1.0.0.85-11`**, which is the Deck/Jupiter bootstrap packaging
aimed at a handheld session. This is a laptop with a desktop session. The two are easy to confuse
because both appear under `pacman -Ss steam` and the CachyOS one sorts first.

**The transaction was measured before it was run**, on 2026-09-05: `pacman -Sp --print-format` with
stdin closed resolves **26 packages** — 14 missing direct dependencies, 11 pulled transitively, and
`steam` itself — and asks nothing. Steam's own footprint is small (19.43 MiB download, 19.53 MiB
installed); the other 25 packages are the 32-bit stack it needs.

That stdin-closed check is not a flourish. This repository forbids commands that can block on a
prompt, and pacman's provider selection is exactly such a prompt. It does not appear here only
because `lib32-nvidia-utils` and `lib32-vulkan-intel` were already installed, so `lib32-vulkan-driver`
and `lib32-libgl` were already satisfied. On a machine without them, the same command would stop and
wait.

**One system-level side effect, named rather than discovered later.** The `steam-devices` dependency
installs udev rules under `/usr/lib/udev/rules.d` granting access to controller hardware. It is the
only part of this transaction that changes device permissions.

Confirmed after the install: exactly two files, `60-steam-input.rules` and `60-steam-vr.rules`. The
second is for VR hardware this machine does not have; it is inert rather than removable, since it
arrives with the package.

## Intent

**The graphics stack needed nothing.** Verified 2026-09-05 rather than inferred from package
presence: `nvidia-utils`, `lib32-nvidia-utils` and the loaded kernel module all report `610.57.04`,
and `linux-cachyos-nvidia-open 7.2.2-1` matches the running kernel. Four layers in agreement.

The discrete GPU is an RTX 5090 Max-Q with 24463 MiB of VRAM, driving no display (`nvidia-smi`
reports `Disp.A: Off`, idle at 28 W of a 150 W cap). That is render offload, so the GPU is selected
**per process** with `prime-run`, set as a per-game launch option. Nothing machine-wide, and nothing
for this repository to project.

**Storage is the default, decided rather than deferred.** `~/.local/share/Steam`, no separate
library, no separate shader cache. `/home` is a single 950 GiB filesystem with 938 GiB free; a
second library location would be a second thing to keep in step, for no benefit that exists today.
Revisit when there is a real capacity problem, not before.

**The account, the library and the Proton runtime are not ours.** This substrate knows the package
exists and that its packaged files are intact. It does not read, project, back up or record anything
under `~/.local/share/Steam` or `~/.steam` — credentials, library manifests, game content, or shader
caches. Secrets management is a recorded non-goal (`SUBSTRATE.md` §9) and this is the same boundary
`proton-pass` draws around its vault.

**Not managed for updates, and only half of it is managed at all.** The launcher is a repo package,
so `checkupdates` covers it and `ms changes` reports when its version moves. Everything Steam
downloads after that — its own runtime, Proton builds, games — updates on Valve's schedule through
Steam's own bootstrap, owned by no package and visible to no pacman query.

## Verification

`pacman -Qkk` verifies every installed file against the package database — presence and integrity —
and launches nothing. That is the deciding property: `steam` with any argument **starts the client**,
which opens a window and asks for account credentials. A check that logs a person in to prove a
package is installed is not a check.

```toml
group      = "Applications"
version    = "pacman -Q steam"
version_re = "([0-9][0-9.]*)"
check      = "pacman -Qkk steam"
ok         = "files intact"
fail       = "files altered or missing"
missing    = "not installed"
```

**What this check does not cover, stated plainly.** It verifies the 50 packaged files of the
19.53 MiB launcher. It says nothing about the tens or hundreds of gigabytes Steam will place under
`~/.local/share/Steam`, none of which any package owns. Reporting `files intact` for this record is
a true statement about a small fraction of what Steam is on this machine, and it should never be
read as more than that.

**Demonstrated within the hour, and this is the useful part of the record.** The first launch pulled
roughly 2 GiB of Steam's own runtime — `/home` went from 938 GiB free to 936 GiB. `ms changes`
reported *nothing changed*. `ms status` reported *files intact*. Both are correct: the content is
unpackaged, so no package database knows it exists, and the integrity check covers 50 files that did
not move. The substrate is not blind here by accident or by defect — it is blind by the boundary
this record draws, and the distance between "2 GiB arrived" and "nothing changed" is exactly the
size of that boundary. A green line for this record means the launcher is intact and nothing more.

**Falsifiability, and a gap this record found.**

Proven 2026-09-05: `pacman -Qkk steam` on an absent package exits 1.

**But exiting 1 routes to `fail`, not to `missing`** — `ms status` uses the `missing` label only when
the check command cannot be executed at all, and `pacman` executes perfectly well while reporting
that a package is not there. So for every package-based record on this machine, the `missing` label
is unreachable, an uninstalled package reads as `files altered or missing`, and `ms status` does not
count it absent or fail the run. `SUBSTRATE.md` §7.2 claims a tooling record is the declaration that
this machine should have the thing; that claim currently holds only for records whose command is the
tool's own binary. `machine-state-q4r` carries this. `canonical/tooling/proton-pass.md` states the
same observation and draws the opposite conclusion from it; it is wrong and is corrected there.

Not proven: the *altered file* path. Every file this package owns is root-owned under `/usr`, so
modifying one to watch the check fail needs a privilege this repository does not have. Trusted on
pacman's behaviour rather than a local demonstration, and recorded as such — the same weaker footing
`proton-pass` records, closable in ten seconds by anyone with a root shell.
