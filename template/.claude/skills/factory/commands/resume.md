Part of the factory skill: SKILL.md's rules apply here too. Moved out of SKILL.md unchanged, so it is read only when needed; a **Section** is one of SKILL.md.

### `/factory resume <id>`
`.factory/job show <id>`; when it lists a pending agent that is not running in this session
(a crashed or cleared session), `.factory/job next <id> --respawn`, else `job next <id>`; drive it. The script knows what is missing: an agent file
that was never written is spawned again (counted as a resume), a queued job starts when
there is room, a job at rest says so.
