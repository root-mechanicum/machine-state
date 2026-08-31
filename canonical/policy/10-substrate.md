## machine-state

This machine's configuration and agent policy are kept in the `machine-state` repository, which
is the canonical source of truth. Agent-facing files here are **projections** of that repository,
not originals — regenerate them with `ms project`, inspect them with `ms status`, and check for
hand-edits with `ms diff`.

Where the truth lives:

| To change | Edit | Then run |
| --- | --- | --- |
| this region | `canonical/policy/` | `ms project` |
| a shared skill | `canonical/skills/` | `ms project` |
| what a tool is for | `canonical/tooling/<tool>.md` | `ms status` |

`SUBSTRATE.md` in that repository is the full contract: what is canonical, what is vendor-owned,
and what may be written where. Read it before adding an agent, a managed config, or a tool.

Other regions of this file belong to other owners and are not ours to edit.
