Part of the factory skill: SKILL.md's rules apply here too. Read only when needed; a **Section** is one of SKILL.md.

# Discovery: docs drift

When `/factory next` finds nothing to build and the session looks for new work itself (discovery,
as the session's brief asks), check the docs against the code, next to the tests, linters and the
running app. Stale docs mislead users and the factory's own agents alike.

1. **Collect claims.** In `README*`, `docs/**`, `CONTRIBUTING*`, `AGENTS.md`/`CLAUDE.md`, ADRs and
   `.factory/repo.md`'s source docs: commands (make/just targets, npm/uv scripts, CLI commands and
   flags), env vars, config keys and their defaults, file paths, ports, URLs/routes, and links.
2. **Check each against the code**, read-only and without secrets:
   - targets: `make -n <target>`, `just --list`, `jq .scripts package.json`;
   - CLI flags: `<cli> --help` (through `.factory/heavy` if it starts the app), or grep the parser;
   - env vars and config keys: `git grep -n '<NAME>' -- ':!*.md'` (no hit in code = stale), and the
     default in code vs. the default the doc states;
   - paths: `git ls-files '<path>'` or `test -e`; relative links: the target file and anchor exist;
   - routes: grep the router; ports: the dev/serve config.
   Never read or quote dotenv or secret files; an `.env.example` is fine.
3. **Report only what you reproduced**: a claim with a command whose output contradicts it.
   Search open and closed issues first (`docs`, the file name, the term) to avoid duplicates.
4. **One issue per stale claim group** (one doc section or one topic, e.g. "README: setup
   commands"), labelled `docs` (and `factory:docs` when only docs change), with the evidence:
   per claim `file:line`, the claim, the command and its output, and numbered testable acceptance
   criteria ("README.md names `just dev`, not `make dev`"). When the code is wrong and the doc is
   right, it is a normal bug issue instead.
5. **Build them** as docs jobs: `/factory issue <nr> [<nr>…] --docs` (related groups as one bundle;
   `/factory --docs <text>` without an issue). Report one line: "docs drift → N issues (#a, #b)".
6. The same drift twice in one area (a config file and its doc page)? Propose a `docs.rules`
   entry for it to the user (see `commands/config.md`); never edit config.json yourself.
