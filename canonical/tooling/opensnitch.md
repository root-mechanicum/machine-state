# opensnitch

## Function

An application firewall for **outbound** connections. `opensnitchd` intercepts each new connection
through an nftables queue, attributes it to a process (eBPF), and decides by rule — allow or deny,
per executable, destination, port or user. `opensnitch-ui` is the Qt tray and popup that asks a
person when no rule matches, and the editor for rules and the connection log.

**Here it is the missing half of the channel model.** `cap` declares which channels an action may
use and refuses an undeclared `net:` — but that is a promise the process keeps about itself. An
agent that runs a tool, or a tool with a bug, is not bound by it. A per-process egress rule is
enforced by the kernel, below anything an agent can talk its way past. That is the reason it is on
this machine, and the reason it is recorded the week the agent got hands (`machine-state-aox`).

## Role

An application, and a **network owner**: a root daemon that sits on every outbound connection on the
machine. Nothing in this repository depends on it yet, and nothing should silently start to — a
stopped daemon fails *open* (see Intent), so it is a guard, never a dependency.

It is **not** an inbound firewall. `ufw` is enabled on this machine and keeps that job; the two
write separate nftables tables and do not overlap in purpose.

## Ownership

`cachyos-extra-v3/opensnitch 1.7.2-4.1`, packaged by `CachyOS <admin@cachyos.org>`,
GPL-3.0-or-later, upstream `https://github.com/evilsocket/opensnitch`. Signature enforced, same
trust root as `asusctl`.

| | |
| --- | --- |
| Download | 5.56 MiB |
| Installed | 20.49 MiB |
| Built | 2026-01-10 |
| Depends | `libnetfilter_queue`, `libnfnetlink`, `python`, `python-grpcio`, `python-protobuf`, `python-slugify`, `python-pyqt5`, `python-pyinotify`, `python-notify2`, `python-packaging` |
| Optional | `logrotate`, `python-qt-material`, `python-pyasn` |
| Replaces | `opensnitch-ebpf-module` — the eBPF objects ship in this package |

**The install pulls a Qt 5 stack** (`qt5-base`, `python-pyqt5`, `qt5-translations`) and gRPC tooling:
22 packages in all, read from `pacman -Sp` on 2026-10-31. Qt 5 is new to this machine.

**It does not pull `qt5-wayland`, and without it the UI is unreadably small.** The session sets
`QT_QPA_PLATFORM=wayland;xcb`; with no Wayland plugin Qt 5 silently takes `xcb`, so the UI runs under
XWayland. This machine has `xwayland:force_zero_scaling = true` on a scale-2 panel (`eDP-1`,
3840×2400), so an XWayland client draws at 1× — half size. Seen on first launch, 2026-10-31.
The fix is the missing plugin (`qt5-wayland`), not a per-app `QT_SCALE_FACTOR`: native Wayland
gets the compositor's scale the way every other window here does.

What the package puts on disk, read from the package before installing:

| Path | What |
| --- | --- |
| `/usr/bin/opensnitchd`, `/usr/bin/opensnitch-ui` | daemon, UI |
| `/usr/lib/opensnitchd/ebpf/*.o` | process, DNS and connection probes |
| `/usr/lib/systemd/system/opensnitchd.service` | `WantedBy=multi-user.target`, `Restart=always` |
| `/etc/opensnitchd/default-config.json` | daemon config (below) |
| `/etc/opensnitchd/system-fw.json` | its own nftables chains |
| `/etc/opensnitchd/rules/` | one JSON file per rule — *the* state worth owning |
| `/usr/share/applications/opensnitch_ui.desktop` | **no** autostart entry ships |

The kernel side is present: `/sys/kernel/btf/vmlinux` exists, `CONFIG_NFT_QUEUE=m`,
`CONFIG_NETFILTER_NETLINK_QUEUE=m`, `CONFIG_KPROBES=y`, `CONFIG_BPF_EVENTS=y` on 7.3.0-cachyos.

## Intent

**It fails open, by default, in two places — and that is the first thing to know.**

- `"DefaultAction": "allow"` — with no rule and **no UI connected**, a connection is allowed.
- `"QueueBypass": true` — if the daemon is not reading the queue, packets pass.

So with the daemon running and the UI closed, the machine behaves as if nothing were installed,
except for explicit deny rules. That is the right default for a first install — a firewall that
blocks the session's own plumbing is worse than none — and the wrong one to forget about.

**`"FlushConnsOnStart": true` — the first start will drop open connections.** Expect the Proton Mail
bridge, browser tabs and any SSH session to reconnect. Local vLLM requests in flight may fail once.

**The UI is the prompt, and it is a session program.** The daemon talks to it over
`unix:///tmp/osui.sock`. Without the UI there are no popups and the default action applies. The
package ships no autostart entry; XDG autostart does run in this session (systemd's
`app-*@autostart` units), and the UI offers to write `~/.config/autostart/opensnitch_ui.desktop`
itself. **Decided 2026-10-31: neither.** The UI starts from our Hyprland module
(`canonical/desktop/hypr/machine-state.lua`, a `hyprland.start` handler, with the 3 s delay its
`.desktop` file asks for so the tray is up first). That keeps it canonical and visible to `ms diff`;
a file in `~/.config/autostart` would be state this repository cannot see. If the UI offers to
write its own autostart entry, decline — two starts would mean two UIs.

**Unverified until installed:** the UI's popup timeout and its action on timeout; whether loopback
(`127.0.0.1:8000`, vLLM; `127.0.0.1:1143`, the bridge) is intercepted or exempt; and whether eBPF
attribution works on this kernel or falls back to `/proc`. Each is a claim about a package not yet
on the machine, and is to be checked against it, not tidied up.

**What it is for, later, stated so it is not mistaken for done.** Rules are files, so the rules that
matter can become canonical — the obvious first one: the headless agent (`pi -p`, the role's `ask`)
may reach `127.0.0.1:8000` and nothing else. That is `machine-state-aox` territory and is not
built here.

**Install** (root; the user runs it):

```sh
sudo pacman -S --noconfirm opensnitch qt5-wayland qt6-wayland
sudo systemctl enable --now opensnitchd
```

The UI then starts with the session (see above); nothing to launch by hand after the next login.

**Uninstall:** `sudo systemctl disable --now opensnitchd`, `sudo pacman -Rns opensnitch`, remove
`/etc/opensnitchd/rules/` (pacman leaves rules it did not ship), and `~/.config/autostart/
opensnitch_ui.desktop` if it was written. The nftables table goes with the daemon.

## Verification

The same split as every package record here: `pacman -Q` answers *installed*, `pacman -Qkk` answers
*intact*, and one exit code cannot carry both (`machine-state-q4r`). The altered-file path is proven
without root under `canonical/tooling/proton-pass.md`.

```toml
group      = "Applications"
version    = "pacman -Q opensnitch"
version_re = "([0-9][0-9.]*)"
presence   = "pacman -Q opensnitch"
check      = "pacman -Qkk opensnitch"
ok         = "files intact"
fail       = "files altered or missing"
missing    = "not installed"
```

**A daemon check is deliberately not in that block** — the open question `asusctl.md` records for
`asusd`. Here it is sharper: because the daemon fails open, "installed and intact" says nothing
about whether anything is being filtered. Once installed, `systemctl is-active opensnitchd` is the
candidate, under its own label so that *stopped* reads as *unguarded*, not as *missing*.

**Note on `pacman -Qkk` here:** `/etc/opensnitchd/default-config.json` is a backup file. If it is
edited, `-Qkk` may report it as modified — which is correct, and would mean the config is now state
this record should own.
