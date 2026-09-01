# Noctalia

## Function

The desktop shell for this workstation: bar, launcher, notifications, lock screen. Installed as
the package `noctalia` (5.0.0_beta.10-1.1); its configuration is not package-owned.

## Role

Managed desktop configuration, alongside Hyprland — a **tenant** of the substrate, not part of it.

## Ownership

Noctalia reads a three-layer stack, and the layers have different owners. This is the whole story
and the reason the seam is easy:

| Layer | Path | Owner |
| --- | --- | --- |
| base | `~/.config/noctalia/config.toml` | VENDOR — byte-identical to `/etc/skel`, owned by `cachyos-hypr-noctalia` |
| drop-in | `~/.config/noctalia/*.toml` | **available to us** — every `*.toml` in the dir is read and merged |
| overrides | `~/.local/state/noctalia/settings.toml` | VENDOR — written by the app itself |

Verified 2026-09-01 in an isolated `XDG_CONFIG_HOME`, never against the live shell:

- A second `*.toml` in the config dir **is read**, and **merges** rather than replaces — 21
  sections before and after adding one that sets a single key.
- Load order is **alphabetical, later wins**. A file sorting *before* `config.toml` lost to it;
  `machine-state.toml` sorts after and wins. **The filename is load-bearing**, and a future
  `zz-*.toml` would beat ours.
- `noctalia config validate` exits 0 on a config dir carrying a drop-in.

So the seam is a pure `render` of `~/.config/noctalia/machine-state.toml`. No splice, no marker,
nothing of the vendor's touched — cleaner than Hyprland, which needed a spliced `require` line.

## Intent

- The base `config.toml` stays pristine. Our decisions go in a drop-in, so "what CachyOS ships"
  and "what we decided" remain separable, exactly as with Hyprland.
- **Nothing is projected yet, because there is nothing to project.** `config.toml` is
  byte-identical to skel, and `settings.toml` holds only app-generated runtime state: a schema
  version, lock-screen widget geometry keyed to `@eDP-1`, and wallpaper bookkeeping. No decision
  has been made here worth recording. The adapter is written the day one is.

**Known limit — we own the declarative layer, not the effective value.** The app's
`settings.toml` overrides our drop-in, so a setting changed in the Noctalia UI silently wins over
canonical, and `ms diff` will *not* report it: our file is unchanged, only the effective value
differs. This is the same shape as `dcg doctor` verifying installation rather than posture. If
that becomes a problem, the fix is a check that compares `noctalia config export merged` against
what canonical expects — not a fight with the app over its own state file.

## Verification

`noctalia config validate` checks the whole stack and exits non-zero on an invalid config.

```toml
group      = "Desktop"
version    = "noctalia --version"
version_re = "([0-9][0-9.]*)"
check      = "noctalia config validate"
ok         = "config valid"
fail       = "config invalid"
missing    = "not installed"
```
