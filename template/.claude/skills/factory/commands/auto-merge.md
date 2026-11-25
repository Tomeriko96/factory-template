Part of the factory skill: SKILL.md's rules apply here too. Moved out of SKILL.md unchanged, so it is read only when needed; a **Section** is one of SKILL.md.

**Auto-merge** (only if `delivery.auto_merge` is true and `delivery.draft` is false, and the
`ACTION: deliver` printed `AUTO-MERGE: yes`). `.factory/job` decides: `yes` only for a job that
got here through an approver `MERGE` (or a clean `--docs` precheck), whose precheck says
`AUTO-MERGE: yes` (no issues, no audit deviation — an `⚠️ ENV: <cause, measured load>` row,
caused only by load or network, is not one, nor a `⚠️ TEST: <why> · criterion verified by
<evidence>` row, where a hidden acceptance test guessed wrong and the audit verified the
criterion itself — no file in CI/pipeline config, dependencies,
containers, schema/migrations, auth or `auto_merge_never`), without an approver `HOLD:` line,
and whose branch has no sync in which an agent resolved conflicts (a clean sync does not
count). On `AUTO-MERGE: no (<reasons>)` open the
PR/MR ready for review **without** auto-merge, and if this PR/MR already has it on (after a
rework) switch it off: `gh pr merge <nr> --disable-auto`, or
`glab api -X POST "projects/:id/merge_requests/<iid>/cancel_merge_when_pipeline_succeeds"`.
Say the reasons in the report line: that PR/MR waits for a human.

With `delivery.auto_merge_held: true` a held job prints `AUTO-MERGE: yes (held: <reasons>;
delivery.auto_merge_held overrides the hold)` and a `MERGE:` line: switch auto-merge on as for
`yes`; `pr-body.md` already lists the hold under `## Auto-merge hold overridden`, so use it as it is.
On GitHub, `gh pr merge <nr> --auto --merge --delete-branch` when the repo allows auto-merge, else
wait until CI passes and `gh pr merge <nr> --merge --delete-branch` (the owner's choice for this
flag; it is the one case where the factory merges and deletes the branch). Report the hold reasons
in the report line.

This is the only merge-related action the factory takes, and it is a switch, not a merge: the
forge merges when its own checks pass; the factory never merges directly (except the
`auto_merge_held` case above), never skips checks to get green, never retries them except the one
automatic retry of an infrastructure failure (`CI: INFRA`), never touches approval rules. Auto-merge set right after
creation often fails because the pipeline does not exist yet, and some CLIs fail silently:

- `gitlab`: wait until `glab api "projects/:id/merge_requests/<iid>/pipelines"` lists at
  least one pipeline, then
  `glab api -X PUT "projects/:id/merge_requests/<iid>/merge" -f auto_merge=true`.
  Verify with
  `glab api "projects/:id/merge_requests/<iid>"` → `merge_when_pipeline_succeeds` is true.
- `github`: `gh pr merge <nr> --auto` (the merge method follows the repo's
  setting; add `--squash`/`--merge`/`--rebase` only if the repo allows just one). Verify
  with `gh pr view <nr> --json autoMergeRequest` → not null.

Except under `delivery.auto_merge_held` on GitHub (above), never ask the forge to delete the branch on merge (`--delete-branch`,
`should_remove_source_branch`): the factory never deletes remote branches, and `rework`
needs `factory/<id>` after a merge. The repo's own "delete branch after merge" setting
is the owner's choice.

Not set after a retry, or the MR sits on a conflict or a missing approval → report it and
leave the MR open; never work around it. Report whether auto-merge is on in the same line
as the URL.
