# Proton Pass

## Function

Credential manager. Installed 2026-09-03 as the first half of `machine-state-t0u.1`, and as the
first application installed through the substrate's own loop rather than by hand.

## Role

An application, not substrate. Nothing here depends on it, and removing it costs this repository
nothing but this record. It is recorded because an installed application that nothing knows about is
how an inventory stops being true.

## Ownership

`cachyos/proton-pass 1.39.1-1`, packaged by `CachyOS <admin@cachyos.org>`, GPL-3.0-or-later,
upstream `https://proton.me/pass`. The `cachyos` repository is configured `SigLevel = Required`, so
the signature is enforced — the same trust root as every other package here.

Note it is a **distribution build**, not Proton's own binary. `proton-mail-bin` on this machine is
the other pattern: a repackaged upstream binary. Both are trusted through CachyOS; they are not the
same provenance and should not be described as if they were.

**It brought a second Electron.** `electron43` (332.78 MiB) arrived with it, alongside the
`electron40` (285.29 MiB) that `proton-mail-bin` already required. Roughly 618 MiB of Electron on
this machine, in two runtimes that patch on independent schedules. Not a problem — 939 GiB free —
but it is the kind of fact that is invisible from the package's own 25.90 MiB and worth having
written down before someone wonders where the disk went.

## Intent

**Its vault is not ours.** Proton Pass stores credentials, and secrets management is a recorded
non-goal for this repository (`SUBSTRATE.md` §9). This substrate knows that the package exists and
that its files are intact. It does not project, back up, read or record anything the application
stores, and nothing here should grow to.

**Not managed for updates.** It is a repo package, so `checkupdates` covers it like any other; there
is no separate update path to maintain. `ms changes` reports when its version moves.

## Verification

`pacman -Qkk` verifies every installed file against the package database — presence and integrity —
and launches nothing. That last part is not incidental: `proton-pass --version` **starts the
application**, prints Electron's autoupdater notice, and exits 0 regardless. A check that launches a
GUI to prove a package is installed is worse than no check, and one that exits 0 whatever happens
proves nothing at all.

```toml
group      = "Applications"
version    = "pacman -Q proton-pass"
version_re = "([0-9][0-9.]*)"
check      = "pacman -Qkk proton-pass"
ok         = "files intact"
fail       = "files altered or missing"
missing    = "not installed"
```

**Falsifiability, stated exactly rather than assumed.** Half of it is proven and half is not, and
the difference matters more than a tidy claim would.

Proven 2026-09-03: `pacman -Qkk` on an absent package exits 1.

**The conclusion drawn from that here was wrong, and is corrected 2026-09-05.** This said "so the
`missing` path can fail". It cannot. `ms status` reaches the `missing` label only when the check
command cannot be *executed*, and `pacman` executes perfectly well while reporting that a package is
not installed — so exit 1 routes to `fail`, and an uninstalled package would read `files altered or
missing` and would not fail the run at all. The observation was right and the inference was not.
`machine-state-q4r` carries the fix; `canonical/tooling/steam.md` found it.

Not proven: the *altered file* path. Every file this package owns lives under `/usr` and is
root-owned, so modifying one to watch the check fail needs a privilege this repository does not
have. The check is trusted here on pacman's behaviour rather than on a local demonstration — which
is a weaker footing than `SUBSTRATE.md` §5 asks for, and is recorded as such instead of being
written up as though it had been tested. Anyone with a root shell can close this in ten seconds by
appending a byte to a file in `/usr/lib/proton-pass` and re-running the check.
