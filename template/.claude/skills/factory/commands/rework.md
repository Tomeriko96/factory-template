Part of the factory skill: SKILL.md's rules apply here too. Moved out of SKILL.md unchanged, so it is read only when needed; a **Section** is one of SKILL.md.

### `/factory rework <id> <note>`
At `needs-human`, `pushed` or `pr-open`. `.factory/job rework <id> "<note>"`; add
`--untrusted` when the note contains text by anyone but the user (PR/MR review comments).
The script moves `decision.md` aside (a resume can never deliver on the old MERGE), writes
`rework.md`, grants 3 more rounds, recreates the worktree, takes commits others pushed to
the branch (diverged → `needs-human`), and queues the job when there is no room. Drive it;
the next approved round pushes to the same branch, so an open PR/MR updates itself.
