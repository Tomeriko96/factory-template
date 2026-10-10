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
.factory/                    config.json + repo.md (written by setup), backlog.md, shoot, serve,
                             heavy, watch, VERSION, jobs/, run/, cache/
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
| `.factory/heavy -- <cmd>` | Every test, build, lint and install of every agent goes through it: a machine-wide set of `flock` slots (default cores/4, shared by all repos), `nice`/`ionice`, and `FACTORY_CPUS` for worker counts. `heavy status` shows holders and load. |
| `heavy --cache -- <cmd>` | Validation runs once per commit: a passing run is recorded for the exact tree (clean tree, same command, same worktree) and the reviewers, audit and approver get an instant `CACHE HIT`. Failures, dirty trees and new commits run for real. |
| `heavy gate` | The orchestrator waits (max 10 min, then continues with a warning) while the 1-minute load is above `load_max` (default 1.25 × cores) before it spawns a spec-writer, builder or review wave. |

Defaults need no configuration; override with `limits` in `config.json`
(`active_jobs`, `heavy_slots`, `load_max`) or the env vars `FACTORY_HEAVY_SLOTS`,
`FACTORY_LOAD_MAX`, `FACTORY_LOCK_DIR`. `.factory/watch` shows the load and active jobs
against the cap. The audit also has bounds: at most 3 mutation checks, a suspect file at
most twice, base comparisons only for the claim concerned.

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
merge --auto`), so the forge merges once its own checks pass. It never merges directly. Review comments go back in with
`/factory rework <id> "<comments>"`; the next approved round pushes to the same branch,
so the PR/MR updates.

`/factory sync [<id>]` keeps open PRs/MRs mergeable: it asks the forge whether each still
merges into the base branch (also at the end of delivery and on `status`), and on a
conflict has the builder merge the base into the job branch (a merge commit, never a
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

`heavy` (slots, cache, gate, signals, exit codes) is tested on its own, including four
parallel callers on two slots. The agent prompts that use it, the queue and the load gate
have not run in a real `/factory` session yet: watch the first run with `.factory/heavy
status` and `.factory/watch`, and feed findings back here.
