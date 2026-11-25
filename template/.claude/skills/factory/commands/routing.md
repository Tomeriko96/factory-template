Part of the factory skill: SKILL.md's rules apply here too. Moved out of SKILL.md unchanged, so it is read only when needed; a **Section** is one of SKILL.md.

## Routing

Every spawn block carries `MODEL:` and `EFFORT:` (see **Job state**). The defaults are in the
agents' frontmatter (`model:`, `effort:`): every reviewer except the audit (code, security,
llm-safety, privacy, data-quality, methodology, ux, ui), the spec-writer and the approver on
sonnet at medium; the audit on opus at high; the builder on opus at high in `full`, medium in
`light` and low in `docs` jobs (the script sets that per mode). **Security floor:** when the
diff reaches a floor class (CI/pipeline config, dependencies, containers/deploy, schema or
migrations, auth, `delivery.auto_merge_never`) or a secrets-handling path (`*secret*`,
`*credential*`, `*crypt*`, `*password*`, `*token*`, `*vault*`, `*.sops.*`, `*keyring*`, plus
`routing.security_floor_globs`), the security reviewer runs at `routing.security_floor`
(default `{"model": "opus", "effort": "high"}`; `false` switches it off) and its block shows
`FLOOR: <model>/<effort> (why)`. The floor only raises: a `routing.agents` setting above it stays. **Escalation ladder:** after a round with blocking
reviews, a failed full validation or an approver REWORK, the next builder goes one step up:
effort first, then the model (sonnet → opus), up to `routing.cap` (opus/xhigh). A
`BUILD: BLOCKED` is retried once in the same round one step up (`round-N/build-blocked-K.md`
keeps the old file); at the cap, or on the second block, the job goes to `needs-human` as
before. The block then shows `ESCALATED: +k steps (why)`. If the Agent tool in this session
has no `effort` parameter, only the frontmatter effort applies and the ladder raises effort
in name only (the metrics still record it); the model step works either way.
`.factory/metrics.jsonl` records every spawn (model, effort, escalation) and verdict;
`.factory/job report` sums it up.
