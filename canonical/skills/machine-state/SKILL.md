---
name: machine-state
description: Use when working on this workstation's configuration or agent policy — projecting canonical state into agent locations, checking whether a projected file has been hand-edited, inspecting substrate tooling, or deciding where a change belongs. Trigger on ms project, ms diff, ms status, ms unproject, canonical/, adapters/, or questions about which file is the source of truth.
---

# machine-state

Configuration and agent policy for this workstation live in the `machine-state` repository. It is
canonical; the files agents read elsewhere are one-way projections of it.

## Deciding where a change belongs

Ask who owns the file before editing it.

| Owner | Examples | Rule |
| --- | --- | --- |
| canonical | `canonical/**`, `SUBSTRATE.md` | edit freely, then `ms project` |
| projected | any spliced region, linked skill dirs | never edit; edit canonical instead |
| vendor | files an installer owns, e.g. anything `bd setup` writes | leave to that tool |

Editing a projection is not wrong so much as futile: `ms diff` reports it and `ms project`
overwrites it.

## Commands

```bash
ms status      # every target and tool, with the check each one declares
ms diff        # exits non-zero if any projection has drifted from canonical
ms project     # realise canonical into every declared target; idempotent
ms unproject   # remove every projection this repo owns
```

`ms project` refuses to overwrite a file it has no record of creating, so pointing an adapter at
an existing hand-written file reports a conflict rather than destroying it.

## Extending

Adding an agent is adding `adapters/<agent>.toml`. Adding managed config is adding a directory
under `canonical/`. Adding a tool is adding `canonical/tooling/<tool>.md`. None of these should
require changing `bin/ms`. See `SUBSTRATE.md` for the full contract.
