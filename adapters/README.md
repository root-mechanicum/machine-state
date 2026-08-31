# adapters/ — manifest schema

One `<agent>.toml` per resident agent. An adapter is a **manifest, never content**: it declares
where an agent expects things and which canonical sources fill them. Adding an agent is adding a
file here — it must never require editing `bin/ms`.

No conditionals, no templating language, no per-agent code paths. If an adapter needs logic, the
design is wrong. See `SUBSTRATE.md` §3.

## Keys

Three keys on every target:

| Key | Type | Meaning |
| --- | --- | --- |
| `kind` | `"render"` \| `"link"` \| `"splice"` | which projection mechanism |
| `path` | string | destination; repo-relative, or absolute with `~` expanded |
| `sources` | list of strings | canonical paths, repo-relative |

Two more, on `splice` targets only:

| Key | Type | Meaning |
| --- | --- | --- |
| `marker` | string | names our region, e.g. `MACHINE-STATE POLICY` |
| `comment` | `"html"` \| `"hash"` \| `"dash"` | how to wrap the marker for this file format |

`comment` is explicit rather than inferred from the file extension. Guessing a comment syntax
from a filename would be exactly the content-awareness the projector is forbidden to have. The
projector composes the delimiters from `marker` and `comment` alone:

| `comment` | BEGIN line | for |
| --- | --- | --- |
| `html` | `<!-- BEGIN MACHINE-STATE POLICY -->` | Markdown, HTML |
| `hash` | `# BEGIN MACHINE-STATE POLICY` | TOML, YAML, shell, `.gitignore` |
| `dash` | `-- BEGIN MACHINE-STATE POLICY` | Lua |

## Mechanisms

- **`render`** — concatenate `sources` in order and write the whole file. Only for files we
  create. **Never point `render` at a vendor-owned file**; see the corollary in `SUBSTRATE.md` §4.
- **`link`** — symlink a single canonical directory at `path`. `sources` holds exactly one entry.
  Link the specific subdirectory, never a shared parent.
- **`splice`** — replace the bytes between our two marker lines, preserving everything outside.
  This is how we co-own a file with a vendor installer. If the markers are absent, the region is
  appended at end of file.

## Worked example

```toml
# adapters/example.toml — illustration only; not a live adapter.

# render: a file we own entirely.
[[target]]
kind    = "render"
path    = "./POLICY.md"
sources = [
  "canonical/policy/00-generated.md",
  "canonical/policy/10-identity.md",
]

# link: one skill directory, not the skills/ container.
[[target]]
kind    = "link"
path    = "~/.claude/skills/machine-state"
sources = ["canonical/skills/machine-state"]

# splice: co-owning a vendor file. bd owns its own marked block in the
# same file; we own only ours.
[[target]]
kind    = "splice"
path    = "./CLAUDE.md"
sources = [
  "canonical/policy/10-identity.md",
  "canonical/policy/agents/claude-harness.md",
]
marker  = "MACHINE-STATE POLICY"
comment = "html"
```

## Invariants

- Every `sources` path must exist under `canonical/`.
- No target may resolve outside the repository or the agent's own home directory.
- No target may be a vendor-owned path under `kind = "render"` or `"link"`. Vendor files are
  reachable by `splice` only. The ownership table is in `SUBSTRATE.md` §2.
