# Secrets on this machine — what landed, and what needs your root

**Status, 2026-09-06.** Sections 2 and 4 are **done**. `gnome-keyring 1:50.0-1.1` is installed, the
Secret Service answers, and both tooling records are at their canonical paths;
`machine-state-t0u.10` and `machine-state-t0u.1` are closed.

**Section 3 — the PAM change — is still a proposal and has not been applied.** `/etc/pam.d/greetd` is
untouched. It is optional: without it the keyring prompts once per session.

Two corrections this document earned by being checked against the machine rather than trusted. The
falsifiability control proposed in §2 — masking the systemd socket unit — **does not work**:
activation is by D-Bus and both systemd units are inactive while the service answers, so that control
would have passed while disabling nothing. And the `version_re` in the drafted record would have
reported the pacman **epoch** (`1`) as the version instead of `50.0`. Both are fixed in
`canonical/tooling/gnome-keyring.md`, which supersedes §2 below.

---

## 1. What is actually missing

Measured 2026-09-05, not assumed:

```
$ busctl --user call org.freedesktop.secrets /org/freedesktop/secrets \
        org.freedesktop.DBus.Peer Ping
Call failed: The name is not activatable

$ secret-tool search --all service ch.proton.drive
secret-tool: The name is not activatable
```

No file under `/usr/share/dbus-1/services/` declares `org.freedesktop.secrets`. `kwallet 6.29.0-1.1`
ships `/usr/bin/ksecretd` under `org.kde.secretservicecompat`, which claims the freedesktop name only
once it is already running — and nothing here starts it. This is a Hyprland session; it launches no
keyring agent, and `kwalletd6` is installed but not running.

So this machine has **no Secret Service**, and the Proton Drive CLI's default credential store cannot
work. That is how the gap was found, and it is the only thing currently asking for one.

### Why `gnome-keyring` and not the alternatives

Verified from the Arch file list rather than from memory — the package ships exactly the three things
that matter:

```
usr/share/dbus-1/services/org.freedesktop.secrets.service   <- D-Bus ACTIVATION for the missing name
usr/lib/security/pam_gnome_keyring.so                       <- the auto-unlock module
usr/lib/systemd/user/gnome-keyring-daemon.{service,socket}  <- socket-activated, no autostart line
```

The first line is the whole argument: **installing the package alone closes the measured gap.** No
session file, no autostart entry, no environment variable, nothing projected into `~`.

- **Not `kwallet`.** Already installed, and the Secret Service still does not exist — because nothing
  activates `ksecretd` under the freedesktop name. Adopting it means owning a session service *and*
  an unlock dialog outside a KDE session. Its only merit is zero new packages, and it does not
  deliver the thing that is missing.
- **Not `password-store`.** A fine store, and the wrong one for this secret. It would need
  `PROTON_DRIVE_CREDENTIALS_STORE=pass` set in every context the CLI runs in, agent sessions
  included; a context that misses it gets a *different store*, silently. It also needs a GPG key,
  which is a new irreplaceable thing to own and back up.
- **Not Proton Pass.** It cannot serve here and it is not a near miss. `PROTON_DRIVE_CREDENTIALS_STORE=pass`
  means passwordstore.org, not Proton Pass — an unfortunate name collision. Checked on this machine:
  `~/.config/Proton Pass/Local State` holds only `uninstall_metrics`, with no `os_crypt` section; its
  log never mentions a keyring backend; state is Chromium DOMStorage flushed to disk. It is an
  Electron app with no daemon, no D-Bus service and no CLI. It neither provides machine credentials
  nor consumes them.

**The deciding property is that the Drive session is re-derivable.** Lose it and `auth login`
regenerates it. A durable, portable, backed-up store is for secrets that cannot be regenerated; this
is not one, and matching the store to the secret is the whole decision.

### The boundary, stated before it is crossed

An unlocked login keyring is readable by **anything running as this user, including any agent** —
`secret-tool search` would return the Drive session. That is `machine-state-u40`'s boundary again:
`HOME` is agent-readable, and root is the only real boundary on this machine.

Acceptable for a credential that can be regenerated. It is also the reason this keyring must not
become the place where irreplaceable secrets accumulate. Those stay in Proton Pass, behind an unlock
no cached agent holds:

```
login password  --PAM-->  gnome-keyring login keyring  -->  Drive CLI session   (re-derivable)
Proton Pass     <--account password, memorized
                -->  login password, account password, recovery codes          (irreplaceable)
```

Nothing needs Proton Drive to recover anything, so there is no cycle.

---

## 2. Draft — `canonical/tooling/gnome-keyring.md`

> Not yet written to that path. `ms status` would fail the moment it is, correctly, because the
> package is not installed. It moves there as part of the install, not before.

````markdown
# gnome-keyring

## Function

The Secret Service on this machine: the D-Bus API (`org.freedesktop.secrets`) that applications ask
for a credential store, and the daemon behind it.

## Role

Substrate-adjacent. Nothing in this repository depends on it, but the machine's only native
credential store is not an application detail — without it, every tool that wants to keep a session
either prompts forever or writes a secret to disk in the clear.

## Ownership

`cachyos-extra-v3/gnome-keyring 1:50.0-1.1`, a signed repository package — the same provenance class
as every other record here, and deliberately so: the credential store should not be the one thing on
the machine arriving over plain HTTPS.

Three files carry the whole reason it was chosen:

| Path | What it does |
| --- | --- |
| `/usr/share/dbus-1/services/org.freedesktop.secrets.service` | D-Bus activation for the name this machine lacked |
| `/usr/lib/security/pam_gnome_keyring.so` | auto-unlock at login (separate, optional step) |
| `/usr/lib/systemd/user/gnome-keyring-daemon.{service,socket}` | socket-activated; no session autostart line |

## Intent

**Installed to close a measured gap, not to adopt GNOME.** Before this,
`busctl --user call org.freedesktop.secrets ... Ping` answered `The name is not activatable`, and so
did `secret-tool`. `kwallet` was already installed and did not help: it claims the freedesktop name
only once `ksecretd` is running, and nothing in a Hyprland session starts it.

**Nothing is projected for it.** It is D-Bus activatable and socket-activated, so no autostart entry,
no session file, no environment variable. That is the property that made it the right choice — the
alternative store needed a variable set correctly in every context including agent sessions, and a
context that missed it would have used a different store without saying so.

**What it holds, and what it must not.** The keyring is for credentials that can be REGENERATED — the
Proton Drive CLI session is the first and currently the only one. An unlocked login keyring is
readable by anything running as this user, agents included; see `machine-state-u40`. Irreplaceable
secrets stay in Proton Pass, behind an unlock no cached agent holds. That split is the security
model, not a convention.

**Auto-unlock is a separate decision** and is recorded in `machine-state-t0u.10` whether or not it is
taken. Without it the keyring prompts once per session. With it, `/etc/pam.d/greetd` gains two
`optional` lines — in a file `noctalia` has already edited once.

## Verification

**The check asks whether the bus name ANSWERS, not whether a package is installed**, and that
distinction is the point. `pacman -Qkk gnome-keyring` would have reported green on this machine
yesterday, when `kwallet` was installed and the Secret Service still did not exist. A check that
cannot see the failure it was written for is the exact false green these records exist to prevent.

```toml
group      = "Safety"
version    = "pacman -Q gnome-keyring"
version_re = "([0-9][0-9.]*)"
presence   = "pacman -Q gnome-keyring"
check      = "busctl --user call org.freedesktop.secrets /org/freedesktop/secrets org.freedesktop.DBus.Peer Ping"
ok         = "secret service answers"
fail       = "installed but not answering"
missing    = "not installed"
```

`presence` and `check` are separate here for the reason `machine-state-q4r` established: `pacman -Q`
answers *is the package there*, the `busctl` call answers *is the service alive*, and one exit code
cannot carry both. This is the first record where the two genuinely disagree in a useful way — an
uninstalled package reads `not installed` and fails the run, while an installed package whose daemon
cannot start reads `installed but not answering`, which is a different problem with a different fix.

**Falsifiability.** The failing path is reachable without root and without breaking anything:
`systemctl --user mask gnome-keyring-daemon.socket` and re-run — the call fails and the record reads
`installed but not answering`. Unmask to restore. Proven at install time; until then this record is a
draft.

**This verdict is environment-dependent, like `hypr`'s.** It asks a running user session a question,
so it is a true statement only from inside one. A run without a session bus reports the check
unobserved rather than failed, which `machine-state-c4v` already handles.
````

---

## 3. Draft — the PAM change

**This is the risky half, it is optional, and it should be applied separately from the package.**

Without it, everything works; the keyring simply prompts once per session for its password. With it,
the login password unlocks the keyring at login and nothing prompts — which matters here, because
this repository forbids commands that can block on a prompt, and a status check that stalls is worse
than no check.

### The login path, established rather than guessed

```
greetd 0.10.3-2.1  ->  /usr/bin/noctalia-greeter-session  (noctalia-greeter 1.2.1-1)
PAM stack: /etc/pam.d/greetd  ->  includes system-local-login
```

A password *is* typed at the greeter, so PAM auth runs and auto-unlock is possible in principle.

### Current file, verbatim

```
#%PAM-1.0

auth       required     pam_securetty.so
auth       requisite    pam_nologin.so
auth       include      system-local-login
account    include      system-local-login
session    include      system-local-login
session    required     pam_systemd.so
```

### Proposed file

```
#%PAM-1.0

auth       required     pam_securetty.so
auth       requisite    pam_nologin.so
auth       include      system-local-login
auth       optional     pam_gnome_keyring.so
account    include      system-local-login
session    include      system-local-login
session    required     pam_systemd.so
session    optional     pam_gnome_keyring.so auto_start
```

Two lines. Both `optional`, so a failure in either can never block a login. The `auth` line must sit
**after** `auth include system-local-login` — that is where the password becomes available for it to
capture; placed before, it captures nothing and silently does nothing.

### Three things wrong with this file that are not our doing

1. **`noctalia` has already edited it.** It added `session required pam_systemd.so` on 2026-08-30 and
   left `/etc/pam.d/greetd.bak.noctalia.20260830145901` beside it. A future noctalia install or
   update can revert our two lines the same way. That failure is **quiet** — login keeps working,
   the keyring simply starts prompting again — which is the worst shape a failure can have. If
   auto-unlock stops working, look here first.
2. **The file is owned by the `greetd` package**, so a `greetd` update will produce a `.pacnew` and
   the merge is manual.
3. **greetd with a custom greeter is not the mainstream `pam_gnome_keyring` path.** It should work
   and it is not verified on this machine. Treat the first login after the change as a test.

### Order, and the one ordering that can hurt

**Install the package first.** Editing PAM to reference a module that is not on disk is the only step
here that can go wrong in a way that matters. With `optional` even that is survivable, but there is
no reason to find out.

```
1.  sudo pacman -S gnome-keyring          # closes the gap on its own; verify before going further
2.  busctl --user call org.freedesktop.secrets /org/freedesktop/secrets \
        org.freedesktop.DBus.Peer Ping    # must answer before step 3 is worth taking
3.  sudo cp /etc/pam.d/greetd /etc/pam.d/greetd.bak.machine-state.<date>
4.  edit /etc/pam.d/greetd as above
5.  keep a root TTY open, then log out and back in
```

Rollback: step 1 is `pacman -R gnome-keyring`; steps 3–4 are `cp` the backup back. Nothing in this
repository changes, because nothing here is projected.

---

## 4. Done — `canonical/tooling/proton-drive.md`

**No longer a draft.** Installed and verified 2026-09-06; the record is at that path and `ms status`
reports `proton-drive 0.8.0 responds`. It is the one piece of this that did not need root and did not
need the keyring. **What the keyring decision settled:**

- **Credential store: the default.** `PROTON_DRIVE_CREDENTIALS_STORE` is not set, anywhere. The CLI
  uses `keychain`, the session lands in the login keyring under service
  `ch.proton.drive/drive-sdk-cli`, and there is nothing to project and nothing an agent session can
  get wrong. The earlier draft's `pass` route is dropped along with the environment variable it
  needed.
- **`unsafe_file` is refused** and stays refused. It writes the session to disk in the clear.
- **Nothing else moves.** The artifact is still `linux/x64` of `0.8.0` — `x86_64` rules out arm64,
  AVX2 present rules out `x64-baseline`, glibc 2.44 rules out musl — still 112.48 MiB with a SHA-512
  and **no signature**, still installed to `~/.local/bin` as a loose binary that `ms changes` tracks
  by content hash.
- **The check is now proven, both ways.** `check = "proton-drive help"` — offline-safe, 0.107 s, no
  account. `fail` reached by truncating a copy to half its length: valid ELF header, so it executes
  and dies on the destroyed payload, exit `135`. `missing` reached under `env -i` with a narrow
  `PATH` in a throwaway copy: `not installed`, counted absent, exit `1`. Bare `proton-drive` does
  open a REPL, so both recorded commands were run with stdin closed under `timeout` first.
- **One thing found that the draft did not predict:** `--version` makes a network call to Proton's
  update check. It degrades silently offline (0.333 s online vs 0.107 s with `unshare -rn`) rather
  than hanging, so it is hook-safe — but `ms status` now reaches Proton on every run, and that is
  recorded in the record rather than left to be discovered.
- **`auth login` remains yours.** It opens a browser. An agent cannot complete it and should not try.

---

## 5. What this asks of you

| # | Step | Whose | Reversible by |
| --- | --- | --- | --- |
| 1 | `sudo pacman -S gnome-keyring` | yours (root) | `pacman -R gnome-keyring` |
| 2 | verify the bus name answers | mine | — |
| 3 | promote the gnome-keyring record, prove its check fails | mine | delete the record |
| 4 | PAM edit — **optional**, only to drop the prompt | yours (root) | restore the backup |
| ~~5~~ | ~~download + verify + install the Drive CLI~~ — **done** | mine | delete the binary |
| ~~6~~ | ~~prove the Drive check, promote its record~~ — **done** | mine | delete the record |
| 7 | `proton-drive auth login` | yours (browser) | `auth logout` |

Steps 1–3 stand alone and are worth doing whether or not the Drive CLI is ever installed: this
machine currently has no credential store at all, and that is a gap independent of what found it.
