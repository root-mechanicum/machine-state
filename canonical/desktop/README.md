# canonical/desktop — RESERVED

Empty by design in v0.01. This is the future home of managed desktop configuration:

- `hypr/` — Hyprland, currently 13 unversioned `.lua` files in `~/.config/hypr/config/`
  behind a `hyprland.lua` that `require`s them.
- `noctalia/` — Noctalia shell, currently an unversioned `~/.config/noctalia/config.toml`.

The slot exists now so that adopting them later is *adding a directory and a manifest target*,
rather than reorganising the substrate. Nothing here is projected until that happens; see
`SUBSTRATE.md` §9, which lists desktop config as an explicit v0.01 non-goal.

Both are plain text formats that accept comment markers, so they are reachable by the same
`splice` mechanism the agent instruction files use — no new projector capability required.
