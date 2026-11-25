Part of the factory skill: SKILL.md's rules apply here too. Moved out of SKILL.md unchanged, so it is read only when needed; a **Section** is one of SKILL.md.

### Triage
`/factory next` does not take issues one by one. `.factory/job triage prepare` removes what must not
start, the **factory-triage** agent (pinned on sonnet, no Bash, reads only the issue file and the repo)
decides per issue its effort and which small related issues share one job, and `triage plan`
checks that plan: at most `bundle_max` issues per `docs`/`light` job and `full_bundle_max` (default 2) per `full` job, labels
`factory:docs|light|full` over the agent, `factory:solo` alone, issues the agent forgot become their own
`full` job. Judgement sits in the agent and the rules in the script, so the result does not depend on
the model or effort of this session. A `light` job that turns out to touch CI, dependencies,
containers, schema or auth (or `delivery.auto_merge_never`) is lifted to `full` by the script after the
build (a NOTE tells you); a `docs` job that touches code continues as `light`.
