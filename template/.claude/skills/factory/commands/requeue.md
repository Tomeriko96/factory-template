Part of the factory skill: SKILL.md's rules apply here too. Moved out of SKILL.md unchanged, so it is read only when needed; a **Section** is one of SKILL.md.

### `/factory requeue <id> ["<reason>"]`
`.factory/job requeue <id>`: a job that has not started real work (`queued`, or at `spec` before its
first build) goes to the end of the queue with its state kept (spec.md, acceptance tests, worktree);
its slot goes to the next queued job. Use it to change the order of the queue ("merge first") or to
make room; never `drop` a job and start it again for that (that made jobs 003/026 and 004/023 of one
repo: two jobs per issue). A running build or review is not requeued: let it finish.
