Part of the factory skill: SKILL.md's rules apply here too. Moved out of SKILL.md unchanged, so it is read only when needed; a **Section** is one of SKILL.md.

## Config keys

- `template` and `archetype`: the factory version setup ran with and the repo's archetype (A–E,
  see `setup.md`); information only.
- `forge`: `github`, `gitlab` or `none`, the forge of the delivery remote; it picks `gh` or `glab`
  for PRs/MRs, pipelines and issues. Missing → `github` for the CI calls.
- `port_base` (default 5100): job `NNN` gets builder port `port_base + 10·NNN`, the ux/ui/audit
  reviewers `+1`/`+2`/`+3` (see Constants).
- `reviewers` is the full-review set. Name `x` is agent `factory-reviewer-x`. Each round
  `.factory/job` keeps only those whose paths the diff touches (see **Reviewers**);
  `reviewer_paths` (optional) sets those paths per reviewer.
- `issues` is `null` when issue mode is off. Which issues `/factory next` considers: every
  open issue whose author is in `allowed_authors`, except those with a label in
  `issues.skip_labels` (default `blocked`, `wontfix`, `factory:in-progress`). `issues.label`
  is optional: when set, only issues with that label count (older configs have
  `factory:ready`; leave it out to take all). Labels that steer a single issue:
  `factory:docs|light|full` (the effort, wins over the triage), the effort labels of
  `effort.labels` (default: `easy` and `good first issue` → `light` with a sonnet builder; they
  win over the triage and over `/factory issue`'s default `full`), `factory:solo` (never
  bundled), `factory:bundle` (a bundle issue: one job for it and its members, see **Bundle
  issues**). `limits.bundle_max` (default 4) is the most issues in one `docs`/`light` job
  (a `full` job takes at most `limits.full_bundle_max`, default 2). `issues.link` is the keyword that
  references the issue in PR/MR bodies: `Closes` (closes it on merge) or `Refs` (link
  only; required when merge commits are mirrored to another forge, where `Closes #N`
  would close an unrelated issue with the same number). Missing → `Closes`.
  `issues.close_on_merge`: close the job's issue once its PR/MR is confirmed merged (see
  **Closing issues**). Missing → `true`; `false` leaves closing to a human.
- `delivery.mode`: `local` (merge into `base` locally), `push` (push the job branch) or
  `pr` (push + open a PR/MR). Missing → `local`.
- `delivery.remote`: the remote job branches are pushed to and PRs/MRs are opened on. Missing →
  `origin`.
- `delivery.draft`: open the PR/MR as a draft. Missing → `true`.
- `delivery.auto_merge`: in `pr` mode, switch on the forge's auto-merge after opening the
  PR/MR, so the forge merges it itself once the required checks pass. Missing → `false`.
  Only meaningful with `draft: false` (a draft cannot merge); with both set, ignore the
  auto-merge and say so. It is the switch, not the decision: `.factory/job` gates every
  delivery (`AUTO-MERGE: yes|no` in `ACTION: deliver`, see **Delivery**).
- `delivery.auto_merge_held` (optional, default `false`): `true` = auto-merge on every PR/MR, also
  for a job the factory holds (hold-class files or `auto_merge_never`, an approver `HOLD:`, an audit
  deviation, `/factory approve`, a resolved sync conflict). The precheck still names the hold
  (`AUTO-MERGE: held: …`) and delivery puts it into the PR/MR description; precheck issues
  (secrets, failing validation) still block. See **Delivery**.
- `effort` (optional): `effort.labels` maps an issue label to a mode, or to
  `{"mode": "light", "builder": "sonnet"}` (the builder's model while the job stays `light`/`docs`).
  Missing → `easy` and `good first issue` map to light with a sonnet builder; `{}` → no labels
  beyond `factory:*`. The floor still lifts such a job to `full` (and drops the pin) when its diff
  touches security/auth, schema, dependencies, CI or `auto_merge_never` paths.
- `delivery.auto_merge_never` (optional): extra globs that always keep a job off auto-merge,
  for paths CI cannot vouch for: put the personal-data paths here. The defaults already
  cover CI/pipeline config, dependencies and lockfiles, containers and deploy config,
  schema and migrations, and auth.
- `limits` (optional, all keys optional): `active_jobs` = how many jobs of this repo may be
  in `spec`/`build`/`review`/`approve`/`deliver` at once (default 3, see Constants);
  `open_prs` = how many jobs may sit at `pr-open` before new ones wait (default 5, `0` =
  no limit: every merged PR/MR makes the others conflict, so a long CI queue should slow
  intake); `guard: false` switches off `.factory/guard`; `docs_globs` = paths that count
  as documentation for `--docs` (default `*.md`, `*.mdx`, `*.rst`, `*.adoc`,
  `docs/**`, `LICENSE*`, `mkdocs.yml`);
  `heavy_slots`, `cpu_budget`, `cpu_max` and `load_max` set the machine-wide limits of
  `.factory/heavy` (defaults: at most max(2, cores − 1) commands at once, weights together at most
  the cores, CPU not above 90%, load average ignored; before v0.19.0: cores/2 and 75%). See **Resources**.
- `acceptance_tests` (optional): hidden acceptance tests. Missing → on for `full` jobs only;
  `true` → `full` and `light`; `false` → off; or a list of modes. See `commands/acceptance-tests.md`.
- `routing` (optional): model and effort per spawn, and the builder's escalation ladder.
  `routing.agents.<agent>.model|effort` (a value, or one per job mode such as
  `{"light": "low"}`) wins over the script's choice and the agent's frontmatter;
  `routing.escalate: false` switches the ladder off; `routing.cap` (default
  `{"model": "opus", "effort": "xhigh"}`) is its top; `routing.blocked_retries` (default 1)
  is how often a `BUILD: BLOCKED` is retried one step up in the same round; `routing.security_floor`
  and `routing.security_floor_globs` set when security leaves sonnet. See **Routing**.
- `validate` (optional): where the round's full validation runs. `{"mode": "local"}` (default):
  repo.md's Validate commands through `heavy` on this machine. `{"mode": "ci", "open_pr": true|false}`
  (setup writes it when `.factory/forgecheck` finds CI that runs the suite for
  a job branch and delivery is `pr`): the validation step pushes the job branch, opens the PR/MR when
  `open_pr` (always a draft until delivery, since v0.17.0: `validate.draft` is deprecated and ignored,
  an open ready one is made a draft again; delivery marks it ready per `delivery.draft`), and waits for that commit's pipeline on
  the forge, without a heavy slot; a job delivered `local`/`push` still validates locally. Optional
  `poll_s` (30), `no_pipeline_min` (10: no pipeline for the pushed commit by then = `VALIDATE: ERROR`),
  `timeout_min` (180).
- `ci` (optional): `{"preview_cleanup_job": "<job name>", "preview_jobs": ["<glob>", …]}`. A failed
  preview deploy (a job matching `preview_jobs`, default `*preview*`, whose log shows a Helm upgrade
  failure, a failed pre-upgrade hook job or `timed out waiting for the condition`) counts as
  infrastructure; before its one retry the factory plays (manual) or retries `preview_cleanup_job` in the
  same pipeline (GitLab only) and waits for it (`FACTORY_CI_CLEANUP_WAIT`, 420 s), so the deploy starts
  on a fresh preview namespace. Without the key nothing changes. prompt-library:
  `{"preview_cleanup_job": "kubernetes:deploy-preview:cleanup"}`.
- `ui_review` (optional, default `auto`) and `ui_page_globs`: the form of the ux/ui reviews, see
  **Reviewers**.
- `worktree_seed` (optional, default `true`): a new job worktree gets the main checkout's
  `node_modules` (next to a `package-lock.json`/`npm-shrinkwrap.json`) and `.venv` (next to a
  `uv.lock`) as hardlinks (`cp -al`; a plain copy across filesystems; never a symlink) when that
  lockfile is identical to the main checkout's; otherwise nothing and the normal install runs.
  The builder's prompt then says `Dependencies seeded: …`. `false` switches it off.
- `adopt_conflicting` (optional, default `false`): `true` lets `.factory/job adoptable` adopt every
  open PR/MR by an allowed author in this repo that has a merge conflict and no job (see
  `/factory adopt`); `false` only lists them as adoptable.
- `house_style` (optional, no default; set by whoever runs the factory, never by setup):
  `{"skills": ["<skill>", …]}`. The builder and the ux/ui reviewers get a `House style:`
  line naming these skills; they load and follow them for UI work, over the vendored
  `frontend-design` skill (which the builder otherwise reads for new UI, below the repo's
  own design system: not preloaded, but named on a `UI work:` line of the builder's prompt
  when the diff or spec.md touches a UI path). A skill the session does not have is reported, not fatal.
- `docs` (optional, no default: nothing is checked without it): `{"rules": [{"code": [globs],
  "docs": [globs], "why": "<what the docs describe>"}]}`. When a job's diff touches a rule's `code`
  globs and none of its `docs` globs, `.factory/precheck` reports the issue `DOCS: missing update
  for <why> (<files>)`: a precheck issue, so auto-merge stays off (also with `auto_merge_held`) and
  the approver sends it back (REWORK). It passes once the docs change, or when the job's text
  (round-N/build.md, decision.md or pr-body.md) has a line `Docs: not needed: <reason>`; a line
  that names a rule's `why` (`Docs: not needed (config keys): <reason>`) covers only that rule, one
  without covers every rule. The precheck notes `DOCS: not needed for <why>: <reason>` and
  `--pr-body` quotes the line in the PR/MR. Globs: `**` spans directories, `*` stays within one,
  a glob without `/` matches the file name anywhere. `/factory setup` proposes rules from the
  repo layout and writes them after the user's yes.
- `.factory/repo.md` holds the repo facts the agents need (setup, dev server,
  validation, CI). You do not need to read it; the agents do.
