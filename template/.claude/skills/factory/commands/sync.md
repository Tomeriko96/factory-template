Part of the factory skill: SKILL.md's rules apply here too. Moved out of SKILL.md unchanged, so it is read only when needed; a **Section** is one of SKILL.md.

### `/factory sync [<id>]`
Keeps open PRs/MRs mergeable. `.factory/job prs [<id>]` does the asking for every job at `pr-open`
(or one): `MERGED:` lines (the job is marked merged and its issues closed), `CLOSED:` (closed
without merge: the job went to `needs-human`), `UNKNOWN:` (ask again later), and `ACTION: sync` with
one `SYNC:`/`RUN:` pair per PR/MR that conflicts with or is behind the base. It also asks about every
**unfinished** job (queued, running, `needs-human`) that has a PR/MR already (`validate.mode: ci` opens
it before delivery) or a pushed branch with an open one: `OPEN: <id> …: job at <stage>, pipeline
<state>` (count them as open MRs; never conclude "no open MRs" from the `pr-open` jobs alone),
`MERGED:` (merged on the forge while the job waited at `needs-human`: marked merged), and
`RESUME: <id>` (its last validation failed on infrastructure and the head pipeline is green now:
the validation counts as passed, run `job next <id>`; never build another round for it). After a
long pause run `job prs` before anything else. What it asks the forge:

- `gitlab`: `glab api "projects/:id/merge_requests/<iid>"` → conflict when
  `has_conflicts` is true or `detailed_merge_status` is `conflict` or `need_rebase`.
  `checking` / `unchecked` is not an answer: look again after a short wait, at most
  three times, then report "unknown".
- `github`: `gh pr view <nr> --json mergeable,mergeStateStatus` → conflict when
  `mergeable` is `CONFLICTING` (`mergeStateStatus` `DIRTY`); `BEHIND` counts only if the
  repo requires up-to-date branches.

PR/MR already merged → `.factory/job pr-merged <id>`, then `.factory/job close-issues <id>` (`job prs` does both); closed
without merge → `.factory/job fail <id> "PR/MR closed without merge"`. Report it and skip
it. No conflict → nothing to do. Conflict → `.factory/job sync <id>` and drive it:

1. The script checks the sync budget (`limits.max_syncs`, then `needs-human`) and `limits.active_syncs`
   (default 2 at once; more → `WAIT: sync postponed`, retried on the next `status`/`sync`/`next`; a
   sync never waits for a job slot), recreates the
   worktree and takes commits others pushed to the branch (diverged → `needs-human`).
2. It spawns a sonnet `factory-builder` with `Sync <n>`: it merges `<remote>/<base>` into
   the job branch (a merge commit: never rebase, never force-push), resolves the
   conflicts, runs the validation and writes `sync-<n>/build.md` (`SYNC: CLEAN` when git
   merged without conflicts, `SYNC: RESOLVED` when it resolved conflicts, or
   `SYNC: NEEDS-HUMAN`). A conflict sonnet cannot settle ends as `NEEDS-HUMAN`, not as a
   guess. The script checks the merge commit with `git merge-tree` and records per sync
   whether it had conflicts (`job.json` `sync.conflicts`).
3. `SYNC: NEEDS-HUMAN` → `needs-human`; the PR/MR stays open and untouched. This is the
   right outcome when `base` already fixes the same thing in a different way (the job is
   then probably superseded: say so and suggest closing the PR/MR), when both sides change
   the same behaviour, or when validation fails after the merge. Never resolve such a
   conflict by picking a side.
4. `SYNC: CLEAN` or `SYNC: RESOLVED` → it spawns `factory-reviewer-code` with `Review sync <n>`
   (checks that nothing of either side was lost). `CHANGES` → `needs-human`. `PASS` →
   `ACTION: push`, with (when `delivery.auto_merge` is on) an `AUTO-MERGE:` line:
   - `AUTO-MERGE: no (<reasons>)`: switch auto-merge **off** before the push (see Delivery
     for the command). A sync where an agent resolved conflicts always gives this: a human
     merges it, and `.factory/job` keeps it off at every later delivery.
   - `AUTO-MERGE: yes`: a clean sync (no conflicts, validation passes) of a job whose gate
     allows it: after the push switch auto-merge **on again** and verify it (some forges
     drop it on a new push), as in Delivery.
   Then run the printed push (never `--force`), check the PR/MR is mergeable again, then
   `.factory/job sync-done <id>` (push rejected → `.factory/job fail <id> "<error>"`). Report
   one line per job: id, MR, clean/resolved, and whether auto-merge is on.

Runs automatically, check **and** fix: at the end of every delivery, on every `status`,
and whenever you notice that a PR/MR got merged (every merge can make the other open
PRs/MRs conflict: then run it for all other jobs at `pr-open`). Jobs that are not
checked for a while (nobody calls `status`) are caught by `/loop 10m /factory sync`.
