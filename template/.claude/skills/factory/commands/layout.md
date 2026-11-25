Part of the factory skill: SKILL.md's rules apply here too. Moved out of SKILL.md unchanged, so it is read only when needed; a **Section** is one of SKILL.md.

## Layout

```text
<repo>/.factory/                         (git-excluded)
  config.json  repo.md  backlog.md  job  shoot  serve  heavy  guard  precheck  rereview  watch  ci  forgecheck  VERSION
  cache/                                 (.factory/heavy: passing validation results per tree;
                                          .factory/ci: CI/CD state per job as ci-<job-id>.json)
  run/triage/                            (`/factory next`: issues.json, plan.json, groups.json)
  metrics.jsonl                          (.factory/job: one line per spawn and per verdict; `job report`)
  jobs/<job-id>/
    job.json                             (written only by .factory/job)
    spec.md
    acceptance.md, acceptance/            (factory-acceptance-writer: hidden tests; only the audit uses them)
    acceptance-notes.md                   (audit: wrong assumptions of failed hidden tests; later acceptance writers read it)
    round-N/build.md
    round-N/build-blocked-K.md            (a BUILD: BLOCKED that was retried one step up)
    round-N/review-<name>.md
    round-N/shots/<name>/                (ui/ux screenshots, made with .factory/shoot)
    round-N/decision.md                  (an approver's REWORK, moved here by the script)
    round-N/validate.md, validate.json   (.factory/precheck --validate: the round's one full-suite run,
                                         local or on the forge's CI: validate.mode)
    precheck.md                          (.factory/precheck, before the approver)
    decision.md                          (approver: the current decision)
    sync-N/build.md, review-code.md      (/factory sync: base merged into the branch)
    rework.md                            (only after /factory rework)
<repo>/../<repo>-worktrees/<job-id>/     (git worktree, branch factory/<job-id>)
```
