Part of the factory skill: SKILL.md's rules apply here too. Moved out of SKILL.md unchanged, so it is read only when needed; a **Section** is one of SKILL.md.

## Resources

This container has a few cores, and a job fans out into a builder plus up to six
reviewers. Unchecked, parallel jobs ran at load 20–33 on 8 cores: tests timed out,
reruns and false "flaky" findings cost extra rounds. Three guards:

1. **`limits.active_jobs`** (Constants): `.factory/job` never lets more jobs in flight.
2. **Load gate:** before every spawn of a spec-writer, builder or review wave run
   `<repo>/.factory/heavy gate` (Bash timeout 600000). It returns when the CPU is at or
   below its limit (90%, sampled over a second), or after 10 minutes with a warning; then
   continue and mention the warning in your next report. Do not poll the load yourself.
3. **`.factory/heavy`** for every test, build, lint, install and validation command the
   agents run, in every repo on this machine. Each command has a weight (the cores it may
   use: 3 for Node, browser and build tools, 1 for the rest); the weights running at the
   same time, host-wide, stay within the cores (at most max(2, cores − 1) commands; `--timeout SECS`
   counts only the run, never the queue; a long output shows its first 20 and last 150 lines, the
   rest is in the run log). It runs at low priority and passes
   `FACTORY_CPUS` (its weight) for worker counts. A command that may wait or run longer
   than a tool call lives goes `heavy --background -- <cmd>` (returns a ticket) and
   `heavy wait <ticket>` (repeat while it exits 124). `.factory/heavy status` shows who
   holds capacity, who waits (with priority) and the CPU. Every run ends with the line
   `heavy: exit=<n> log=<path>` (also on a refusal, exit 75); the guard refuses piping
   heavy's output (`heavy … | tail`) unless the command sets `set -o pipefail`.
   It also refuses `pkill`/`killall` (by name or pattern they hit other sessions' processes):
   stop your own work by PID (`kill $!`), `heavy cancel <ticket>` or `serve stop <port>`.
   **Priority** (`--priority high|normal|low`, env `FACTORY_HEAVY_PRIORITY`, default
   normal): a waiter only takes a free slot when no waiter of a higher priority, and no
   older waiter of the same priority, is queued (FIFO, so a big build is not starved; stale waiters whose process is gone are ignored). The precheck's full validation and
   the builder run at high; audits and timing/measurement runs at low ("audits:
   `.factory/heavy --priority low …`"); everything else normal. `.factory/watch` shows the
   priority next to each heavy command.

`rework`, `resume` and `sync` move a job back into `build`/`review`: the script applies
the same capacity check (a rework without room is queued; a sync needs no job slot, only room
under `limits.active_syncs`, else it is "postponed" and retried on the next `status`/`sync`/`next`),
and every spawn has the load gate.

These rules are not left to the agents' good will: every factory agent has a `PreToolUse`
hook, `.factory/guard`, that refuses a test, build, install or type-check command which is
not run through `heavy` and tells the agent what to do instead (Claude Code runs it for
subagents in trusted workspaces, also in bypass mode; `limits.guard: false` turns it off).

**Targeted tests during the build, the full suite once.** Builders and reviewers run only
the tests related to the change (the test files of the touched modules, a path or `-k`),
never with coverage; repo.md's Validate commands run once per round, in the precheck step
(`ACTION: validate`), through `heavy`. Coverage is left to CI. `--cache` makes each
command run once per commit instead of once per agent: a passing run is recorded for the
exact tree, and the other agents get an instant "CACHE HIT" for the same command on the
same tree. A new commit, a dirty tree or a
different command runs for real. The agents' prompts say how to use it; you only need to
make sure each agent prompt keeps the paths block (the worktree path is part of the key).
