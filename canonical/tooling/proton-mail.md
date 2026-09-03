# Proton Mail

## Function

Desktop mail client. Fulfils the `mail` role in `canonical/roles/roles.toml`, which is what
`SUPER + M` opens.

## Role

The first application this substrate learned to operate. `desktop.application.ensure role=mail`
resolves it by window class and either focuses the running window or launches it — so this record is
not bookkeeping: a role points at it, a key binding invokes that role, and the agent catalogue
exposes the same action.

## Ownership

`cachyos/proton-mail-bin 1.13.4-1`, installed 2026-09-01. The `-bin` suffix is the meaningful part:
this is Proton's own binary repackaged, where `proton-pass` on this machine is a distribution build
from source. Both are trusted through CachyOS and they are **not** the same provenance.

It carries `electron40` (285.29 MiB). `proton-pass` later brought `electron43`, so this machine runs
two Electron runtimes patching on independent schedules — recorded in `proton-pass.md` where the
second one arrived.

## Intent

**This record exists because its absence was the evidence for `machine-state-an1`.** Three packages
have been chosen on this machine since it was installed — `openai-codex`, `proton-mail-bin` and
`proton-pass` — and two of them had records. This one did not, for two days, while a key binding and
a declared role both depended on it. Nothing detected that, because until `an1` a record was a
description of something installed rather than a statement that it should be.

**Its mailbox is not ours.** Credentials and message content are out of scope, as for every
application here; the substrate knows the package exists, that its files are intact, and that the
`mail` role resolves to it.

## Verification

`pacman -Qkk` verifies every installed file for presence and integrity and launches nothing. The
same trap applies as for `proton-pass`: asking an Electron application for its version starts it.

```toml
group      = "Applications"
version    = "pacman -Q proton-mail-bin"
version_re = "([0-9][0-9.]*)"
check      = "pacman -Qkk proton-mail-bin"
ok         = "files intact"
fail       = "files altered or missing"
missing    = "not installed"
```
