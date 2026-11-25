Part of the factory skill: SKILL.md's rules apply here too. Moved out of SKILL.md unchanged, so it is read only when needed; a **Section** is one of SKILL.md.

## Reviewers: which ones the script keeps

`.factory/job reviewers` then keeps only the reviewers the diff (`<base>...HEAD` of the
worktree) concerns, and prints why each was chosen or skipped (`NOTE: reviewer paths: …`):

- `code` and `audit`: always.
- A diff that only touches tests or docs: only `code` and `audit`.
- `security`: any code change outside tests/docs, and always for CI, dependencies,
  containers, schema or auth (the auto-merge hold classes).
- `ux`/`ui`: only when a file matches the "UI paths" line of repo.md (default:
  `*.tsx *.jsx *.vue *.svelte *.css *.scss *.html`, `templates/`, `static/`,
  `frontend/src/**`); round > 1 only when UI files changed since the last round, or they
  gave `CHANGES` before. Their prompt carries `UI review: light|full (why)`: **light** by
  default (one screenshot per changed page/route at 1280 and 375 with `shoot --axe`, console
  errors and axe violations, no Playwright flow, `heavy --priority low`, sonnet at medium);
  **full** (the exploratory review) only in a `full` job whose diff adds a new page/route
  (`config.ui_page_globs`, default `*/pages/*`, `*/routes/*`, `*/views/*`, `*/app/**/page.*`,
  `*/templates/*.html`, `*/screens/*`) or whose spec.md has a `UI review: full` line.
  `config.ui_review: "light"|"full"` forces one form for every job; `.factory/job set <id>
  ui_review light|full|auto` for one job.
- `llm-safety`: only when prompt, agent or LLM code changes (default globs `*prompt*`,
  `*agent*`, `*llm*`, `*/prompts/*`, `*/agents/*`, `*/llm/*`; a prompt in `.md` outside
  `docs/` counts as code).
- `data-quality`: only for pipelines, ETL, SQL and data files (default globs `*/data/*`, `*/etl/*`,
  `*/pipelines/*`, `*transform*`, `*ingest*`, `*.sql`, `*/dbt/*`, `*.csv`, `*.parquet`, …).
- `privacy`: only when a path in `reviewer_paths.privacy` changes, else the
  `delivery.auto_merge_never` globs; with neither set, files whose names handle personal data
  (`*user*`, `*person*`, `*student*`, `*account*`, `*consent*`, `*export*`, `*/auth/*`, `*logging*`, …).
- Any other reviewer (methodology, …): on any code change, unless `reviewer_paths` names its globs.
- **Specialists** (everyone but code, audit and security): from round 2 on only when their paths
  changed since the last round (or they objected), and not for a change of one or two lines in their
  paths (`limits.review_min_lines`, default 3; a number, or `{"<reviewer>": n, "default": n}`; `0` = off;
  ux/ui only when named; any change to prompt text counts in full for llm-safety). Measured on one day:
  26 specialist runs on sonnet blocked nothing; the two blocking findings came from audit and security.

`config.reviewer_paths` (optional) overrides the globs per reviewer, e.g.
`{"llm-safety": ["agent/**", "**/prompt*"], "privacy": ["src/students/**"], "ui": ["web/**"]}`.
A glob with a `/` matches the whole path (`x/` = that directory anywhere), one without
the file name. Reviewers whose latest verdict is not PASS always run again.
A review `VERDICT: PASS (unverified: tests did not run: <reason>)` is not blocking (the round goes
on, `job next` prints `NOTE: unverified …`), but it is a precheck issue until the approver ran those
tests (`VERIFIED: <reviewer>: …` in decision.md), and that reviewer runs again in the next round.
