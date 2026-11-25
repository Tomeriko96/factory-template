Part of the factory skill: SKILL.md's rules apply here too. Moved out of SKILL.md unchanged, so it is read only when needed; a **Section** is one of SKILL.md.

### Closing issues: the rules `.factory/job close-issues` applies

Unless `issues.close_on_merge` is `false`, the factory closes a job's issue once the forge
confirms its PR/MR is merged. It runs when a merge is noticed (`/factory sync`, also
`/loop 10m /factory sync`; the check at the end of delivery; `/factory status`) and for any
job at `merged` with an issue (a bundle: with issues not yet in `issue_closed`) and no `issue_closed`, so older merged jobs are caught up.
All of these must hold, otherwise do nothing (and say why in one line):

Do this for **each** issue of the job (`"issues"` for a bundle, else `"issue"`); the checks below are per issue.
1. The job came from the issue (`"issue": <nr>` or `<nr>` in `"issues"`), has `pr_url`, and its `job.json`
   `delivery.mode` is `pr` (how this job was delivered; a local merge or a bare push has
   not reached the forge's base branch). A job without a `delivery` field (made before
   `.factory/job`) counts when it has a `pr_url`.
2. The forge says the PR/MR is merged, into the job's `base`: `gitlab`:
   `glab api "projects/:id/merge_requests/<iid>"` → `state` is `merged`; `github`:
   `gh pr view <nr> --json state,baseRefName` → `MERGED`. Closed without merge never counts.
3. The issue is still open (`glab issue view <nr> --output json` → `state` `opened`; `gh issue
   view <nr> --json state` → `OPEN`). Already closed (e.g. by `Closes #<nr>`) →
   `.factory/job set <id> issue_closed "already closed"` (a bundle: see below).
4. No other job with the same issue (in `issue` or `issues`) is still in progress (stage `queued`, `spec`,
   `build`, `review`, `approve`, `deliver` or `pr-open`): then the issue is not done yet;
   set nothing and report it. A sibling at `needs-human` does not block.

Close: `gitlab`: `glab issue close <iid>`; `github`: `gh issue close <nr> --reason
completed`. With `"report": true` add a one-line comment first: `Merged: <pr_url>`. Then
verify the issue is closed, `.factory/job set <id> issue_closed "<ISO8601>"` and report `closed
#<nr> (job <id>, <pr_url>)`. For a bundle `issue_closed` is a JSON object `{"<nr>": "<ISO8601 or
reason>"}` that you extend per issue (`job set <id> issue_closed '{"12": "…", "14": "…"}'`, all entries
so far); the job counts as closed when every issue of it is in it. Fails → report the error, leave `issue_closed` null (it is
tried again on the next run). Never reopen an issue, never close one that is not in the
job's `issue`/`issues`, never close on a closed-without-merge PR/MR.
