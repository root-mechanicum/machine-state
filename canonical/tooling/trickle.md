# Trickle

## Function

Per-command user-space network bandwidth limiter. Start the program under Trickle;
it does not attach to an already running process. Rates are in KB/s:

```sh
trickle -s -d 5000 -u 500 command arguments
```

`-s` runs standalone, `-d` limits downloads and `-u` limits uploads. Either
rate can be omitted. It intercepts network calls, so dynamically linked TCP
applications are the intended target; it does not govern all machine traffic,
and static binaries or UDP traffic may bypass it. Verify the limit with the
actual application when it matters.

## Ownership

Installed at the user's request on 2026-11-07 as AUR `trickle` 1.07-14,
built locally from the AUR recipe and installed with pacman. Package files are
vendor-owned; AUR updates require a separate rebuild and are not provided by
the configured pacman repositories. No daemon is needed for standalone use.

## Verification

```toml
group      = "Applications"
version    = "pacman -Q trickle"
version_re = "([0-9][0-9.]*)"
presence   = "pacman -Q trickle"
check      = "pacman -Qkk trickle"
ok         = "files intact"
fail       = "files altered or missing"
missing    = "not installed"
```

Package presence and `trickle -h` were checked on 2026-11-07; bandwidth
limiting against a real application has not yet been tested here.
