# Tailscale

## Function

Private networking to reach the user's two VPSs over their existing tailnet.

## Role

A system network client, maintained independently of machine-state. The CLI and
the system daemon provide connectivity; the VPSs and their credentials are not
managed by this repository.

## Ownership

The `tailscale` package is provided by the configured CachyOS repositories and
updated through the normal pacman workflow. Package files and daemon state are
vendor-owned. Do not record authentication keys or tailnet credentials here.

## Intent

The user requested installation and connection to an existing tailnet for VPS
access. Daemon activation and enrollment are needed for that connection.
Do not advertise routes, an exit node, or new services. Do not select an exit
node or accept subnet routes without a separate choice. DNS and inbound access
are to be inspected and recorded rather than assumed.

Installed from `cachyos-extra-v3/tailscale 1.104.4-1.1` on 2026-11-03 and
enrolled in the existing GitHub-backed tailnet. The system daemon is enabled
and active. Verified preferences: DNS acceptance off, shields up, no accepted
subnet routes, exit node, advertised routes or services, or Tailscale SSH.
Use Tailscale IP addresses for the VPSs until DNS is deliberately enabled.
Tailscale also reports a systemd-resolved/NetworkManager wiring warning; DNS
was not changed as part of this installation.

Both visible online Linux peers responded to `tailscale ping`: `prod` directly
and `ubuntu-16gb-nbg1-1-1` via DERP Frankfurt. This proves Tailscale-level
reachability, not SSH login. A third similarly named Ubuntu node was offline.
The CLI requires root to change its preferences; no operator was configured.

## Verification

Package presence and integrity are separate from daemon and tailnet status:

```toml
group      = "Applications"
version    = "pacman -Q tailscale"
version_re = "([0-9][0-9.]*)"
presence   = "pacman -Q tailscale"
check      = "pacman -Qkk tailscale"
ok         = "files intact"
fail       = "files altered or missing"
missing    = "not installed"
```

On 2026-11-03 `pacman -Qkk tailscale` reported 26 files, none altered, outside
the filesystem sandbox. Inside it, remapped ownership incorrectly reports all
files altered; do not treat that sandbox reading as the machine's state.
