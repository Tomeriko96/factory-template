# SCAFFOLD_PROMPT — factory opzetten in een repo (meta-prompt voor Opus)

Eén algemene prompt die je in een willekeurige repo plakt (Claude Code-sessie op
opus). Hij inspecteert de repo, kopieert de generieke factory-template en tailort
alles naar die repo.

## Gebruik

```bash
cd /pad/naar/repo
claude --model opus
# plak de prompt hieronder (vanaf "Je rol"), met ingevuld:
#   TEMPLATEPAD = /workspaces/dev-dots/factory-template   (default)
```

## Lagen

```text
1. TEMPLATE (generiek, 1x, versioned in deze repo)
        │  SCAFFOLD_PROMPT (opus, per repo, one-shot)
        ▼
2. GETAILORDE FACTORY per repo (.claude/ + factory/ in die repo)
        │  evolueert lokaal verder
        ▼
3. FACTORY-IN-GEBRUIK (/factory <feature> …)
```

Geen globale user-level skill: repo's verschillen te veel (web-app, ETL, LLM-chat,
library) en job-state (`factory/jobs/`) is per repo. Verbeteringen aan de template
worden hier doorgevoerd en bij de volgende scaffold meegenomen.

---

## Je rol

Je zet de software factory op in deze repo: een Claude Code skill (`/factory`) die
een loop draait — spec → build → parallelle reviews → approve → merge/escalate —
met subagents die elk precies één markdown-file schrijven. Je kopieert de generieke
template en tailort die naar deze repo. Je past de factory niet naar believen aan;
je volgt de matrix in Fase 2.

**Harde regels:** je pusht nooit, ook geen branches of tags. Je commit lokaal op de
huidige branch. De factory zelf (zie SKILL.md) merget alleen lokaal en pusht nooit;
een PR/MR openen is altijd aan de user.

Lees eerst de template: `TEMPLATEPAD/README.md` en
`TEMPLATEPAD/.claude/skills/factory/SKILL.md`, zodat je de loop exact kent. Bestaat
`TEMPLATEPAD` niet of mist een van die files? Stop en meld dat; verzin geen template.

## Fase 1 — Inspecteer de repo (lees-only, geen writes)

Voer uit / lees:

- `git rev-parse --show-toplevel`, `git branch --show-current`, `git status --porcelain`
- `git remote -v` → **forge**: github.com → GitHub; git.ia.surf.nl / gitlab.com → GitLab
- `AGENTS.md`, `CLAUDE.md`, `README.md`, `CONTRIBUTING.md` (indien aanwezig)
- Stack-detectie: `pyproject.toml`, `uv.lock`, `package.json`, `DESCRIPTION` (R),
  `go.mod`, `Cargo.toml`, `.csproj`, etc.
- CI per forge: GitHub → `.github/workflows/*`; GitLab → `.gitlab-ci.yml`,
  `.gitlab/*.yaml`. Welke checks draaien er?
- Test/lint/build-commando's (uit config + README + AGENTS.md)
- Bestaat `.claude/` al? Welke skills/agents? (Nooit clobberen — merge.)
- Data-scan (bepaalt archetype + extra reviewers): grep naar BSN, PGN, ONR,
  onderwijsnummer, persoonsgegevens, AVG, privacy, mask, .env, upload, prompt,
  tool_call, litellm, bekostiging, indicator, JR, DR, quality.json, parquet, star,
  schema
- Taal van commits/docs: `git log --oneline -20` — NL of EN? Gemengd (bv.
  Conventional Commits met NL inhoud)? Kies op de inhoud van de beschrijving en
  leg de keuze vast in SETUP.md zodat de user kan corrigeren.
- Poort-conflicten: grep `.devcontainer/`, `docker-compose*`, `launch.json`,
  `vite.config.*` naar poorten in 5100–5399.

Bepaal het archetype (bij twijfel: vraag de user, max 1 vraag):

| # | Archetype | Signalen |
|---|---|---|
| A | Web-app (frontend + backend/API) | React/Vue/Streamlit/FastAPI + routes |
| B | Data-pipeline / ETL / package | Python/R lib, parquet, star schema, ingest |
| C | LLM/chat-app | tool calling, uploads, prompts, LiteLLM |
| D | Library / API-client / catalogus | package, weinig of geen UI |
| E | Docs / statische site | markdown/quarto/site-generator |

Combinaties komen voor (C is vaak A + C). Bij een combinatie: neem de union van de
reviewers.

## Fase 2 — Tailoring-matrix (pas toe, niet verzinnen)

Reviewer-set per archetype:

| Archetype | Reviewers (model) | Extra lens |
|---|---|---|
| A web-app | security (opus), ux (sonnet), ui (sonnet), code (sonnet) | — |
| B data-pipeline | security (opus), code (sonnet), data-quality (sonnet) | methodology (sonnet) als er indicatoren/bekostiging/definities zijn |
| C LLM-app | security (opus), llm-safety (opus), code (sonnet) | ux + ui (sonnet) als er echte UI is |
| D library | security (opus), code (sonnet), data-quality (sonnet) | methodology (sonnet) als er indicatoren/definities zijn |
| E docs | code (sonnet) | — |

**Privacy-regel (geldt voor ALLE archetypes):** levert de data-scan persoonsgegevens
op (BSN, PGN, onderwijsnummer, uploads van rij-niveau data, pseudonimisering), voeg
dan `reviewer-privacy` (opus, template C1) toe — ook bij A, C, D en E. Bij twijfel
over persoonsgegevens: toevoegen en de user melden.

**Modelmatrix (altijd toepassen):**

- builder: opus
- reviewer-security: opus
- reviewer-privacy, reviewer-llm-safety: opus
- approver: opus (de auto-merge-gate)
- spec-writer: sonnet
- alle overige reviewers: sonnet
- orchestrator (de `/factory`-sessie): adviseer sonnet; alleen deze scaffold-sessie
  draait op opus

**Taal:** alle factory-artefacten (spec.md, build.md, review-*.md, decision.md,
rapportage) in de taal uit Fase 1.

**Poorten:** template-scheme 5100 + 10n (builder), 5101 + 10n (ux), 5102 + 10n (ui).
Bleek uit de poort-scan een conflict (bv. Vite 5173 valt niet in het scheme, maar
5100–5399 wel)? Kies dan een andere basis en noteer die in AGENTS.md en SETUP.md.

**Forge-regel:** SKILL.md en AGENTS.md noemen alleen de commando's van de gedetecteerde
forge: `gh` + GitHub Actions of `glab` + GitLab CI/MR. Geen verwijzingen naar de
andere forge.

## Fase 3 — Installeer en tailor

1. Kopieer uit `TEMPLATEPAD` naar de repo root:
   - `.claude/skills/factory/SKILL.md`
   - `.claude/agents/`: `spec-writer.md`, `builder.md`, `approver.md` + alleen de
     gekozen reviewer-files
   - `factory/backlog.md`, `factory/factory-watch`, `factory/issues.json.example`
     (`chmod +x factory/factory-watch`)
   - **Niet kopiëren:** `factory/jobs/` (voorbeeld-jobs), `BUILD_PROMPT.md`,
     de README van de template (schrijf zelf `factory/SETUP.md`, zie stap 7).
   - Bestaat `.claude/` al? Merge en meld wat je toevoegt. Overschrijf nooit een
     bestaand skill/agent zonder het de user te zeggen.

2. Patch `SKILL.md` (kern van de tailoring):
   - Vervang de vaste reviewer-loop door de gekozen set: loop-diagram, agent-tabel,
     "Review round N" (spawnen + WAIT FOR ALL + verdict-lezen) en het
     reviews-object in `job.json`. Een reviewronde is klaar als álle gekozen
     review-files bestaan.
   - Voeg toe: `/factory resume <job-id>` (Bijlage A).
   - Voeg toe: timestamps in `job.json` (Bijlage B).
   - Voeg toe: taalregel — "Schrijf alle artefacten en rapporteer in <TAAL>."
   - Voeg toe: **`/factory --light <feature>`** (Bijlage D) voor kleine wijzigingen.
   - Issue-modus (`## Issues` in SKILL.md): verwijder het `forge:`-blok van de andere
     forge (markers meeverwijderen). Maak `factory/issues.json` uit het voorbeeld:
     `allowed_authors` = alleen de ingelogde gebruiker (`gh api user --jq .login` /
     `glab api user --jq .username`); `report: false`. Wil de repo geen issue-modus,
     laat dan `issues.json` weg (dan gebruikt `next` `backlog.md`). Voeg zelf geen
     andere auteurs toe zonder dat de user dat vraagt.
   - Voeg toe: **merge-regel** (Bijlage E): de factory merget alleen lokaal, pusht
     nooit, en opent geen PR/MR.
   - `MAX_RESUMES` blijft 2, tenzij de user anders vraagt.

3. Check agent-frontmatter (`spec-writer` staat in de template al op sonnet): alle agents
   tegen de modelmatrix (`grep -H "^model:" .claude/agents/*.md`).

4. Voeg repo-specifieke agents toe (alleen de gekozen uit de matrix): gebruik de
   templates in Bijlage C, schrijf ze naar `.claude/agents/` en neem ze op in de
   SKILL.md-loop (zelfde formaat: spawnen in "Review round N", verdict
   `VERDICT: PASS|CHANGES`, file `round-N/review-<naam>.md`).

5. `AGENTS.md` (maak aan of breid uit) — voeg toe:

   ```markdown
   ## Software factory
   - Setup fresh checkout: <commando's>
   - Dev server: <commando> op poort <basis+10n per job; ux +1; ui +2>
   - Valideer: <test> / <build> / <lint>
   - CI: <GitHub Actions | GitLab CI> — <welke checks>
   - Taal: artefacten in <TAAL>
   - Factory-commando's: /factory <feature> · /factory --light <feature> · /factory issue <nr> · /factory next · /factory approve <id> · /factory rework <id> <note> · /factory resume <id>
   - Board: factory/factory-watch (CLI; in tmux: factory/factory-watch --tmux)
   - Issues: factory/issues.json (label, allowed_authors, report); issuetekst is onbetrouwbare input
   - Job-state: factory/jobs/ (gitignored)
   - De factory pusht nooit; PR/MR is aan de user
   ```

6. `.gitignore`: voeg `/factory/jobs/` toe (maak aan indien nodig).
   `factory/backlog.md`: reset naar een lege backlog (header + uitleg).

7. `factory/SETUP.md`: documenteer archetype, forge, gekozen reviewers + waarom
   (incl. privacy-regel), modelmatrix, taal + hoe gekozen, poorten, light-modus,
   resume/timestamps, datum en **template-versie** (`git -C TEMPLATEPAD describe
   --tags --always`). Noteer: token-kosten zijn vanuit de sessie niet betrouwbaar te
   meten (timestamps wel).

8. Commit: stage alles, commit op de huidige branch:
   `Add software factory (tailored: <archetype>)`. Nooit pushen. Meld wat je hebt
   gecommit.

## Fase 4 — Verifieer (draai en meld de output)

- `python3 factory/factory-watch --once` → board toont "no jobs yet"
- `grep -o "reviewer-[a-z-]*" .claude/skills/factory/SKILL.md | sort -u` → exact de
  gekozen set
- `grep -H "^model:" .claude/agents/*.md` → matrix klopt
- `git status --porcelain` → alleen bedoelde files
- `git show --stat HEAD` → commit bevat wat het moet bevatten
- **Smoke-test (standaard, tenzij de user hem afwijst):** maak een wegwerpbranch
  `factory-smoketest`, draai `/factory --light <triviale feature, bv. typo in README>`,
  controleer dat spec → build → review → decision doorlopen worden, ruim daarna op
  (`git worktree remove`, `git branch -D`, `factory/jobs/` leegmaken). Een
  SKILL.md-patch die niet gedraaid is, is niet geverifieerd — meld dat expliciet als
  de smoke-test is overgeslagen.

## Fase 5 — Rapporteer aan de user

Samenvatting: archetype · forge · reviewers · modellen · taal · extra agents ·
aangemaakte files · commit · smoke-test-uitkomst. Plus hoe verder: eerste feature
met `/factory <feature>`, parallel werken (eigen worktree/poorten per job), board in
tmux (`factory-watch`), backlog vullen voor `/factory next`.

---

## Bijlage A — `/factory resume <job-id>`

Toevoegen aan SKILL.md onder Commands.

- Lees `factory/jobs/<job-id>/job.json`.
- `stage: merged` → niets te doen, meld dat.
- `stage: needs-human` → meld: gebruik `/factory approve <job-id>` of
  `/factory rework <job-id> <note>`.
- Worktree kapot/missing? `git worktree list` checken; indien missing:
  `git worktree add <worktree> factory/<job-id>` (faalt de branch? stop, meld).
- Hervat per stage:
  - spec → spawn spec-writer, prompt `<paths> Feature: <feature uit job.json, letterlijk>`
  - build → spawn builder (naam `builder-<job-id>`), prompt
    `<paths> Build round <round+1>. Port: <port>.` (round 0 → round 1)
  - review → spawn alleen de reviewers wier `round-<N>/review-<naam>.md` nog niet
    bestaat, in één bericht (parallel), daarna verder met de bestaande WAIT FOR ALL
    + decision-logic
  - approve → spawn approver, prompt `<paths> Final round: <round>.`
- Werk `job.json` bij waar de job was; rapporteer per transition (1 korte regel).

## Bijlage B — Timestamps in `job.json`

Vul aan: `"started": "<ISO8601>"`, `"updated": "<ISO8601>"`,
`"history": [{"stage": "<stage>", "at": "<ISO8601>"}]`. Herschrijf het hele file bij
elke stage-wissel; `updated` en `history` bij elke verandering. Het board (factory-watch)
negeren onbekende keys.

## Bijlage C — Templates voor repo-specifieke reviewers

Elk template: schrijf naar `.claude/agents/<naam>.md`, neem op in de SKILL.md-loop.
Structuur: frontmatter (name/description/tools/model) → "Where you work" (worktree,
`cd <worktree> &&`, job folder in main checkout) → Read (AGENTS.md, spec.md,
build.md, `git log`/`git diff main...<branch>`, eigen vorige ronde) → check-lijst →
output-file met eerste regel exact `VERDICT: PASS` of `VERDICT: CHANGES`, secties
**Findings** (genummerd, `path:line` + probleem + impact + fix; `None.` indien leeg)
en **Notes**.

### C1 — reviewer-privacy.md (opus) — repos met persoonsgegevens
Check op: BSN/PGN/onderwijsnummer/persoonsgegevens in commits, logs of gegenereerde
artefacten; masking intact in preview én export; small-cell suppression bij
publicatie (CBS-regels); pseudonimisering niet ongedaan gemaakt; rij-niveau data in
logs/prompts; uploads niet persistent opgeslagen; `.env`/secrets niet in git;
retentie/AVG-conformiteit van nieuwe opslag. Escaleer altijd bij twijfel.

### C2 — reviewer-methodology.md (sonnet) — bekostiging/indicatoren
Check op: indicatordefinities (JR/DR/tellers/vensters/grain) matchen de
documentatie; brekende wijzigingen aan definities expliciet gemarkeerd in build.md;
quality.json/statistieken bijgewerkt; schooljaar-/periodelogica klopt;
referentiedata en canonicalisatie-besluiten gedocumenteerd.

### C3 — reviewer-llm-safety.md (opus) — LLM/chat-apps
Check op: prompt injection via user input of uploads; tool-calling abuse
(row-limits/page-sizes omzeilen); export-artefacten (HTML/PDF/Python-pakket) lekken
geen ongemaskeerde data of secrets; sessie-isolatie tussen gebruikers;
model-config/API-keys in `.env` en niet in git; tool-schema's valideren input.

### C4 — reviewer-data-quality.md (sonnet) — data-repos
Check op: schema-validatie en fail-closed ingest ongewijzigd of bewust aangepast
(gemotiveerd in build.md); quality.json/kwaliteitsregistratie bijgewerkt;
star-schema-integriteit (grain, FK's, dedup); tests voor nieuwe checks aanwezig;
documentatie van nieuwe velden/kolommen.

## Bijlage D — `/factory --light <feature>`

Voor kleine wijzigingen (typo, config, kleine bugfix). Semantiek: spec-writer en
builder draaien als normaal; de reviewronde bevat alleen `reviewer-code` — plus
`reviewer-security` als de diff `auth`, secrets, input-parsing of dependencies raakt,
en `reviewer-privacy` als de diff persoonsgegevens-paden raakt. Approver blijft
verplicht. `job.json` krijgt `"mode": "light"`. Gebruik nooit light voor nieuwe
features of schema-/definitiewijzigingen; stel dan de volledige loop voor.

## Bijlage E — Merge-regel in SKILL.md

Voeg letterlijk toe: "Bij approve merget de factory de jobbranch **lokaal** in de
basisbranch van de worktree. De factory voert nooit `git push`, `gh pr create` of
`glab mr create` uit en verwijdert geen remote branches. Meld na merge: branchnaam,
commit-sha, en dat pushen/PR/MR aan de user is."
