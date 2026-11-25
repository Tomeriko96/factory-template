Part of the factory skill: SKILL.md's rules apply here too. Moved out of SKILL.md unchanged, so it is read only when needed; a **Section** is one of SKILL.md.

### `/factory pause ["<reason>"]` / `/factory unpause`
"Finish what runs, start nothing new": `.factory/job pause "<reason>"` writes `.factory/paused`.
While paused no queued job starts (`job next` on it prints `WAIT: queued: the factory is paused …`,
a freed slot starts nothing); running jobs, syncs, `adopt` and delivery go on as usual, and a new
job (`/factory <feature>`, `issue`, `next`) is only queued, so say that when you create one. Never
park (`fail`) or `drop` jobs to stop the queue: pause keeps it. `.factory/job unpause` ends the pause
and starts queued jobs while there is room: drive every `STARTED:` job with `job next`. The board
and `job list` show `PAUSED`.
