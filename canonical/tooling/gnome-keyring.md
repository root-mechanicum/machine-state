# gnome-keyring

## Function

The Secret Service on this machine: the D-Bus API `org.freedesktop.secrets` that applications ask for
a credential store, and the daemon behind it.

Installed 2026-09-06 to close a gap that had been measured the day before.

## Role

Substrate-adjacent. Nothing in this repository depends on it, but the machine's only native
credential store is not an application detail — without one, every tool that wants to keep a session
either prompts forever or writes a secret to disk in the clear.

## Ownership

`cachyos-extra-v3/gnome-keyring 1:50.0-1.1`, a signed repository package — deliberately the same
provenance class as every other record here. The credential store should not be the one thing on the
machine arriving over plain HTTPS, which is exactly what `proton-drive`, the tool that needed it, has
to be.

Three files carry the whole reason it was chosen over the alternatives:

| Path | What it does |
| --- | --- |
| `/usr/share/dbus-1/services/org.freedesktop.secrets.service` | D-Bus activation for the name this machine lacked |
| `/usr/lib/security/pam_gnome_keyring.so` | auto-unlock at login — a separate, still-untaken step |
| `/usr/lib/systemd/user/gnome-keyring-daemon.{service,socket}` | systemd units, **not** the path in use here |

## Intent

**Installed to close a measured gap, not to adopt GNOME.** Before this,
`busctl --user call org.freedesktop.secrets ... Ping` answered `The name is not activatable`, and so
did `secret-tool`. No file under `/usr/share/dbus-1/services/` declared the name.

`kwallet 6.29.0-1.1` was already installed and did not help. It ships `/usr/bin/ksecretd` under
`org.kde.secretservicecompat`, which claims the freedesktop name only once it is already running, and
nothing in a Hyprland session starts it. A package being present is not a service existing — which is
the same lesson `machine-state-q4r` taught about `pacman` verdicts, arriving here from the other
direction.

**Nothing is projected for it, and that is why it was chosen.** It is D-Bus activatable, so there is
no autostart entry, no session file and no environment variable. The alternative store,
`password-store`, would have needed `PROTON_DRIVE_CREDENTIALS_STORE=pass` set correctly in every
context the CLI runs in, agent sessions included; a context that missed it would have used a
different store without saying so.

**It is activated by D-Bus, not by systemd, and the distinction matters.** Verified 2026-09-06:
`gnome-keyring-daemon.socket` and `.service` are both `inactive` while the name answers, and the
process behind it is `/usr/bin/gnome-keyring-daemon --start --foreground --components=secrets` —
exactly the `Exec=` line in the D-Bus service file. Anyone reaching for `systemctl --user mask` to
disable this will change nothing and may conclude the check is broken. See Verification.

**What it holds, and what it must not.** The keyring is for credentials that can be **regenerated** —
the Proton Drive CLI session, under service `ch.proton.drive/drive-sdk-cli`, is the first and
currently the only one. An unlocked login keyring is readable by anything running as this user,
agents included (`machine-state-u40`: `HOME` is agent-readable, and root is the only real boundary
here). That is acceptable for a secret that `auth login` can mint again, and it is precisely why
irreplaceable secrets stay in Proton Pass, behind an unlock no cached agent holds. The split is the
security model, not a convention.

**Auto-unlock has not been done**, and is recorded rather than quietly skipped. Without it the keyring
prompts once per session. With it, `/etc/pam.d/greetd` gains two `optional` lines — `auth` after
`auth include system-local-login`, and `session ... auto_start` at the end. That file is owned by the
`greetd` package *and* has already been edited once by `noctalia`, which left
`/etc/pam.d/greetd.bak.noctalia.20260830145901` beside it. A future noctalia run can revert our lines,
and that failure is quiet: login keeps working and the keyring simply starts prompting again.
`machine-state-t0u.10.md` holds the drafted change.

## Verification

**The check asks whether the bus name ANSWERS, not whether a package is installed.** That distinction
is the entire point of this record. `pacman -Qkk gnome-keyring` would have reported green on this
machine yesterday — when `kwallet` was installed and the Secret Service still did not exist. A check
that cannot see the failure it was written for is the exact false green these records exist to stop.

```toml
group      = "Safety"
version    = "pacman -Q gnome-keyring"
version_re = "(?:[0-9]+:)?([0-9][0-9.]*)"
presence   = "pacman -Q gnome-keyring"
check      = "busctl --user call org.freedesktop.secrets /org/freedesktop/secrets org.freedesktop.DBus.Peer Ping"
ok         = "secret service answers"
fail       = "installed but not answering"
missing    = "not installed"
```

**`version_re` carries an epoch, and this is the first record here that needed to.** `pacman -Q`
prints `gnome-keyring 1:50.0-1.1`. The regex every other record uses, `([0-9][0-9.]*)`, matches the
epoch and reports this package's version as **`1`**. Caught before it landed by running the regex
against the real output rather than assuming its shape — the optional `(?:[0-9]+:)?` steps over the
epoch and captures `50.0`.

**`presence` and `check` are separate, and here they genuinely disagree in a useful way.**
`machine-state-q4r` added the distinction for package-query records: `pacman -Q` answers *is the
package there*, the `busctl` call answers *is the service alive*, and one exit code cannot carry
both. An uninstalled package reads `not installed` and fails the run; an installed package whose
daemon will not start reads `installed but not answering`, a different problem with a different fix.
This is the clearest case on the machine for having both.

**Falsifiability: proven on this machine, by the install itself.** The evidence is a before and after
with one variable, which is better than any synthetic control:

```
2026-09-05, before   busctl ... Ping  ->  Call failed: The name is not activatable   (fail)
2026-09-06, after    busctl ... Ping  ->  rc 0                                       (ok)
```

**A repeatable local control is NOT available, and the obvious one is wrong.**
`systemctl --user mask gnome-keyring-daemon.socket` does not disable this — activation is by D-Bus,
and both systemd units are already inactive while the service answers. A control built on it would
pass while changing nothing, which `SUBSTRATE.md` §5 names as the failure that manufactures
confidence; it has already happened twice in this repository. Two attempts at a hermetic control were
made and abandoned rather than written up as successes: a session bus started with `XDG_DATA_DIRS`
pointed away still resolved the service and then hung on `discover_other_daemon`, and a private
`dbus-daemon` with no service directories did not answer at all. Short of removing the package, the
failing path is not reproducible here, and that is recorded instead of being dressed up.

**This verdict is environment-dependent, like `hypr`'s.** It asks a running user session bus a
question, so it is a true statement only from inside one. A run without a session bus takes no
reading rather than reporting a failure, which `machine-state-c4v` already handles: what was not
observed keeps what the record last held and says so on its line.
