# restic

## Function

Encrypted, deduplicated backups. Each run saves a snapshot of the given folders into a repository;
only changed chunks are stored, so a daily run costs minutes and megabytes. Command line only, no
daemon. Restore any snapshot (`restic restore`), browse one as a folder (`restic mount`, needs
`fuse2`), check the repository (`restic check`), copy snapshots between repositories (`restic copy`).

**Here it is the machine's backup.** Until 2026-11-13 there was none: snapshots lived on the same SSD
they protect. Bead `machine-state-yqm`.

## Role

A tool, not a service. What runs it, when, and on what is the backup plan below; the schedule goes
through `cap`, never a timer of its own.

**Layout:**

| What | Repository | Cadence |
| --- | --- | --- |
| home folder | `/mnt/data/backup/restic` (4 TB M.2), repository `da4d8fdae9` | daily, `cap` action `backup.home` |
| home, off the laptop | the WD Elements disk, by `restic copy` from the 4 TB | weekly, when plugged in (not yet built) |
| old-PC archive (`/mnt/data/archive/old-pc`) | the WD Elements disk | after changes (not yet built) |

**The daily run** is `backup.home` (`canonical/actions/backup.toml`), bound to `time.daily`:
`restic backup ~ --exclude-file canonical/restic/home.exclude --one-file-system --exclude-caches
--no-cache`, password from the keyring (`service=restic repository=<repo>`). It is the first
`maintain`-class action (`CAPABILITIES.md` §4): it runs unattended only while
`/etc/machine-state/grants.toml` names it and this repository under `[maintain]`. Silent when
complete. Notifies and writes an inbox note when it fails, or when it is *incomplete* (restic exit 3:
snapshot made, some files unreadable; said once per new set of files). Each run's result is in
`~/.local/state/agents/backup-home.json`. `backup.freshness`, on `time.hourly`, says so once a day
when the newest snapshot is over 36 hours old or none was ever recorded. By hand: `cap act backup.home`.
Pruning (`restic forget --prune`) deletes, so it is not part of this and is done by hand.

**Copies that exist now (2026-11-13):**

| Data | Copies | Checked |
| --- | --- | --- |
| Laptop home (less `home.exclude`): 112,938 files, 9.6 GiB | restic snapshot `462b12f6`, 4 TB | restored `.ssh .gnupg` keyrings `Documents src/machine-state`: identical; `restic check` clean; Proton Pass copy of the password opens it |
| Old PC (Extreme SSD, exFAT): 416,708 files, 311,824,839,195 bytes | original; WD `old-pc-copy-2026-11-13/`; 4 TB `/mnt/data/archive/old-pc/` | both: file count and bytes equal the original |
| Laptop home essentials (`src .config Documents Drive .ssh .gnupg` keyrings, `.claude .pi .codex`) | WD `quick-copy-2026-11-13/home-essentials.tar.zst`, 7.6 GB | read back, 150,666 entries |
| Models | main SSD; WD `Models/<org>--<repo>/` | SHA-256 (see `strata.md`) |

**The quick copy is unencrypted and holds SSH/GPG keys and the keyring.** It was a stopgap until
the first restic backup was restore-tested, which it now is: delete it the next time the WD disk is
plugged in.

**The password** opens the repository's master key; it is not the encryption key itself, so
`restic key add` / `key remove` change it without re-encrypting, but do not undo a leak of the
old one — that needs a new repository and `restic copy`. It lives in the login keyring for the
automatic runs and in Proton Pass. On the WD disk (not encrypted) the restic password is the only
lock, so it is long and random, never typed.

## The disk it writes to

Not a tool, but nothing else describes it yet. Predator SSD GM6 4 TB
(`/dev/disk/by-id/nvme-Predator_SSD_GM6_4TB_PSBQ65150100630`), set up 2026-11-13: LUKS2 (label
`data`, LUKS UUID `e35da71c-4cd5-4e20-99e7-7b4fa86b777f`), btrfs inside (label `data`), mounted at
`/mnt/data` with subvolumes `backup`, `models`, `archive`, owned by `klaas`. Installed by hand, as
`/etc` files here are; these are the lines added:

```
# /etc/crypttab
data UUID=e35da71c-4cd5-4e20-99e7-7b4fa86b777f /etc/cryptsetup-keys.d/data.key luks,discard,nofail
# /etc/fstab
/dev/mapper/data /mnt/data btrfs noatime,compress=zstd:3,nofail,x-systemd.device-timeout=10s 0 0
```

Unlocked at boot by a 64-byte keyfile (root-only). The passphrase is the recovery key, kept in
Proton Pass with the LUKS header backup. `nofail`: a missing or failed disk never stops boot. The
keyfile sits on the unencrypted main SSD, so this protects the disk on its own (removed, discarded,
returned), not a stolen laptop.

**Not for models that are served.** Strata reads from disk while it generates (~14 MB/s of small
reads, measured 2026-11-13) because its 84 GB model exceeds VRAM + locked RAM, so its models stay on
the main SSD. `models` here is for those kept but not served.

## Ownership

`cachyos-extra-v3/restic 0.19.1-1.1` (packaged by CachyOS; `extra/restic 0.19.1-1` is the same
upstream version, repository order picked CachyOS), BSD-2-Clause, upstream
`https://github.com/restic/restic`. Depends only on `glibc`. 10.45 MiB download, 41.40 MiB installed.
Optional `fuse2` for `restic mount`, not installed.

## Intent

**Install:** `sudo pacman -S --needed --noconfirm restic`. Done 2026-11-13 by the disk setup script.

**Uninstall:** `pacman -Rs restic` and delete this record. The repositories are plain files on the
disks it wrote to; removing the program leaves them, and any restic build can read them.

## Verification

Installed 2026-11-13; first snapshot restore-tested the same day (above). The check below only
proves the program is intact. Whether backups are *happening* is `backup.freshness`'s job, and an
`ms status` line reading the age of the last recorded run would be a third, timer-independent
observer (not built yet).

```toml
group      = "Applications"
version    = "pacman -Q restic"
version_re = "([0-9][0-9.]*)"
presence   = "pacman -Q restic"
check      = "pacman -Qkk restic"
ok         = "files intact"
fail       = "files altered or missing"
missing    = "not installed"
```
