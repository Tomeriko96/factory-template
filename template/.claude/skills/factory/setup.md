# `/factory setup`: tailor the factory to this repo

Run once after `factory-init` (preferably on opus); re-run any time to re-tailor. You
inspect the repo and write exactly two files: `.factory/config.json` and
`.factory/repo.md`. You do not invent anything beyond the matrix below.

## Hard rules

- Write **only** inside `.factory/`. Never edit `AGENTS.md`, `CLAUDE.md`, `.gitignore`,
  agent or skill files, or any tracked file.
- Never commit, never push, never create branches or tags (except the throwaway
  smoke-test branch in step 4, which you delete again; the smoke test always uses
  `local` delivery).
- First check the install is really local-only:
  `for p in .factory/VERSION .claude/skills/factory/SKILL.md .claude/agents/factory-builder.md; do git check-ignore -q "$p" || echo "NOT ignored: $p"; done`
  must print nothing (`check-ignore -q` takes one path at a time), and
  `git status --porcelain` must not list any of those paths. If not, stop: tell the
  user to re-run `factory-init`.

## 1. Inspect (read-only)

- `git rev-parse --show-toplevel`, `git branch --show-current`, `git status --porcelain`
  (remember this output: it must be identical at the end).
- `git remote -v`. **Delivery remote** = the remote the team opens PRs/MRs on (usually
  `origin`; with several remotes, e.g. a private GitLab plus a public GitHub mirror,
  check README/AGENTS.md/CONTRIBUTING.md and ask if unclear). **Forge** follows that
  remote: github.com → `github`; git.ia.surf.nl / gitlab.com → `gitlab`; none → `none`.
  Every other remote goes into repo.md under "Never push to".
- `AGENTS.md`, `CLAUDE.md`, `README.md`, `CONTRIBUTING.md` (if present).
- Stack: `pyproject.toml`, `uv.lock`, `package.json`, `DESCRIPTION` (R), `go.mod`,
  `Cargo.toml`, `*.csproj`, …
- CI: `.github/workflows/*` or `.gitlab-ci.yml` + `.gitlab/*.yaml`. Which checks run?
- Setup, test, lint, build and dev-server commands (config + README + AGENTS.md,
  Makefile, package.json scripts). Read what each one really does: a `make dev` that
  first runs `pkill`, a hard-coded port or a dev proxy to a fixed backend port all
  break parallel reviewers (see Serve below).
- Untracked runtime files the app needs (`git status --ignored --short`): `.env`,
  local databases, data folders. They are not in a job worktree.
- Data scan (decides archetype and extra reviewers): grep for BSN, PGN, ONR,
  onderwijsnummer, persoonsgegevens, AVG, GDPR, privacy, mask, upload, prompt,
  tool_call, litellm, bekostiging, indicator, JR, DR, quality.json, parquet, star schema.
- Port conflicts: grep `.devcontainer/`, `docker-compose*`, `launch.json`,
  `vite.config.*` for ports in the range `port_base` … `port_base + 10 × 100`.

## 2. Decide (apply the matrix, do not invent)

Archetype (when in doubt: ask the user, max one question):

| # | Archetype | Signals |
|---|---|---|
| A | Web app (frontend + backend/API) | React/Vue/Streamlit/FastAPI + routes |
| B | Data pipeline / ETL / package | Python/R lib, parquet, star schema, ingest |
| C | LLM/chat app | tool calling, uploads, prompts, LiteLLM |
| D | Library / API client / catalogue | package, little or no UI |
| E | Docs / static site | markdown/quarto/site generator |

Combinations happen (C is often A + C): take the union of the reviewers.

Reviewer set (`config.reviewers`):

| Archetype | Reviewers | Extra |
|---|---|---|
| A | security, code, ux, ui, audit | — |
| B | security, code, data-quality, audit | methodology if there are indicators/funding/definitions |
| C | security, llm-safety, code, audit | ux + ui if there is a real UI |
| D | security, code, data-quality, audit | methodology if there are indicators/definitions |
| E | code | — |

**Privacy rule (all archetypes):** if the data scan finds personal data (BSN, PGN,
onderwijsnummer, row-level uploads, pseudonymisation), add `privacy`, also for A, C, D
and E. When in doubt: add it and tell the user.

Models live in the agent frontmatter (builder, approver, security, privacy, llm-safety
and audit on opus; the rest on sonnet). Do not change them. Advise the user to run the
`/factory` sessions themselves on sonnet.

**Ports:** `port_base` 5100 unless the scan found a conflict; then pick another base
and say why in `repo.md`.

**Issues:** forge `github`/`gitlab` → `issues` =
`{"label": "factory:ready", "allowed_authors": ["<login>"], "report": false, "link": "Closes"}`
with the logged-in user only (`gh api user --jq .login` / `glab api user --jq .username`). Never
add other authors unless the user asks. Forge `none`, or the user does not want issue
mode → `"issues": null` (then `next` uses `backlog.md`). Set `"link": "Refs"` when the
repo is mirrored to another forge (a second remote on another host, or docs that say
commits are mirrored): `Closes #N` would close an unrelated issue there. Check the label
exists (`gh label list` / `glab label list`); if not, tell the user (creating it is
their call, it changes the forge).

**Delivery** (ask the user once, recommend `pr`): `local` (merge into the base branch
locally), `push` (push `factory/<id>` only) or `pr` (push + open a PR/MR). Forge `none`
→ `local`. `draft: true` unless the user wants ready-for-review PRs. Ask at the same time
whether the factory should switch on auto-merge on the PR/MR it opens (`auto_merge`,
default `false`; it needs `draft: false` and then also decides on the merge, so only on
the user's explicit yes). Check `push`/`pr`
can work: `gh auth status` / `glab auth status`, and `git ls-remote <remote>` succeeds.

**Running the app in a worktree** (skip for archetypes without a server). Several
reviewers serve the same worktree at the same time, each on its own port, so define:

- **Worktree setup**: run once per new worktree by the builder (install dependencies).
  Untracked runtime files are never copied: pass them by path instead, e.g.
  `uv run --env-file <Repo>/.env …`, `docker run --env-file …`, or an env var pointing at
  the file in the main checkout. Never print or read secret files.
- **Prepare**: run by the builder at the end of every round, after its last commit
  (e.g. build the frontend), so serving needs no build.
- **Serve**: one command with `{port}` that reviewers run through `.factory/serve`
  (own process group, refuses a busy port, waits for the ready path, stops exactly
  that group); it must (1) start a single
  process tree on `{port}` only, (2) talk only to services on that same port, never to
  a fixed dev-proxy port, (3) never stop or signal other processes (no `pkill`,
  no `make stop`), (4) never write into the worktree (no build, no install). Prefer the
  production-like path (backend serving the built frontend) over a dev server with a
  proxy. If no such command exists without a code change, say so in repo.md and to the
  user (that code change is a good first factory job); until then use `"reviewers"`
  without ux/ui.

## 3. Write

`.factory/config.json`:

```json
{
  "template": "<contents of .factory/VERSION>",
  "archetype": "A",
  "forge": "github",
  "port_base": 5100,
  "reviewers": ["security", "code", "ux", "ui", "audit"],
  "issues": { "label": "factory:ready", "allowed_authors": ["<login>"], "report": false, "link": "Closes" },
  "delivery": { "mode": "pr", "remote": "origin", "draft": true, "auto_merge": false }
}
```

Check that every name in `reviewers` has `.claude/agents/factory-reviewer-<name>.md`.

`.factory/repo.md` (short, factual; agents read it every round):

```markdown
# Repo profile (factory)

- Archetype: <A–E> — <one line why>
- Reviewers: <list> — <one line why, incl. privacy rule>
- Forge / CI: <GitHub Actions | GitLab CI | none> — <which checks>
- Setup fresh checkout: <commands, run in the worktree>
- Validate: <test> · <lint> · <build> (match what CI runs, incl. install extras)
- Validate (docs-only): <which paths count as docs, e.g. *.md, docs/> → <quick checks, e.g. mkdocs build --strict, or "none">
- Worktree setup (builder, once): <commands>
- Prepare (builder, end of every round): <commands, e.g. frontend build>
- Serve (reviewers, per port): <command with {port}> · ready path: <e.g. /health>
  (agents run it as `.factory/serve start <port> --cwd <worktree> --ready <path> -- <command>`)
- Runtime files: <how the app gets .env/db/data from the main checkout, by path only>
- Pages to screenshot by default: <paths, e.g. / /upload>
- Conventions: <commit style, code style, anything agents must respect>
- Commits: in English, following the repo's commit convention; issues as `Refs #N`.
  Edits inside existing text stay in that file's language.
- Delivery remote: <remote> · Never push to: <other remotes, or "none">
- Notes: <port conflicts, slow tests, costs (e.g. real LLM calls), data that must never be touched>
```

## 4. Verify (run and report the output)

- `.factory/watch --once` → "factory board: no jobs yet".
- `ls .claude/agents/factory-reviewer-*.md` covers `config.reviewers`.
- `git status --porcelain` is identical to step 1: nothing tracked changed.
- With ux/ui: run Worktree setup + Prepare + Serve in a throwaway worktree
  (`git worktree add --detach /tmp/factory-serve-check HEAD`, removed afterwards) on a
  free port, started with `.factory/serve start` and stopped with `.factory/serve stop`
  — this proves Serve works outside the main checkout — then run
  `.factory/shoot http://localhost:<port> --out /tmp/factory-shoot-check`, expect exit 0
  and **look at one screenshot** with Read (the app is really visible).
  Missing browser: `uv run --no-project --python 3 --with playwright==1.63.0 playwright install chromium`.
- Any `uv run` you or the agents use for factory tooling (not the app) needs
  `--no-project --python 3`, so it neither syncs the repo's project nor follows its
  `.python-version` pin.
- **Smoke test** (default; skip only if the user declines): `git switch -c
  factory-smoketest`, run `/factory --light <trivial change, e.g. a README typo>`, check
  that spec → build → review → decision complete. Then clean up: `git switch -`,
  `git worktree remove --force` the job worktree, `git branch -D factory-smoketest
  factory/<job-id>`, delete `.factory/jobs/<job-id>`. Not run = not verified: say so
  explicitly.

## 5. Report to the user

Archetype · forge · reviewers (+ why) · port base · issue mode · delivery ·
smoke-test outcome · files written. Then the next steps: `/factory <feature>`, `/factory --light <feature>`,
fill `.factory/backlog.md` for `/factory next`, live board with `.factory/watch`
(`--tmux` for a split pane). Remind them: the factory itself is local to this clone and
invisible to git (`factory-init --remove` takes it out again); only job branches leave
the machine, and only with `push`/`pr` delivery.
