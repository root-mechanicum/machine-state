# Proton Mail Bridge

## Function

Proton's own local gateway to an end-to-end encrypted mailbox. It decrypts on this machine and
serves IMAP on `127.0.0.1:1143` and SMTP on `127.0.0.1:1025`. It is the only route by which `cap`
reads mail (`interests.mail`, through `fetch_mail` in `bin/cap`): read-only, loopback only, and
only the senders an interest declares.

## Ownership

`cachyos/protonmail-bridge` + `protonmail-bridge-core`, installed 2026-10-26 from the signed
repository package (machine-state-1ke.1). Signed in and synced 2026-10-30. Its encrypted local
store (`~/.local/share/protonmail/bridge-v3/gluon`, 6.7 GB at 2026-11-12) and its vault
(`~/.config/protonmail/bridge-v3/vault.enc`) are vendor-owned. The Bridge login itself lives in
the Secret Service (`keychain.json`: helper `secret-service`).

`cap` holds a separate credential, the Bridge-generated IMAP password, in the Secret Service as
`service=protonmail-bridge username=<bridge username>`. It is stored by the human and read only
for the length of one login.

## Intent

**Bridge runs headless at login**, through the package's own user unit
`protonmail-bridge.service` (`protonmail-bridge-core --noninteractive`, `WantedBy=default.target`).
machine-state does not render its own unit. Enabling the vendor's is the whole intent:

```sh
systemctl --user enable --now protonmail-bridge
```

The GUI (`protonmail-bridge`) is for sign-in and settings only, and cannot run alongside the
service. Stop the service before opening it, and keep its **Open on startup** setting off: it
is on by default, and writes `~/.config/autostart/Proton Mail Bridge.desktop`, which starts a
second Bridge at every login that finds the service running and exits with an error (seen and
removed 2026-11-13).

Until 2026-11-12 nothing started Bridge, so after the first restart it was simply off and the
mailbox it had synced was unreachable. The decision to use Bridge over direct-API clients, and
the code review behind it, are in machine-state-yr5.

**Its mailbox is not ours.** Agents draft, never send (memory `mail-draft-never-send`). `cap`
never opens the SMTP port.

## Verification

Asking the GUI launcher for `--help` **starts Bridge** (it spawns the GUI to answer), the same
trap as the Electron apps. Check the package and the listener, never the binary.

```toml
group      = "Services"
version    = "pacman -Q protonmail-bridge-core"
version_re = "([0-9][0-9.]*)"
presence   = "pacman -Q protonmail-bridge-core"
check      = "systemctl --user is-active protonmail-bridge"
ok         = "running"
fail       = "not running: nothing can read mail"
missing    = "not installed"
```
