# Proton Pass

## Function

Credential manager. Installed 2026-09-03 as the first half of `machine-state-t0u.1`, and as the
first application installed through the substrate's own loop rather than by hand.

**There is an official CLI, and this record's framing implied there was not.** `pass-cli`
(`github.com/protonpass/pass-cli`, docs `protonpass.github.io/pass-cli`) lists and reads vaults and
items, injects secrets into environment variables or template files through a
`pass://vault/item/field` URI, and integrates SSH keys — on the paid tiers. It is **not installed
here**, not in any configured repository, and distributed as a Proton-published binary or a
`curl | bash` script. `machine-state-t0u.16` evaluates it.

The claim it corrects was built from this machine's *desktop app* — no daemon, no D-Bus name, no
command surface — which was accurate about the app and was never evidence about the product. Worth
remembering the shape of that error: absence in one client is not absence in the vendor's offering.

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
presence   = "pacman -Q proton-pass"
check      = "pacman -Qkk proton-pass"
ok         = "files intact"
fail       = "files altered or missing"
missing    = "not installed"
```

**Falsifiability, stated exactly rather than assumed.** Both halves are proven now; one of them was
recorded as unproven for three days first, and the way it was eventually closed is the useful part.

Proven 2026-09-03: `pacman -Qkk` on an absent package exits 1.

**The conclusion drawn from that here was wrong, and is corrected 2026-09-05.** This said "so the
`missing` path can fail". It could not. `ms status` reached the `missing` label only when the check
command could not be *executed*, and `pacman` executes perfectly well while reporting that a package
is not installed — so exit 1 routed to `fail`, and an uninstalled package would have read `files
altered or missing` and would not have failed the run at all. The observation was right and the
inference was not. `canonical/tooling/steam.md` found it, by being written before its install.

**What makes the `missing` path reachable is the `presence` line above**, added by
`machine-state-q4r`. `pacman -Q proton-pass` asks whether the package is installed and
`pacman -Qkk proton-pass` asks whether its files are intact — two questions that one exit code
cannot separate, so the record states which command answers which instead of leaving `ms` to guess.
The probe failing means absent and fails the run; the check failing means altered.

**Proven 2026-09-06, and it needed no root after all.** This record previously said the *altered
file* path was untestable here — every file the package owns is root-owned under `/usr` — and that
only a root shell could close it. That was wrong about the means, not about the difficulty: the
repository's own throwaway rule closes it, applied to a **mount namespace** instead of a directory.
`unshare -r -m` gives a private mount table, and an altered copy of a packaged file can be
bind-mounted over the original inside it. Nothing under `/usr` is written. Verified after every run:
`27 total files, 0 altered files`, exit `0`, and the file's md5 unchanged (`machine-state-03m`).

Inside the namespace, with an altered copy bind-mounted over
`/usr/share/applications/proton-pass.desktop`:

```
warning: proton-pass: /usr/share/applications/proton-pass.desktop (Modification time mismatch)
warning: proton-pass: /usr/share/applications/proton-pass.desktop (Size mismatch)
warning: proton-pass: /usr/share/applications/proton-pass.desktop (SHA256 checksum mismatch)
```

With a byte-identical copy bind-mounted at the same path instead — `cp -p`, so the mtime survives —
pacman reports **no warning for that file at all**. Same namespace, same path, only the bytes differ.
That pair is the proof; either run alone would not be.

**The summary line lies inside a namespace, and the warning kinds are what discriminate.**
`unshare -r` maps this user to uid 0, so every file owned by real root appears as `nobody`: pacman
reports `UID mismatch` and `GID mismatch` for all of them and ends with `27 altered files` in the
CONTROL run too. The count is worthless here. A user-owned copy appears as `root:root` inside the
namespace, which is exactly why the bind-mounted pristine file is the one that reports clean.

Exit code `1` from both runs inside the namespace: a mismatch of any kind is enough, so the `fail`
label is reachable for an altered file. That is what this record needed and could not previously
show, and it closes the same gap for every record built on `pacman -Qkk` — `steam`, `proton-mail`,
`gnome-keyring`.
