**In this harness:** beads context loads through native hooks — `bd setup codex` registered
`SessionStart`, `UserPromptSubmit`, `PreCompact` and `PostCompact` in `.codex/hooks.json`, and
`.codex/config.toml` sets `features.hooks = true`. Inspect or toggle them with `/hooks`; run
`bd prime` by hand only if that context is missing or stale. The beads skill is at
`.agents/skills/beads/SKILL.md`.
