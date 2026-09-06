# Proton Drive CLI

## Function

Proton Drive file operations from a terminal: browse, upload, download, trash, share, invite, and
album and photo commands. Built on the Proton Drive SDK, the same foundation as the desktop and
mobile clients.

**It is not a sync client.** No continuous mirroring, no mount, no daemon, no watched directory.
Every transfer is a command someone runs. Third-party projects wrap it to add sync; none are
Proton's and none are in scope here.

Installed 2026-09-06. The record was drafted before the install and completed after it, which is the
order `machine-state-t0u.4` used and the order that found `machine-state-q4r`.

## Role

An application, not substrate. Nothing in this repository depends on it.

It is the **only route to Proton Drive on this machine**, and the third of a Proton surface this
repository already records: `proton-mail-bin` and `proton-pass` are packaged, Drive was not
addressable from Linux at all until Proton shipped this.

## Ownership

**NOT A PACKAGE, and that is the whole difference from the other two Proton records.** A
Proton-published standalone executable, fetched over HTTPS and placed by hand at
`~/.local/bin/proton-drive`.

| | |
| --- | --- |
| Version | `0.8.0`, released `2026-08-13` (`cli-drive@0.8.0+06e8c605`, SDK `js@0.21.0+06e8c605`) |
| Artifact | `https://proton.me/download/drive/cli/0.8.0/linux-x64/proton-drive` |
| SHA-512 | `cf61c2688c45e1055d8add6221d9471a5a5b64bf3bcdb86460f5cb18414596cc4df3cdb6627c9097c94bec32a3c9915ada3211ef2ae5be33c46ebbc996ccaa28` |
| Size | 117 946 496 bytes (112.48 MiB) — it embeds the Bun runtime |
| Source | `https://github.com/ProtonDriveApps/sdk`, directory `cli/` |

Verified twice on 2026-09-06: once on the downloaded file and again at `~/.local/bin/proton-drive`
after installation, so the recorded hash describes the file that is actually on the machine rather
than the one that was fetched.

**Nine artifacts are published; this is the one for this machine, chosen rather than assumed.**
Counted from the index rather than eyeballed: `macos/{arm64,x64}`, `linux/{arm64,x64,x64-baseline,
arm64-musl,x64-musl}`, `windows/{arm64,x64}`.

- `x86_64`, so neither `arm64`.
- `avx2` present in `/proc/cpuinfo` (Intel Core Ultra 9 290HX Plus), so **not** `x64-baseline` —
  that build exists for CPUs without AVX2, where the ordinary one dies with `Illegal instruction`.
- glibc 2.44, so not `x64-musl`.

**The provenance is the weakest of any record here, and it is not going to be dressed up.** Proton
publishes a SHA-512 per artifact, on the same HTTPS page that serves the binary — one compromise
falsifies both. There is **no detached signature and no signing key**. Compare `steam` or
`proton-pass`: repository packages validated by signature against a keyring the system already
trusts. This is trust-on-first-use over TLS; the checksum catches a corrupted download, not a
hostile one.

Not in any configured repository — `pacman -Ss proton-drive` returns nothing. The AUR is excluded by
`machine-state-t0u.1` on purpose: an unofficial PKGBUILD adds a packager to trust without removing
the one already being trusted.

## Intent

**User-scope, no root.** It sits beside the three other unpackaged tools on this machine — `bd`,
`claude`, `dcg` — and installing it needed no privilege at all.

**Updates have no database to ask, so its content is the record.** `checkupdates` and `ms changes`
both query the package database; no package owns this file, so both would stay silent forever. It is
therefore tracked as a **loose binary**: `ms changes` hashes it and reports `replaced` when the bytes
move. Same mechanism and same limit as the other three — the hash says *it changed*, never *it is
still authentic*. Re-verify the published SHA-512 when replacing it.

The CLI also checks for updates itself, which is covered under Verification because it is a property
of the check command.

**Credentials: the default store, deliberately.** `PROTON_DRIVE_CREDENTIALS_STORE` is **not set,
anywhere**, so the CLI uses `keychain` and the session lands in the Secret Service under service
`ch.proton.drive/drive-sdk-cli`. Nothing is projected and nothing an agent session can get wrong.

That was the deciding property. The alternative, `PROTON_DRIVE_CREDENTIALS_STORE=pass`, means
passwordstore.org — not Proton Pass, an unfortunate collision — and would have to be set correctly in
every context the CLI runs in, agent sessions included; a context that missed it would use a
different store, silently. The third option, `unsafe_file`, writes the session to disk in the clear
and is **refused**.

**Authenticated 2026-09-06, and the session is where this record said it would be.** That paragraph
previously read: `org.freedesktop.secrets` is not activatable on this machine, so `auth login` has
nowhere to put a session, and the CLI cannot be authenticated until one exists. True on 2026-09-05,
settled by `machine-state-t0u.10`, and closed by `machine-state-t0u.13`.

The item, read back off the bus rather than assumed:

| | |
| --- | --- |
| Collection | `login` — the keyring `pam_gnome_keyring` created, not `Default_keyring` |
| Label | `ch.proton.drive/drive-sdk-cli/auth-session` |
| Attributes | `service=ch.proton.drive/drive-sdk-cli`, `account=auth-session`, `xdg:schema=com.oven-sh.bun.Secret` |

**That schema is worth noticing: `com.oven-sh.bun.Secret`.** The credential is written through *Bun's*
secrets API, not through libsecret directly — the same embedded runtime that makes the binary 112
MiB. It means the storage behaviour belongs to Bun, and a future Bun change can move it without
Proton changing anything.

Demonstrated the same day: `proton-drive filesystem list /` returns the account's real top level —
`/my-files`, `/devices`, `/shared-by-me`, `/shared-with-me`, `/trash`, `/albums`, `/photos`,
`/photos-shared-by-me`, `/photos-shared-with-me`, `/photos-trash` — exit `0`. Before the login the
same command printed `You need to login first` and exited `1`, promptly and without prompting.

**A LOCKED STORE PROMPTS; IT DOES NOT LIE.** This was the open worry, and it was tested rather than
assumed: the login collection was locked again over D-Bus (`Secret.Service.Lock`) and the same
command re-run. It raised a visible `Unlock Login Keyring` prompt and WAITED — it did not fall back
to `You need to login first`, which would have made a locked keyring indistinguishable from a lost
session. Answering the prompt completed the listing, exit `0`.

The cost of that correctness is a command that blocks until someone answers. On this machine the
login keyring is not reliably unlocked at boot (`machine-state-t0u.11`), and an unanswered gcr prompt
is not withdrawn when its client is killed (`machine-state-jw9`). **Anything that runs `proton-drive`
unattended must use a timeout and must treat a timeout as "the store was locked", not as an error
from Drive.**

**The Drive session is re-derivable, which is why a keychain is the right weight for it.** Lose it
and `auth login` regenerates it. Durable, portable, backed-up storage is for secrets that cannot be
regenerated; this is not one. It also means an unlocked keyring readable by any agent
(`machine-state-u40`) is an acceptable home for this particular secret and not for others.

**The Drive's contents are not ours.** This substrate records that the executable exists and that its
bytes are the ones Proton published. It does not read, project, back up or index anything in the
Drive, and it stores no credential. Secrets management is a recorded non-goal (`SUBSTRATE.md` §9) —
the same boundary `proton-pass` and `steam` draw.

**Authentication is the user's step.** `proton-drive auth login` opens a browser; no password is
typed at the command line. An agent cannot complete it and should not try.

**Uninstall is three steps, listed because an unpackaged tool has no `pacman -R`:**
`proton-drive auth logout` while a session exists, delete `~/.local/bin/proton-drive`, remove the app
data and cache directories (`$PROTON_DRIVE_CACHE_DIR` if set, otherwise the XDG-standard locations).
Then delete this record, which is how this repository stops wanting a tool.

## The local mirror

**`~/Drive/my-files` is remote `/my-files`, and one local directory maps one remote root.** That
shape is deliberate: `/photos` is going to Immich (`machine-state-t0u.5` territory, `immich-go` is
packaged and the server wants Docker) and will need a staging directory with a pipeline behind it,
not a plain mirror. Keeping the roots separate now means nothing has to be renamed then.
`machine-state-t0u.15`.

**It is a mirror by command. It is not a sync, and it never becomes one.** This CLI has no daemon, no
watcher and no memory of what it saw last, so a scheduled `download` is a one-way copy: it cannot
tell *deleted here* from *added there*. A local file can be stale with nothing on screen to say so —
Dolphin shows the tree under Home as an ordinary folder, with no emblems, no status column and no
badge, because nothing is watching it. Deleting a file here does not touch the Drive; editing one
does not push.

**Two named modes, and the strategy flag is never left off.** `download` and `upload` both *prompt*
when no conflict strategy is given, and on this machine an unanswered `gcr` prompt hangs its caller
and is not withdrawn when that caller dies (`machine-state-jw9`).

| Mode | Command | Meaning |
| --- | --- | --- |
| stage | `download -f skip -d merge` | never overwrites a local file |
| refresh | `download -f remove -d merge` | remote wins, deliberately |
| push | `upload -f create-new-revision -d merge` | keeps the remote history rather than replacing it |

`upload` also offers `replace`, which **trashes the remote copy** before uploading the local one. It
is not used here: `create-new-revision` keeps a revision, and `replace` throws the remote version
away on the strength of a local file whose freshness nothing has established.

**An allowlist, not a denylist, and it is empty today.** Nothing is pulled unless it is named here.
`/my-files` contains a folder called `ssh` and a file called `Tesla Backup Passcodes`; a blanket
mirror would put those on this disk in the clear, and secrets management is a recorded non-goal
(`SUBSTRATE.md` §9). A denylist would include each new sensitive folder by default until somebody
remembered to exclude it. **Excluded even if the allowlist grows:** `/my-files/ssh`, and any file
whose contents are a credential.

The repository records the convention and nothing about the contents: no projection, no backup, no
index, no file list.

**MODIFICATION TIMES ARE NOT PRESERVED, measured 2026-09-06 and not inferred.** A 67-byte file
uploaded at `13:48:58Z` and downloaded back reported `modificationTime 2026-09-06T13:48:58.000Z` on
the server and landed locally with an mtime of `14:49:18` — the moment it was written. So **mtime
cannot decide which side is newer**, with this client either. rclone's Proton Drive backend is
documented as not supporting modification times; this is the same limit reached from the other
direction, and it constrains any future sync design regardless of which engine wins.

**The round trip is proven, both ways, in one pass.** A 67-byte probe was uploaded to `/my-files`,
confirmed server-side with `filesystem info` (`type: file`, `mediaType: text/plain;charset=utf-8`,
`directRole: admin`), downloaded into `~/Drive/my-files`, compared byte-for-byte against the original
— identical — and then trashed. It left `/my-files` and appeared in `/trash`, which is where a trashed
file is supposed to be and is not the same as gone.

## Verification

`help` prints the command surface and exits `0`. It is the only command that touches neither the
network nor the account: there is no `status` or `whoami` subcommand, `auth login` opens a browser,
and every other verb acts on the Drive.

```toml
group      = "Applications"
version    = "proton-drive --version"
version_re = "([0-9][0-9.]*)"
check      = "proton-drive help"
ok         = "responds"
fail       = "not responding"
missing    = "not installed"
```

**Bare `proton-drive` opens an interactive REPL**, and this repository forbids a command that can
block on a prompt. Both commands above were run with stdin closed under `timeout` before this record
was written, and both exit on their own. A check that hangs would stall every `ms status`, the
session-start hook included.

**`--version` makes a network call, and that is recorded rather than hidden.** It prints `You are
running the latest version.` — an update check against Proton. Measured 2026-09-06: 0.333 s online,
0.107 s with the network removed (`unshare -rn`), where it prints the two version lines and drops the
third. It **degrades silently and quickly** rather than hanging, so it is safe in a hook, but
`ms status` does reach Proton on every run for as long as this record uses `--version`. No documented
flag suppresses it.

**Falsifiability, and it is proven both ways here rather than trusted.**

Proven 2026-09-06 — the `fail` path, which is the one that is usually hard to reach. A copy of the
binary truncated to half its length keeps a valid ELF header, so it **executes** and then dies on the
destroyed Bun payload: exit `135`. Non-zero from a command that ran routes to `fail`, so a
present-but-corrupt binary reads `not responding` rather than `not installed`. That distinction is
the point of having both labels.

Proven the same day — the `missing` path, in a throwaway copy of the repository under `env -i` with
`PATH=/usr/bin:/bin`, a redirected `HOME`, and no remembered path for this tool yet. The command
cannot be executed, `rc` is `None`, and `ms status` reports `not installed`, names it in `recorded
here but not installed`, and exits `1`. The binary itself was not touched: `dcg` refuses an `mv`
against `~`, correctly, and the refusal was answered by narrowing the test rather than by widening
the guard.

**No `presence` probe, and that is correct rather than an omission.** `machine-state-q4r` added one
for records built on a package query, where `pacman` executes fine while reporting the package
absent. Here the check command **is** the tool, so a command that cannot be executed is a tool that
is not there — presence and integrity are one question, and `ms status` already answers it. The
distinction that record introduced applies to package-query records only, and this is the clearest
example of the other kind.
