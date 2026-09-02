# derived/

Content produced by a tool in this repository from canonical declarations.

Not canonical: no human authored it, and editing it here is pointless because the next run of its
producer will overwrite it. Not projected either: `bin/ms` never writes into this directory, it only
reads from it.

| Path | Produced by | Verified by |
| --- | --- | --- |
| `hypr/bindings.lua` | `cap render` from `canonical/bindings/` | `cap check` |

**Committed deliberately.** A derived file could be regenerated on demand, but then `ms diff` could
not answer "does the machine match the repository" without first running every producer, and a
projection would stop being auditable from the repository alone. Checked in, the chain from
declaration to live file is readable in one place and in one commit.

See `SUBSTRATE.md` §2 for the ownership class and the rule about what may be an adapter source.
