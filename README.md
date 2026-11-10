# factory-template

A local software factory for Claude Code: spec → build → parallel reviews → approve →
local merge or escalate. You install it into any repo with one command. It lives only
in that clone and is never committed.

## Use

```bash
git clone https://github.com/Tomeriko96/factory-template.git && cd factory-template
./install --link        # once: puts `factory-init` on PATH (~/.local/bin symlink)

cd /path/to/repo
factory-init            # install (or update) + start `claude --model opus "/factory setup"`
```

Then, in a Claude Code session in that repo (any model and effort: the skill sets its own effort,
the judgement sits in pinned agents):

```text
/factory <feature>              full loop
/factory --light <feature>      small change: code review (+ security/privacy if touched)
/factory --docs <feature>       documentation only: one carry-out step, no reviewers
/factory … --local <feature>    this job merges locally whatever delivery.mode says
/factory issue <nr> [<nr>…]    from one issue (trusted authors only); several = one bundle job;
                                label factory:docs|light|full sets the effort
/factory next [--yes]           triage ALL open, non-blocked issues of trusted authors: bundles small related
                                ones into one job, picks docs/light/full per job, shows the plan, then starts
                                (without config.issues: the first item of .factory/backlog.md)
/factory approve|rework|resume|drop|deliver <id>
/factory status                 or live: .factory/watch [--tmux]   (factory-watch: all repos)
```

## The board

`.factory/watch` is an interactive board in the terminal (plain text in a pipe or with
`--once`, JSON with `--json`). Jobs are grouped by what you need to do: **NEEDS YOU** (the
reason and the command to type), **RUNNING** (which agent runs, review progress, the `heavy`
command in its worktree, for how long), **QUEUED**, **OPEN PRs** (age since opened, CI with
only the failing checks named, mergeability) and a one-line **DONE** count. On terminals
of 140+ columns the sections are columns; narrower, a list of cards.

Keys: `j`/`k` move, `h`/`l` change column, `enter` opens a job (beside the board when
wide: timeline with durations, reviewer × round table, the first line of every agent file,
CI by status, the next command), `a` finished jobs, `/` filter, `c` copies the selected job's
next command (OSC 52, also through tmux), `v` cards or one line per job, `R` this repo or
all repos, `?` help, `q` quit. It only reads; `.factory/job` is the only writer.

`install` keeps a list of the repos it installed into (`~/.local/state/factory/repos`), and
`install --link` also puts `factory-watch` on PATH: one board for all of them, with the repo
in front of each job.

`factory-init --remove` takes it out again. It refuses while a job is not at rest
(`needs-human` counts as unfinished: approve, rework or park it first), stops the servers
`serve` started, removes clean job worktrees (worktrees with uncommitted changes and local
`factory/*` branches are listed, never deleted), and keeps your data (`.factory/config.json`,
`repo.md`, `backlog.md`, `jobs/`, still git-excluded) so a re-install continues where it
was; `factory-init --remove --purge` deletes that data too.
`factory-init --no-setup` installs or updates without starting Claude. `factory-init`
is just a symlink to `./install`, so updating the factory everywhere = `git pull` here
and re-run `factory-init` in each repo.

## Local-only

`install` copies `template/` into the repo and adds these paths to
`.git/info/exclude` (not `.gitignore`, so not even that is committed):

```text
.claude/skills/factory/      SKILL.md (orchestrator) + setup.md (/factory setup)
.claude/agents/factory-*.md  triage, spec-writer, builder, approver, reviewer-{security,code,ux,ui,audit,
                             privacy,methodology,llm-safety,data-quality}
.factory/                    config.json + repo.md (written by setup), backlog.md, job, shoot, serve,
                             heavy, guard, precheck, rereview, watch, ci, forgecheck, VERSION, jobs/, run/, cache/
.claude/settings.local.json  one PreToolUse hook entry (guard), merged into your file if you have one
```

Job worktrees go to `../<repo>-worktrees/<job-id>`, outside the repo. Excluded files
are not checked out there, so nothing from the factory can end up in a job commit.

## Resources

A job is a builder plus up to six reviewers, and several jobs (in several repos) can run on
the same container. Unchecked, that ran at load 20–33 on 8 cores: tests timed out, got
rerun and were reported as flaky, and rounds were spent on load, not on bugs. Four guards:

| Guard | What it does |
|---|---|
| `limits.active_jobs` (default 3) | Jobs of one repo in `spec`/`build`/`review`/`approve` at once. More are `queued` and start when one leaves those stages. |
| `.factory/heavy -- <cmd>` | Every test, build, lint and install of every agent goes through it. Each command has a weight (the cores it may use: 3 for Node, browser and build tools, 1 for pytest and the like); the weights running at once on the whole machine (all repos, all sessions) stay within 75% of the cores, and the CPU must not be busier than 90%, measured over a second, not from the lagging load average. It runs at low priority and sets `FACTORY_CPUS` to the weight. `heavy status` shows who holds capacity. |
| `heavy --background` / `heavy wait` | For commands that may outlast a tool call (a queue, a long suite): `--background` returns a ticket at once, `heavy wait <ticket>` blocks up to 9 minutes and prints the result and exit code (124 = call again). Foreground calls give up after 9 minutes with exit 75 and say so, so a queue can no longer eat an agent's tool call. |
| `heavy --cache -- <cmd>` | Validation runs once per commit: a passing run is recorded for the exact tree (clean tree, same command, same worktree, same behaviour-changing env vars such as `CI`/`*_ENV`/`MODE` and `.env*` files; extend with `limits.cache_env`) and the reviewers, audit and approver get an instant `CACHE HIT`. Failures, dirty trees and new commits run for real. |
| `.factory/guard` | A `PreToolUse` hook in every factory agent: a test, build, install, lint, type-check or browser command that is not run through `heavy` is refused with the fix in the message, so the limits do not depend on the agent remembering. It looks through `&&`/`;`/pipes, `$(…)`, loops, `bash -c`/`-lc`, wrappers (`env`, `timeout`, `xargs`, …) and runners (`uv run`, `npx`, `pnpm exec`, `python -m`, …), and knows npm-family script names (`test:*`, `typecheck`, `e2e`), `make -C`/`-j`, Python, Node, JVM, .NET, Go, Rust and R (`Rscript -e 'devtools::test()'`, `R CMD check`); `--version`/`--help` always pass. Needs a trusted workspace (Claude Code runs project-agent hooks only after the trust dialog, in bypass mode too); `limits.guard: false` turns it off. `install` also adds a `--subagents-only` variant to `.claude/settings.local.json`, so ad-hoc `general-purpose` subagents are covered while your own session stays unrestricted. |
| `limits.open_prs` (default 5) | Jobs at `pr-open` before new ones wait: every merge makes the other open PRs conflict, and CI is the slow part (median 3-14 h from PR to merge). `watch` and `status` show open PRs, the oldest and failing pipelines; the factory never retries a pipeline. `watch` shows one live CI/CD line per `pr-open` job (stages/jobs via `.factory/ci`, GitHub Actions + GitLab CI); `watch <id>` shows the full table, `--no-ci` hides it. |
| `heavy gate` | The orchestrator waits (max 10 min, then continues with a warning) while the CPU is above 90% before it spawns a spec-writer, builder or review wave. |

Defaults need no configuration; override with `limits` in `config.json`
(`active_jobs`, `open_prs`, `heavy_slots`, `cpu_budget`, `cpu_max`, `load_max`) or the env
vars `FACTORY_HEAVY_SLOTS`, `FACTORY_CPU_BUDGET`, `FACTORY_CPU_MAX`, `FACTORY_LOAD_MAX`,
`FACTORY_LOCK_DIR`. `.factory/watch` shows CPU, the `heavy` cores in use and active jobs
against the cap. The audit also has bounds: at most 3 mutation checks (only for criteria that add
behaviour), a suspect file at most twice, base comparisons only for the claim concerned, about 30 tool calls in total.

## Less work per job

- **Docs mode:** `/factory --docs` has no spec-writer, reviewers or approver. A sonnet builder
  makes the change and writes the PR text; `.factory/precheck` checks mechanically that the
  diff only touches documentation (`limits.docs_globs`), has no secrets and is small. If it
  touches anything else the job continues as `--light`.
- **ux/ui only for UI diffs:** they start a server and a browser per round, and gave
  `CHANGES` in 0 of 65 reviews. They now run only when the diff matches the repo's "UI paths"
  (and in round 2+ only if they objected or UI files changed).
- **Cheaper approver:** it was MERGE 37 times out of 37. `precheck` does the mechanical part
  (all PASS, audit table has no ❌/⏭️, no secrets or factory files, diff size); the approver
  now runs on sonnet to judge and write the PR body, and gets opus only when the precheck
  reports issues or it is round 2+.
- **Already done?** Before a job from an issue starts, the factory looks for an open PR/MR,
  a branch or a base commit for that issue (`--force` overrides), and the spec-writer
  can answer `SPEC: ALREADY-DONE`. Two earlier jobs ran for hours before the base turned out
  to contain the same fix.
- **Round 2+ re-runs only what is needed:** two thirds of the later-round reviews came from
  reviewers who had already passed. `.factory/rereview` picks the set: reviewers that gave
  `CHANGES`, plus `audit` and `code`; everyone again only if the builder changed something
  beyond what the findings pointed at. The others keep their earlier PASS (the precheck
  reads each reviewer's latest verdict).
- **The audit is the pace-setter** (median 11 min against 1-2 for the other reviewers), so it
  has a call budget, starts from the cached validation, installs nothing in temporary
  worktrees, and marks what it cannot measure in time as ⏭️ instead of digging on.
- **Cheap orchestrator:** the skill sets `effort: medium` for its own turns (it was producing
  650-970 output tokens per turn, almost all reasoning, for a bookkeeping role), so your session may
  stay on any model and effort. It reports one line per event, and after about 10 delivered jobs it tells you to `/clear` and
  continue with `/factory status` (state is on disk). It never spawns `general-purpose`
  agents to run tests.
- **Few screenshots:** ux/ui take at most 6 paths at 2 widths, light only unless colours
  changed; `shoot` refuses more than 12 shots per call.
- **No size limits as acceptance criteria:** "diff under N lines" is guidance, never blocking.

## Delivery

After the approver says MERGE, `config.delivery.mode` decides:

| Mode | What happens | End stage |
|---|---|---|
| `local` | `git merge --no-ff` into the base branch, in this clone | `merged` |
| `push` | push `factory/<id>` to the remote | `pushed` |
| `pr` (recommended) | push + open a PR/MR (draft by default; `delivery.draft`) with the approver's body: summary, verified acceptance criteria, validation, leftovers, `Closes #<nr>` (or `Refs #<nr>` for mirrored repos, `issues.link`) | `pr-open` |

The factory only ever pushes `factory/*` branches: never the base branch, never
`--force`. It never merges, approves or closes a PR/MR. The one exception is opt-in:
with `delivery.draft: false` and `delivery.auto_merge: true` it switches on the forge's
auto-merge after opening the PR/MR (GitLab: merge when pipeline succeeds; GitHub: `gh pr
merge --auto`), so the forge merges once its own checks pass. It never merges directly.

`auto_merge` is the switch; `.factory/job` is the gate. Every delivery prints `AUTO-MERGE: yes`
or `AUTO-MERGE: no (<reasons>)`, and `no` means a ready PR/MR that a human merges (and auto-merge
switched off if a rework had left it on). `yes` needs all of: an approver `MERGE` (or a clean
`--docs` precheck, never `/factory approve`); precheck without issues and without an audit
deviation (⚠️); no file in CI/pipeline config, dependencies/lockfiles, containers/deploy config,
schema/migrations or auth, nor in `delivery.auto_merge_never` (your globs, e.g. personal-data
paths); no `HOLD: <reason>` line from the approver (breaking change, public API, user-visible
behaviour); and no sync merge on the branch (an agent resolved a conflict, one reviewer checked
it: a human merges that). `/factory setup` runs `.factory/forgecheck`: does CI run on a draft
PR/MR (if not, use `draft: false`), and does the forge require checks before a merge (if not,
auto-merge has nothing to wait for and is not switched on).

Once the forge confirms a job's PR/MR is merged, the factory closes the issue the job came
from (`issues.close_on_merge`, default `true`; `false` leaves that to you), and no other
one. This also catches up older merged jobs on `status`/`sync`. Review comments go back in
with `/factory rework <id> "<comments>"`; the next approved round pushes to the same branch,
so the PR/MR updates.

`/factory sync [<id>]` keeps open PRs/MRs mergeable: it asks the forge whether each still
merges into the base branch (also at the end of delivery, on every `status` and whenever a
merge is noticed, since each merge can make the other open PRs conflict), and on a
conflict has a sonnet builder merge the base into the job branch (a merge commit, never a
rebase or force-push), runs the validation, lets the code reviewer check the merge and
pushes. A conflict that needs a decision (the base already fixes the same thing, both
sides change the same behaviour, validation fails) is never resolved by picking a side:
the job goes to `needs-human` with the reason. At most `MAX_SYNCS` (3) times per job.
`/loop 10m /factory sync` watches continuously.

`install` refuses if one of those paths is tracked in the repo, and it verifies
afterwards with `git check-ignore` that git really ignores them.

## Design

- **Generic files + config.** SKILL.md and the agents are identical in every repo.
  What differs per repo is data: `.factory/config.json` (archetype, forge, port base,
  reviewer set, issue mode) and `.factory/repo.md` (setup, validation, dev server,
  conventions). Updating = re-running `factory-init`; config, backlog and jobs are kept.
- **One file per agent.** Each agent writes one markdown file whose first line is the
  verdict. The orchestrator reads only that line, and all state is on disk, so
  `resume` works.
- **State in code, not in the prompt.** `.factory/job` is the only writer of `job.json`:
  a reconciler that reads the agents' files and applies the state machine under a lock
  (job ids, worktrees, rounds and their budget, verdicts, precheck, REWORK, resumes,
  queue and capacity, delivery bookkeeping, cleanup). `job next <id>` prints the next
  action, including the exact agent prompts; the orchestrator spawns, chooses reviewers
  and talks to the forge, and never edits `job.json`. Before this, the orchestrator
  rewrote `job.json` by hand and kept round budgets and capacity in its head, which left
  gaps (unbounded REWORK loops, a queued `--docs` job losing its mode, stale decisions).
- **Reviews stay in the container.** `reviewer-audit` re-measures every claim and
  acceptance criterion (claim → command → measurement table, explicit withdrawals of
  measurement artefacts). ui/ux look at the running app via headless Chromium
  (`.factory/shoot`: screenshots + overflow, a11y and console checks). Servers are
  started and stopped only through `.factory/serve` (own process group per port,
  refuses a busy port, waits for readiness), so parallel reviewers never test or kill
  each other's server.
- **Severity.** Findings are `[blocking]` or `[non-blocking]`; only blocking findings
  trigger another round. Non-blocking ones end up as Leftovers in `decision.md`.
- **Everything in English.** Artifacts, reports and commit messages.

## Issues: triage, bundles and effort

With `config.issues` set, `/factory next` considers **every open issue** of `allowed_authors` unless it has a
label in `issues.skip_labels` (default `blocked`, `wontfix`, `factory:in-progress`); no `factory:ready` label is
needed (an old config that still has `issues.label` keeps requiring it; remove the key to take all). Steps:

1. `.factory/job triage prepare` filters mechanically: author, skip labels, issues that already have a job,
   an open PR/MR, a remote branch or a commit referencing them.
2. The **factory-triage** agent (sonnet, medium, no Bash) is the *issue audit*: per issue the effort
   (`docs`: documentation only, no spec/reviewers/approver; `light`: small and local, code review only; `full`:
   everything else), issues it should skip (questions, epics, unclear), and which small related issues belong in
   one job.
3. `.factory/job triage plan` validates that plan: at most `limits.bundle_max` (default 4) issues in a
   `docs`/`light` job, 2 in a `full` job, `factory:docs|light|full` labels beat the agent, `factory:solo` is never
   bundled, issues the agent forgot become their own `full` job. You see the groups and agree (or `--yes`).
4. `triage start <k>` starts each group. A bundle is one job with `"issues": [..]`: one spec with criteria
   per issue, one PR with `Closes #a, Closes #b`, and all issues are closed after the merge.

The effort has a **floor**: a `light` job whose diff touches CI/pipeline config, dependencies, containers,
schema/migrations or auth (or `delivery.auto_merge_never`) becomes `full` automatically; a `docs` job that touches
code continues as `light`.

## Status

Install/update/remove, the git-exclusion and the loading of the skill and agents by
Claude Code are tested. `shoot` and `watch` are tested. The `/factory` loop has run for
about 40 jobs in two repos (onderwijsdata-chat, prompt-library); feed findings back here
and tag stable versions (`git tag v0.x.y`), because `install` records
`git describe` in `.factory/VERSION`.

Tests: `bash tests/job_test.sh`, `python3 -I tests/guard_test.py`, `python3 -I tests/prompts_test.py`,
`python3 -I tests/forgecheck_test.py` (CI on drafts, required checks, with a fake `gh`/`glab`),
`python3 -I tests/watch_test.py` (the board, two repos, and every key through a pseudo-terminal;
`.factory/ci` with a fake `gh`: a merged or closed PR is reported as such)
(prompt copies and the contracts between prompts and scripts stay in step).

`job` is tested by `bash tests/job_test.sh` (120 checks, among them the auto-merge gate; a throwaway repo with a bare remote, the agents played by writing their files): the full
loop with a CHANGES round, REWORK and MERGE; budget exhaustion; resume limits; the queue
under six concurrent `new` calls; docs CLEAN and NOT-DOCS; superseded; `pr` delivery,
rework after someone pushed to the branch, sync (resolved and needs-human), job.json files from
before `job`, input checks. The
orchestrator driving it has not run in a real `/factory` session yet.

`heavy` (slots, cache, gate, signals, exit codes), `guard` (166 allow/deny cases in `tests/guard_cases.txt`, run with `python3 -I tests/guard_test.py`, and a
real subagent run in a trusted project: `pytest` refused, `echo` allowed, also in bypass
mode), `precheck` and `watch` are tested on their own. The agent prompts that use them, the
queue, `--docs`, the already-done check and the closing of issues have not run in a real
`/factory` session yet: watch the first run with `.factory/heavy
status` and `.factory/watch`, and feed findings back here.
