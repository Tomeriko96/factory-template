# factory-template

Generieke software-factory voor Claude Code (spec → build → parallelle reviews →
approve → merge/escalate), plus de meta-prompt die hem per repo tailort.

- `SCAFFOLD_PROMPT.md` — plak in een repo, op opus. Forge-bewust (GitHub/GitLab),
  privacy-regel voor alle archetypes, `--light`-modus, lokale-merge-regel,
  standaard smoke-test.

## Nog te doen (template-inhoud)

`SCAFFOLD_PROMPT.md` verwacht deze files, die hier nog gemaakt moeten worden:

```text
.claude/skills/factory/SKILL.md
.claude/agents/{spec-writer,builder,approver}.md
.claude/agents/reviewer-{security,code,ux,ui}.md
factory/{backlog.md,dashboard.html,factory-watch}
```

Tag elke stabiele stand (`git tag v0.1.0`): de scaffold schrijft
`git describe --tags --always` als template-versie in `factory/SETUP.md`.
