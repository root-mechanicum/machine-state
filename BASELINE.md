# Baseline Inventory

Read-only inventory of this workstation. Captured 2026-08-30.

## System

| Item | Value |
| --- | --- |
| Machine | ASUS ROG Strix SCAR 18 G835LXG (board G835LXG) |
| BIOS | G835LXG.304 (2026-04-28) |
| OS | CachyOS Linux (rolling, Arch-based) |
| Kernel | 7.2.2-1-cachyos, x86_64, PREEMPT_DYNAMIC (built 2026-08-28) |

## CPU

- Intel Core Ultra 9 290HX Plus — 24 cores / 24 threads, 1 socket, 1 NUMA node
- Family 6, model 198, stepping 2, microcode 0x122
- 800 MHz – 5500 MHz; VT-x enabled
- Cache: L1d 768 KiB, L1i 1.3 MiB, L2 40 MiB, L3 36 MiB
- Notable ISA: AVX2, AVX-VNNI, VAES, VPCLMULQDQ, GFNI, SHA-NI, IBT/user_shstk (no AVX-512)

## GPUs

| Device | PCI | Driver |
| --- | --- | --- |
| Intel Arrow Lake-S integrated graphics (rev 06) | 00:02.0 | i915 (card1) |
| NVIDIA GeForce RTX 5090 Laptop (GB203M / GN22-X11) | 02:00.0 | nvidia (card2) |

- NVIDIA driver 610.57.04, 24463 MiB VRAM
- Hybrid setup: the internal panel (eDP-1) hangs off the Intel iGPU; all NVIDIA connectors (DP-1, DP-2, eDP-2, HDMI-A-1) are disconnected

## Memory

- RAM: 65182244 kB total (~62 GiB)
- Swap: zram0, 62.2 GiB

## Disks / Filesystems

| Device | Size | Layout |
| --- | --- | --- |
| nvme1n1 (HFS001TEJ9X101N) | 953.9 G | p1 4G vfat `/boot`; p2 949.9G btrfs (root) |
| nvme0n1 (HFS001TEJ9X101N) | 953.9 G | Windows: 450M vfat, 16M reserved, 923.8G BitLocker, 1.3G ntfs, 28G ntfs, 260M vfat — not mounted |

btrfs subvolumes on `/dev/nvme1n1p2`: `@` → `/`, `@home` → `/home`, `@srv` → `/srv`, `@cache` → `/var/cache`, `@tmp` → `/var/tmp`, `@log` → `/var/log`, `@root` → `/root`.

## Desktop / Compositor

- Session type: Wayland (`wayland-1`), not remote; Xwayland present (`DISPLAY=:0`)
- Compositor: Hyprland 0.56.2 (tag v0.56.2, commit efb5099, built 2026-08-05)
- `XDG_CURRENT_DESKTOP=Hyprland`, launched via uwsm (`wayland-wm@hyprland.desktop.service`)
- No full DE (no KDE/GNOME/XFCE shell processes)

## Monitor Configuration

Single display, internal panel only:

- eDP-1 — BOE NE180QA1-MM0, 3840x2400 @ 120.00 Hz at 0x0, scale 2, transform 0
- Physical size 390x240 mm; format XRGB8888; color preset srgb; VRR off
- Available modes: 3840x2400@60, 3840x2400@120
- No external monitors connected

## Development Tools

| Tool | Version | Path |
| --- | --- | --- |
| gcc | 16.2.1 (20260810) | /usr/bin/gcc |
| clang | 22.1.8 | /usr/bin/clang |
| gdb | — | /usr/bin/gdb |
| GNU Make | 4.4.1 | /usr/bin/make (shell alias `make -j24`) |
| Python | 3.14.7 | /usr/bin/python, /usr/bin/python3 |
| Perl | — | /usr/bin/perl |
| vim | 9.2 | /usr/bin/vim |
| sqlite3 | 3.53.4 | /usr/bin/sqlite3 |
| jq | 1.8.2 | /usr/bin/jq |
| ripgrep | 15.2.0 | /usr/bin/rg |
| fd | — | /usr/bin/fd |
| bat | — | /usr/bin/bat |
| fish | 4.8.1 | /usr/bin/fish (login shell) |
| bash / zsh | — | /usr/bin/bash, /usr/bin/zsh |

Not installed / not on PATH: node, npm, pnpm, yarn, bun, deno, pip, uv, rustc, cargo, go, java, cmake, ninja (only a shell alias `ninja -j24`), docker, podman, kubectl, terraform, ansible, nvim, code, tmux, lazygit, git-lfs.

## Git & GitHub CLI

- git 2.55.0
- gh 2.98.0 (released 2026-08-21)

## DCG & Claude

- dcg 0.13.9 — `~/.local/bin/dcg`
- Claude Code 2.1.251 — `~/.local/bin/claude`
