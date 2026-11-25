Part of the factory skill: SKILL.md's rules apply here too. Moved out of SKILL.md unchanged, so it is read only when needed; a **Section** is one of SKILL.md.

### `/factory drop <id> ["<reason>"]`
Clears a job nobody wants any more (a leftover `needs-human`, a duplicate, work that landed another
way): `.factory/job drop <id> "<reason>"` → `superseded`, its worktree and unpushed branch are removed.
Only for `needs-human` or `queued` jobs; refused when the job has an open PR/MR (close that on the forge
first). Its issue is free for `/factory next` again. A needs-human job that was never built (round 0)
has nothing to approve: `status` and the board offer `drop` (or `resume`) for it, not `approve`.
