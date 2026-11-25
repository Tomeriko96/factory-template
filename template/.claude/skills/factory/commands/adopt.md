Part of the factory skill: SKILL.md's rules apply here too. Moved out of SKILL.md unchanged, so it is read only when needed; a **Section** is one of SKILL.md.

### `/factory adopt <pr|mr nr>`
Merge conflicts are always fixed through the factory, also on a PR/MR it did not make (e.g. a
branch `feat/682-…` that conflicts with `main`). `.factory/job adopt <nr>` reads the PR/MR from the
forge and refuses one that is not open, whose author is not in `issues.allowed_authors`, or that
comes from a fork (report the reason; never work around it). It records a minimal job at `pr-open`
(`adopted: true`): branch = the PR/MR's own source branch (fetched into a local branch of the same
name, never renamed), base = its target branch, `issues` = what its description closes, the PR/MR as
its delivery. It then asks the forge for the merge state: `ACTION: sync` → run `.factory/job sync
<id>` and drive it exactly as in `/factory sync`, with two differences the script handles: the
sync builder's prompt says `Adopted PR/MR` (merge the target branch in, resolve the conflicts, run
only the tests that cover the conflicted files through heavy: no full validation), and there is no
code review of the merge (`SYNC: CLEAN|RESOLVED` → `ACTION: push` at once). Push with the printed
command to the same branch (never `--force`), then `.factory/job sync-done <id>`.
`AUTO-MERGE: no` → switch auto-merge off before the push; `AUTO-MERGE: keep` → leave it as it is.
An adopted job never gets a spec, acceptance tests, build or review rounds, an approver or a rework
(`rework`/`approve` are refused): it is only a merge-conflict patch. `SYNC: NEEDS-HUMAN` →
`needs-human` with the reason; `.factory/job sync <id>` tries again later, `.factory/job drop <id>`
forgets the adoption (the PR/MR and its branch stay). A later conflict on it is caught by
`/factory sync` / `status` like any `pr-open` job (or `job next <id>`) and patched again.
