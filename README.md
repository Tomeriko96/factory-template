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
.factory/                    config.json + repo.md (written by setup), backlog.md, shoot, watch,
                             VERSION, jobs/
```

Job worktrees go to `../<repo>-worktrees/<job-id>`, outside the repo. Excluded files
are not checked out there, so nothing from the factory can end up in a job commit.

## Delivery

After the approver says MERGE, `config.delivery.mode` decides:

| Mode | What happens | End stage |
|---|---|---|
| `local` | `git merge --no-ff` into the base branch, in this clone | `merged` |
| `push` | push `factory/<id>` to the remote | `pushed` |
| `pr` (recommended) | push + open a (draft) PR/MR with the approver's body: summary, verified acceptance criteria, validation, leftovers, `Closes #<nr>` | `pr-open` |

The factory only ever pushes `factory/*` branches: never the base branch, never
`--force`. It never merges, approves or closes a PR/MR. Review comments go back in with
`/factory rework <id> "<comments>"`; the next approved round pushes to the same branch,
so the PR/MR updates.

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
  (`.factory/shoot`: screenshots + overflow, a11y and console checks).
- **Severity.** Findings are `[blocking]` or `[non-blocking]`; only blocking findings
  trigger another round. Non-blocking ones end up as Leftovers in `decision.md`.
- **Everything in English.** Artifacts, reports and commit messages.

## Status

Install/update/remove, the git-exclusion and the loading of the skill and agents by
Claude Code are tested. `shoot` and `watch` are tested. The `/factory` loop itself has
not run end-to-end yet: `/factory setup` offers a smoke test; feed findings back here
and tag stable versions (`git tag v0.x.y`), because `install` records
`git describe` in `.factory/VERSION`.
