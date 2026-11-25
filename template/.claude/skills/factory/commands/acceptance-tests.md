Part of the factory skill: SKILL.md's rules apply here too. Moved out of SKILL.md unchanged, so it is read only when needed; a **Section** is one of SKILL.md.

## Hidden acceptance tests

With `acceptance_tests` on for the job's mode, `.factory/job` spawns
**factory-acceptance-writer** (sonnet) after the spec and before round 1: from spec.md's
numbered acceptance criteria only, it writes tests into the job folder (`acceptance/`, at
their worktree-relative paths) and `acceptance.md` (`ACCEPTANCE: WRITTEN` with a `Run:`
command and a criterion → test table, or `ACCEPTANCE: NONE <reason>`). The builder is never
told about them and is instructed not to look. Every round the audit reviewer's prompt
gets a `Hidden acceptance tests:` line: it copies them into the worktree, runs them through
`heavy`, removes them in the same call and reports one row per criterion (a test that failed
only on a wrong assumption, with the criterion verified independently, is `⚠️ TEST: … ·
criterion verified by …` and goes to the job's `acceptance-notes.md`, which later writers
read). You never read or relay their content.
