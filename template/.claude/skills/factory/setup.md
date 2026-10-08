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
  `git check-ignore -q .factory/VERSION .claude/skills/factory/SKILL.md .claude/agents/factory-builder.md`
  must succeed, and `git status --porcelain` must not list any of those paths. If not,
  stop: tell the user to re-run `factory-init`.

## 1. Inspect (read-only)

- `git rev-parse --show-toplevel`, `git branch --show-current`, `git status --porcelain`
  (remember this output: it must be identical at the end).
- `git remote -v` → **forge**: github.com → `github`; git.ia.surf.nl / gitlab.com →
  `gitlab`; none → `none`.
- `AGENTS.md`, `CLAUDE.md`, `README.md`, `CONTRIBUTING.md` (if present).
- Stack: `pyproject.toml`, `uv.lock`, `package.json`, `DESCRIPTION` (R), `go.mod`,
  `Cargo.toml`, `*.csproj`, …
- CI: `.github/workflows/*` or `.gitlab-ci.yml` + `.gitlab/*.yaml`. Which checks run?
- Setup, test, lint, build and dev-server commands (config + README + AGENTS.md).
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
`{"label": "factory:ready", "allowed_authors": ["<login>"], "report": false}` with the
logged-in user only (`gh api user --jq .login` / `glab api user --jq .username`). Never
add other authors unless the user asks. Forge `none`, or the user does not want issue
mode → `"issues": null` (then `next` uses `backlog.md`).

**Delivery** (ask the user once, recommend `pr`): `local` (merge into the base branch
locally), `push` (push `factory/<id>` only) or `pr` (push + open a PR/MR). Forge `none`
→ `local`. `draft: true` unless the user wants ready-for-review PRs. Check `push`/`pr`
can work: `gh auth status` / `glab auth status`, and `git ls-remote <remote>` succeeds.

## 3. Write

`.factory/config.json`:

```json
{
  "template": "<contents of .factory/VERSION>",
  "archetype": "A",
  "forge": "github",
  "port_base": 5100,
  "reviewers": ["security", "code", "ux", "ui", "audit"],
  "issues": { "label": "factory:ready", "allowed_authors": ["<login>"], "report": false },
  "delivery": { "mode": "pr", "remote": "origin", "draft": true }
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
- Validate: <test> · <lint> · <build>
- Dev server: <command with {port}>, ready when <url/curl check> answers
- Pages to screenshot by default: <paths, e.g. / /upload>
- Conventions: <commit style, code style, anything agents must respect>
- Commits: in English, following the repo's commit convention
- Notes: <port conflicts, slow tests, data that must never be touched>
```

## 4. Verify (run and report the output)

- `.factory/watch --once` → "factory board: no jobs yet".
- `ls .claude/agents/factory-reviewer-*.md` covers `config.reviewers`.
- `git status --porcelain` is identical to step 1: nothing tracked changed.
- With ux/ui: start the dev server on a free port, run
  `.factory/shoot http://localhost:<port> --out /tmp/factory-shoot-check`, expect exit 0
  and **look at one screenshot** with Read (the app is really visible). Stop the server.
  Missing browser: `uv run --with playwright==1.63.0 playwright install chromium`.
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
