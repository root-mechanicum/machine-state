# Hyprland

## Function

The Wayland compositor for this workstation, running under `uwsm` as
`wayland-wm@hyprland.service`. Configured in Lua: `~/.config/hypr/hyprland.lua` `require`s a
sequence of modules from `~/.config/hypr/config/`.

## Role

Managed desktop configuration — a **tenant** of the substrate, not part of it. The substrate must
not depend on the compositor, and nothing in `bin/ms` knows what Hyprland is.

## Ownership

| Path | Class |
| --- | --- |
| `~/.config/hypr/config/machine-state.lua` | PROJECTED — a module we create |
| `~/.config/hypr/hyprland.lua` | VENDOR — we co-own one `MACHINE-STATE` marker region |
| everything else under `~/.config/hypr/` | VENDOR — pristine copy of `/etc/skel`, package `cachyos-hypr-noctalia` |

Of roughly a thousand template lines, two were ever ours: `kb_layout = "gb"` and
`mode = "3840x2400@120"`. Both now live in our module, which `hyprland.lua` loads **last**, so
what we set overrides what CachyOS ships. Verified 2026-09-01 with both template files reverted to
stock: the live layout and mode are held by our module alone.

## Intent

- The template stays pristine. A decision goes in our module, never in a template file — that is
  what keeps "what CachyOS ships" and "what we decided" separable, and what makes any divergence
  in the template meaningful rather than noise.
- `~/.config/hypr` is a **frozen copy** of a package-maintained template. `/etc/skel` moves with
  package upgrades; the copy does not, and nothing else reports it. That is what the check below
  is for.
- A divergence is not automatically wrong. It is either a package improvement worth adopting or an
  unrecorded hand-edit worth reverting — but it should never be a surprise.

## Verification

The check compares the live config directory against the skel template, excluding our own module.
Now that the template files are pristine, **any** difference is signal.

```toml
group      = "Desktop"
version    = "hyprctl version"
version_re = "([0-9][0-9.]*)"
check      = "diff -rq --exclude=machine-state.lua /etc/skel/.config/hypr/config /home/klaas/.config/hypr/config"
ok         = "template pristine"
fail       = "template diverged"
missing    = "not installed"
```

Proven falsifiable 2026-09-01: appending a line to a copied `binds.lua` makes it exit 1 and report
the differing file.

Note what this does **not** check. `hyprctl configerrors` reports live config errors, but its
exit-code behaviour on a broken config has not been verified here, and a check that cannot fail is
worse than no check — see `SUBSTRATE.md` §5. It is worth adopting once someone confirms it exits
non-zero when errors exist. `version` also requires a running instance: with Hyprland stopped the
version reads `-` while the template check still answers correctly, since it only reads files.
