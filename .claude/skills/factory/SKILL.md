---
name: factory
description: Software factory-loop — spec → build → parallelle reviews → approve → merge/escalate. Gebruik bij "/factory <feature>", "/factory next", "/factory approve <id>", "/factory rework <id> <note>".
---

# Factory

Je bent de **orchestrator**. Je schrijft zelf geen code en geen spec: je spawnt
subagents, wacht op hun files, leest de verdicts en werkt `job.json` bij.
Elke subagent schrijft precies **één markdown-file**; jij leest alleen die files.

## Loop

```text
/factory <feature>
   │
   ▼
 spec ──► build (round N) ──► review round N ──┬─ alle PASS ──► approve ──┬─ MERGE ──► merged
 (spec-writer)  (builder)   (parallel, WAIT)   │                          ├─ REWORK ─► build N+1
                                ▲              └─ ≥1 CHANGES ─┐           └─ ESCALATE ► needs-human
                                └──────────── N < MAX_ROUNDS ──┘
                                              N = MAX_ROUNDS ──► needs-human
```

## Constanten

- `MAX_ROUNDS = 3` — daarna `needs-human`.
- `MAX_RESUMES = 2` — hoe vaak je een agent opnieuw spawnt die terugkwam zonder zijn
  output-file te schrijven. Daarna `needs-human`.
- Poort van job `NNN-…` (n = NNN als getal): builder `5100 + 10n`, ux `5101 + 10n`,
  ui `5102 + 10n`.

## Layout

```text
<repo>/factory/jobs/<job-id>/          (gitignored, in de main checkout)
  job.json
  spec.md
  round-1/build.md
  round-1/review-<naam>.md
  round-1/...
  decision.md                          (approver, laatste ronde)
  rework.md                            (alleen na /factory rework)
<repo>/../<repo>-worktrees/<job-id>/   (git worktree, branch factory/<job-id>)
```

`<job-id>` = `NNN-<slug>` (NNN = hoogste bestaande + 1, drie cijfers; slug uit de
feature, kleine letters, max 40 tekens).

`job.json`:

```json
{
  "id": "001-voorbeeld",
  "feature": "<letterlijk zoals de user het gaf>",
  "stage": "spec | build | review | approve | needs-human | merged",
  "round": 0,
  "port": 5110,
  "branch": "factory/001-voorbeeld",
  "worktree": "/abs/pad/<repo>-worktrees/001-voorbeeld",
  "resumes": 0,
  "reviews": { "security": null, "ux": null, "ui": null, "code": null }
}
```

`reviews.<naam>` is `null` tot de file bestaat, daarna `"PASS"` of `"CHANGES"`.
Herschrijf `job.json` na elke stage-wissel. Rapporteer elke transition in één regel.

## Paths-blok

Elke subagent-prompt begint met:

```text
Repo: <main checkout, absoluut>
Worktree: <worktree, absoluut>
Job: <repo>/factory/jobs/<job-id>
Branch: factory/<job-id>
```

## Commands

### `/factory <feature>`
1. Bepaal job-id, poort. `git worktree add -b factory/<job-id> <worktree> HEAD`
   (vanaf de huidige branch). Maak jobmap, schrijf `job.json` (stage `spec`).
2. **Spec:** spawn `spec-writer`, prompt `<paths> Feature: <feature>`. Wacht tot
   `spec.md` bestaat. Stage → `build`.
3. **Build round N** (N = round + 1): spawn `builder` (naam `builder-<job-id>`),
   prompt `<paths> Build round N. Port: <port>.` Wacht tot `round-N/build.md`
   bestaat. Stage → `review`, round = N.
4. **Review round N:** spawn **alle** reviewers in **één bericht** (parallel):
   - `reviewer-security` (opus)
   - `reviewer-ux` (sonnet)
   - `reviewer-ui` (sonnet)
   - `reviewer-code` (sonnet)

   Prompt: `<paths> Review round N. Port: <port + offset>.` **WAIT FOR ALL:** ga pas
   verder als alle `round-N/review-<naam>.md` bestaan. Lees van elke file alleen de
   eerste regel (`VERDICT: PASS|CHANGES`) en zet die in `reviews`.
5. **Beslissing:**
   - alle `PASS` → stage `approve`, spawn `approver`, prompt `<paths> Final round: N.`
   - ≥1 `CHANGES` en N < `MAX_ROUNDS` → terug naar stap 3 met N+1 (de builder leest de
     reviews van de vorige ronde zelf).
   - ≥1 `CHANGES` en N = `MAX_ROUNDS` → stage `needs-human`, meld welke reviews
     blokkeren.
6. **Approver** schrijft `decision.md`, eerste regel `DECISION: MERGE|REWORK|ESCALATE`:
   - `MERGE` → merge (zie Merge) → stage `merged`.
   - `REWORK` → build round N+1 (telt mee voor `MAX_ROUNDS`).
   - `ESCALATE` → stage `needs-human`; toon de reden uit `decision.md`.

### `/factory next`
Neem het eerste ongecheckte item (`- [ ]`) uit `factory/backlog.md`, vink het af
(`- [x] … (job <id>)`) en draai `/factory <dat item>`.

### `/factory approve <id>`
Alleen bij `needs-human`. Merge direct (zie Merge), zonder verdere reviews.

### `/factory rework <id> <note>`
Alleen bij `needs-human`. Schrijf `<note>` naar `rework.md`, zet round-teller zodat
er nog één ronde bij kan (`MAX_ROUNDS` geldt per rework opnieuw), spawn builder met
prompt `<paths> Build round N+1. Port: <port>. Lees ook rework.md.`

### `/factory` (zonder argument) / `status`
Toon per job: id, stage, round, reviews.

## Merge

In de main checkout: `git merge --no-ff factory/<job-id> -m "factory: <job-id> — <feature>"`.
Bij conflict: `git merge --abort`, stage `needs-human`. Na succes:
`git worktree remove <worktree>` en `git branch -d factory/<job-id>`.

## Regels

- Lees geen volledige diffs of code zelf; vertrouw op de files van de agents.
- Een agent die terugkomt zonder zijn file: spawn opnieuw (max `MAX_RESUMES`).
- Draai nooit twee builders in dezelfde worktree.
- Pas bestanden in de worktree niet zelf aan.
