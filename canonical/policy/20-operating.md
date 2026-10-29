## Operating rules

**This repository edits a live workstation.** Changes here alter the machine in use, not just
code. For anything outside the repository — a file in `~`, a systemd unit, an installed package —
draft it somewhere reviewable first, and apply it as a separate, explicit step.

**Experiments run in throwaway copies, never the live tree.** This matters most when the question
is how some *other* tool behaves: copy the repository, redirect `HOME` if the test would cross
into it, and let the copy be wrong instead of the machine.

**Follow-ups go through `cap`, never through your own timers.** When asked to keep the user
informed, check back later or repeat something, do not write a script, cron entry or systemd
unit. Propose an event binding in `canonical/bindings/events.toml` for an existing `cap` action
(`cap list`), plus the grant line the user must install in `/etc/machine-state/grants.toml`.
If no action fits, say so and file a bead. That way the user knows it exists, the grant decides
what it may do, and its results land in `cap inbox`.

**Never issue a command that can block on a prompt.** Use `pacman --noconfirm` and
`ssh`/`scp -o BatchMode=yes`. This machine has no `-i` alias on `cp`, `mv` or `rm`, so `-f` is not
needed to avoid a hang — reach for it only when force is actually meant.

**A refusal from `dcg` is answered by narrowing the command**, or by an allowlist entry with a
recorded reason — never by disabling the guard. See `canonical/tooling/dcg.md`.
