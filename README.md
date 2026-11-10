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

Then, in a Claude Code session in that repo (sonnet is enough for the orchestrator):

```text
/factory <feature>              full loop
/factory --light <feature>      small change: code review (+ security/privacy if touched)
/factory --docs <feature>       documentation only: one carry-out step, no reviewers
/factory issue <nr> | next      from an issue (trusted authors only) or .factory/backlog.md
/factory approve|rework|resume|deliver <id>
/factory status                 or live: .factory/watch [--tmux]
```

`factory-init --remove` takes it out again (refuses while jobs are unfinished);
`factory-init --no-setup` installs or updates without starting Claude. `factory-init`
is just a symlink to `./install`, so updating the factory everywhere = `git pull` here
and re-run `factory-init` in each repo.

## Local-only

`install` copies `template/` into the repo and adds these paths to
`.git/info/exclude` (not `.gitignore`, so not even that is committed):

```text
.claude/skills/factory/      SKILL.md (orchestrator) + setup.md (/factory setup)
.claude/agents/factory-*.md  spec-writer, builder, approver, reviewer-{security,code,ux,ui,audit,
                             privacy,methodology,llm-safety,data-quality}
.factory/                    config.json + repo.md (written by setup), backlog.md, job, shoot, serve,
                             heavy, guard, precheck, rereview, watch, ci, VERSION, jobs/, run/, cache/
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
| `heavy --cache -- <cmd>` | Validation runs once per commit: a passing run is recorded for the exact tree (clean tree, same command, same worktree) and the reviewers, audit and approver get an instant `CACHE HIT`. Failures, dirty trees and new commits run for real. |
| `.factory/guard` | A `PreToolUse` hook in every factory agent: a test, build, install, lint, type-check or browser command that is not run through `heavy` is refused with the fix in the message, so the limits do not depend on the agent remembering. It looks through `&&`/`;`/pipes, `$(…)`, loops, `bash -c`/`-lc`, wrappers (`env`, `timeout`, `xargs`, …) and runners (`uv run`, `npx`, `pnpm exec`, `python -m`, …), and knows npm-family script names (`test:*`, `typecheck`, `e2e`), `make -C`/`-j`, Python, Node, JVM, .NET, Go, Rust and R (`Rscript -e 'devtools::test()'`, `R CMD check`); `--version`/`--help` always pass. Needs a trusted workspace (Claude Code runs project-agent hooks only after the trust dialog, in bypass mode too); `limits.guard: false` turns it off. `install` also adds a `--subagents-only` variant to `.claude/settings.local.json`, so ad-hoc `general-purpose` subagents are covered while your own session stays unrestricted. |
| `limits.open_prs` (default 5) | Jobs at `pr-open` before new ones wait: every merge makes the other open PRs conflict, and CI is the slow part (median 3-14 h from PR to merge). `watch` and `status` show open PRs, the oldest and failing pipelines; the factory never retries a pipeline. `watch` shows one live CI/CD line per `pr-open` job (stages/jobs via `.factory/ci`, GitHub Actions + GitLab CI); `watch <id>` shows the full table, `--no-ci` hides it. |
| `heavy gate` | The orchestrator waits (max 10 min, then continues with a warning) while the CPU is above 90% before it spawns a spec-writer, builder or review wave. |

Defaults need no configuration; override with `limits` in `config.json`
(`active_jobs`, `open_prs`, `heavy_slots`, `cpu_budget`, `cpu_max`, `load_max`) or the env
vars `FACTORY_HEAVY_SLOTS`, `FACTORY_CPU_BUDGET`, `FACTORY_CPU_MAX`, `FACTORY_LOAD_MAX`,
`FACTORY_LOCK_DIR`. `.factory/watch` shows the load and active jobs
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
- **Cheap orchestrator:** run the `/factory` session on sonnet with `/effort medium`: it was
  producing 650-970 output tokens per turn, almost all reasoning, for a bookkeeping role. It
  reports one line per event, and after about 10 delivered jobs it tells you to `/clear` and
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

## Status

Install/update/remove, the git-exclusion and the loading of the skill and agents by
Claude Code are tested. `shoot` and `watch` are tested. The `/factory` loop has run for
about 40 jobs in two repos (onderwijsdata-chat, prompt-library); feed findings back here
and tag stable versions (`git tag v0.x.y`), because `install` records
`git describe` in `.factory/VERSION`.

`job` is tested in a simulated repo with a bare remote and fake agent files: the full
loop with a CHANGES round, REWORK and MERGE; budget exhaustion; resume limits; the queue
under six concurrent `new` calls; docs CLEAN and NOT-DOCS; superseded; `pr` delivery,
rework after someone pushed to the branch, and sync (resolved and needs-human). The
orchestrator driving it has not run in a real `/factory` session yet.

`heavy` (slots, cache, gate, signals, exit codes), `guard` (166 allow/deny cases in `tests/guard_cases.txt`, run with `python3 -I tests/guard_test.py`, and a
real subagent run in a trusted project: `pytest` refused, `echo` allowed, also in bypass
mode), `precheck` and `watch` are tested on their own. The agent prompts that use them, the
queue, `--docs`, the already-done check and the closing of issues have not run in a real
`/factory` session yet: watch the first run with `.factory/heavy
status` and `.factory/watch`, and feed findings back here.
