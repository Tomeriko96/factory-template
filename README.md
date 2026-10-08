# factory-template

Generieke software-factory voor Claude Code (spec → build → parallelle reviews →
approve → merge/escalate), plus de meta-prompt die hem per repo tailort.

- `SCAFFOLD_PROMPT.md` — plak in een repo, op opus. Forge-bewust (GitHub/GitLab),
  privacy-regel voor alle archetypes, `--light`-modus, lokale-merge-regel,
  standaard smoke-test.

## Inhoud

```text
.claude/skills/factory/SKILL.md     orchestrator-loop (basis: 4 reviewers, MAX_ROUNDS 3, MAX_RESUMES 2)
.claude/agents/                     spec-writer, builder, approver, reviewer-{security,code,ux,ui}
factory/{backlog.md,factory-watch}   # factory-watch = CLI-board, --tmux voor split-pane
```

De basis bevat bewust **niet**: `/factory resume`, timestamps in `job.json`, taalregel,
`--light`, en de lokale-merge-regel. Die voegt `SCAFFOLD_PROMPT.md` per repo toe
(bijlagen A, B, D, E), samen met de repo-specifieke reviewers (bijlage C).

## Beperkingen

Deze template is geschreven op basis van de loop-beschrijving, niet getest met een
echte `/factory`-run. Draai de smoke-test uit Fase 4 van de scaffold in een eerste repo
en verwerk bevindingen hier terug. Tag stabiele standen (`git tag v0.1.0`): de
scaffold schrijft `git describe --tags --always` als template-versie in
`factory/SETUP.md`.
