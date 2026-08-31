**In this harness:** beads context is injected automatically — `.claude/settings.json` runs
`bd prime` on SessionStart, so there is no need to run it by hand. The harness's own ephemeral
task tools are `TodoWrite` and `TaskCreate`; durable work belongs in beads instead. Shared skills
are linked into `~/.claude/skills/`.
