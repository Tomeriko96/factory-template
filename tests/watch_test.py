"""Checks for .factory/watch: sections, width, CI summary, detail view, odd job.json files.

  python3 -I tests/watch_test.py

Builds a throwaway .factory/ with jobs in every section and a CI cache, then runs the
board the way a user would (no terminal, so no colours) and checks what it prints.
"""
import json, os, shutil, subprocess, sys, tempfile, time
from datetime import datetime, timedelta, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "template", ".factory")
fails, n = [], 0


def check(ok, msg):
    global n
    n += 1
    if not ok:
        fails.append(msg)


def at(minutes_ago):
    return (datetime.now(timezone.utc) - timedelta(minutes=minutes_ago)).strftime("%Y-%m-%dT%H:%M:%S%z")


def job(jid, stage, **kw):
    j = {"id": jid, "feature": f"feature of {jid}", "mode": "full", "stage": stage, "round": 1,
         "round_budget": 3, "history": [{"stage": "queued", "at": at(90)}, {"stage": stage, "at": at(30)}],
         "updated": at(5), "reviews": {}}
    j.update(kw)
    return j


tmp = tempfile.mkdtemp(prefix="factory-watch-test.")
try:
    fd = os.path.join(tmp, "my-repo", ".factory")
    os.makedirs(os.path.join(fd, "cache"))
    for f in ("watch", "heavy"):
        shutil.copy(os.path.join(SRC, f), fd)
    json.dump({"limits": {"active_jobs": 3, "open_prs": 5}, "delivery": {"mode": "pr"}},
              open(os.path.join(fd, "config.json"), "w"))
    jobs = [
        job("001-blocked-builder-with-a-very-long-name-that-must-be-cut", "needs-human",
            reason="builder blocked in round 1: needs the staging API key"),
        job("002-reviews-running", "review", review_sets={"1": ["code", "security", "audit"]},
            pending={"key": "review-1", "spawns": 2, "at": at(3)}),
        job("003-approving", "approve", precheck="ISSUES", pending={"key": "approve-1", "spawns": 1, "at": at(1)}),
        job("004-waiting", "queued", round=0),
        job("005-open-pr", "pr-open", pr_url="https://github.com/o/r/pull/77",
            history=[{"stage": "pr-open", "at": at(60 * 50)}, {"stage": "pr-open", "at": at(2), "event": "sync 1 pushed"}]),
        job("006-merged", "merged", updated=at(60)),
        job("007-superseded", "superseded", updated=at(60 * 24 * 30)),
        job("008-syncing", "pr-open", pr_url="https://gitlab.example/g/p/-/merge_requests/9",
            syncing={"n": 1}, pending={"key": "sync-1", "spawns": 1, "at": at(4)}),
    ]
    for j in jobs:
        os.makedirs(os.path.join(fd, "jobs", j["id"], "round-1"))
        json.dump(j, open(os.path.join(fd, "jobs", j["id"], "job.json"), "w"))
    open(os.path.join(fd, "jobs", "002-reviews-running", "round-1", "review-code.md"), "w").write("VERDICT: PASS\n")
    open(os.path.join(fd, "jobs", "002-reviews-running", "round-1", "review-security.md"), "w").write("VERDICT: CHANGES\n")
    open(os.path.join(fd, "jobs", "005-open-pr", "round-1", "build.md"), "w").write("BUILD: DONE\n")
    for bad, content in (("009-list", "[]"), ("010-broken", "{oops"), ("011-odd", json.dumps(
            {"stage": 5, "reviews": ["x"], "history": ["a"], "round": "x", "pending": "y"}))):
        os.makedirs(os.path.join(fd, "jobs", bad))
        open(os.path.join(fd, "jobs", bad, "job.json"), "w").write(content)
    json.dump({"pipeline": "failed", "merge": "dirty", "jobs": [
        {"name": "lint", "status": "success"}, {"name": "lint", "status": "failed"},
        {"name": "unit", "status": "success"}, {"name": "unit", "status": "success"}]},
        open(os.path.join(fd, "cache", "ci-005-open-pr.json"), "w"))
    json.dump({"pipelines": [{"branch": "main", "status": "success"}, {"branch": "main", "status": "failed"},
                             {"branch": "refs/merge-requests/12/train", "status": "success"},
                             {"branch": "feat/x", "status": "running"}]},
              open(os.path.join(fd, "cache", "ci-others.json"), "w"))

    env = dict(os.environ, COLUMNS="80", NO_COLOR="1", FACTORY_LOCK_DIR=os.path.join(tmp, "locks"),
               FACTORY_REPOS_FILE=os.path.join(tmp, "repos"))

    def watch(*args, fdir=fd):
        r = subprocess.run([sys.executable, "-I", os.path.join(fdir, "watch"), *args],
                           capture_output=True, text=True, env=env, timeout=60)
        check(r.returncode == 0 or "999" in args, f"watch {args} exit {r.returncode}: {r.stderr[-300:]}")
        return r.stdout

    out = watch("--once")
    if os.environ.get("SHOW"):
        print(out)
    lines = out.splitlines()
    check(all(len(l) <= 80 for l in lines), "a line is wider than 80: " + repr(max(lines, key=len)))
    titles = [l.split(" (")[0] for l in lines if l.split(" (")[0] in ("NEEDS YOU", "RUNNING", "QUEUED", "OPEN PRs", "UNKNOWN STAGE")]
    check(titles == ["NEEDS YOU", "RUNNING", "QUEUED", "OPEN PRs", "UNKNOWN STAGE"], f"section order {titles}")
    check("builder blocked in round 1: needs the staging API key" in out, "needs-human reason not shown in full")
    check("→ /factory approve 001-blocked" in out, "next command for needs-human missing")
    check("blocked-builder-with" in out and "…" in out, "long job name not cut with an ellipsis")
    check("reviews 2/3 ✓✗ · waiting audit (resume 1)" in out, "review progress missing")
    check("approver (opus)" in out, "opus approver after ISSUES not shown")
    check("sync 1: sync builder" in out, "running sync not shown under RUNNING")
    check("waits for a slot" in out, "queued line missing")
    check("005 open-pr" in out and "· 2d" in out.split("005 open-pr")[1].split("\n")[0],
          "PR age not counted from when it was first opened")
    check("#77  ✗ lint  ·  conflict → sync" in out, "PR line: failing check by name and merge state")
    check("unit" not in out, "passing checks are named instead of counted")
    check("DONE  1 merged · 1 superseded · 1 this week" in out and "006" not in out, "DONE line wrong or finished jobs listed")
    check("other CI  main ✓  feat/x ●" in out, "other CI: one cell per branch, latest status")
    check("factory · my-repo" in lines[0] and "active 3/3" in lines[0] and "PRs 1/5" in lines[0], "header wrong: " + lines[0])
    check("011 odd" in out, "odd job.json not shown as unknown stage")

    out = watch("--once", "--compact")
    check(len([l for l in out.splitlines() if l.startswith(" ")]) <= 9, "--compact is not one line per job")
    out = watch("--once", "--all")
    check("006 merged" in out and "007 superseded" in out, "--all does not list finished jobs")
    out = watch("--once", "--no-ci")
    check("lint" not in out and "other CI" not in out, "--no-ci still shows CI")

    # A GitLab MR that is no longer open (merged or closed) while the job still says pr-open
    json.dump({"pipeline": "success", "merge": "not_open", "jobs": [{"name": "t", "status": "success"}]},
              open(os.path.join(fd, "cache", "ci-005-open-pr.json"), "w"))
    out = watch("--once")
    check("no longer open → sync" in out, "a merged/closed MR is not flagged as stale")
    check("refs/merge-requests" not in out, "GitLab merge-request refs shown under other CI")
    nxt = {d["id"]: d["next"] for d in json.loads(watch("--json"))}
    check(nxt.get("005-open-pr") == "/factory sync 005-open-pr", f"next for a no-longer-open MR: {nxt.get('005-open-pr')}")
    json.dump({"pipeline": "failed", "merge": "dirty", "jobs": [
        {"name": "lint", "status": "success"}, {"name": "lint", "status": "failed"},
        {"name": "unit", "status": "success"}, {"name": "unit", "status": "success"}]},
        open(os.path.join(fd, "cache", "ci-005-open-pr.json"), "w"))

    data = json.loads(watch("--json"))
    sec = {d["id"]: d["section"] for d in data}
    check(sec.get("001-blocked-builder-with-a-very-long-name-that-must-be-cut") == "needs"
          and sec.get("008-syncing") == "running" and sec.get("006-merged") == "done"
          and sec.get("005-open-pr") == "prs", f"--json sections {sec}")
    check(next(d for d in data if d["id"] == "005-open-pr")["next"] == "/factory sync 005-open-pr",
          "--json next command for a conflicting PR")

    out = watch("002")
    check("002-reviews-running · my-repo · full · review · round 1/3" in out, "detail header wrong")
    check("timeline" in out and "← now" in out and "next     /factory resume 002" in out, "detail timeline/next missing")
    check("reviews" in out and "code" in out and "security" in out, "detail review matrix missing")
    out = watch("005")
    check("BUILD: DONE" in out and "failed   lint" in out and "passed   1 checks" in out, "detail files/CI wrong")
    check("no job" in watch("999"), "unknown job id not reported")

    # A second repo, both registered: --repos shows them together, with the repo in each card
    fd2 = os.path.join(tmp, "other-repo", ".factory")
    os.makedirs(os.path.join(fd2, "jobs", "001-elsewhere"))
    json.dump(job("001-elsewhere", "needs-human", reason="approver escalated"),
              open(os.path.join(fd2, "jobs", "001-elsewhere", "job.json"), "w"))
    open(env["FACTORY_REPOS_FILE"], "w").write(f"{os.path.dirname(fd)}\n{os.path.dirname(fd2)}\n/nonexistent\n")
    out = watch("--once", "--repos")
    check("factory · 2 repos" in out and "other-repo/001 elsewhere" in out and "my-repo/001 blocked" in out,
          "--repos does not show both repos with their names")
    check(out.index("NEEDS YOU (2)") < out.index("RUNNING"), "--repos does not merge sections across repos")

    # The interactive board: every key, wide and narrow, through a pseudo-terminal
    import pty, fcntl, termios, struct, select
    for cols in (80, 160):
        pid, master = pty.fork()
        if pid == 0:
            os.environ.update(env, TERM="xterm-256color")
            os.environ.pop("NO_COLOR", None)
            os.execv(sys.executable, [sys.executable, "-I", os.path.join(fd, "watch"), "--no-ci"])
        fcntl.ioctl(master, termios.TIOCSWINSZ, struct.pack("HHHH", 40, cols, 0, 0))
        screen = b""

        def drain(t=0.4):
            global screen
            end = time.time() + t
            while time.time() < end:
                r, _, _ = select.select([master], [], [], 0.05)
                if r:
                    try:
                        screen += os.read(master, 65536)
                    except OSError:
                        return

        drain(1.5)
        for k in ["j", "j", "k", "l", "h", "\r", "j", "\x1b", "a", "v", "v", "/", "open", "\r", "c", "\x1b",
                  "?", "x", "R", "r", "\x1b[B", "\x1b[A", "\r", "\x1b"]:
            os.write(master, k.encode())
            drain(0.25)
        os.write(master, b"q")
        drain(1)
        _, status = os.waitpid(pid, 0)
        os.close(master)
        text = screen.decode(errors="replace")
        check(os.WEXITSTATUS(status) == 0 and "Traceback" not in text, f"TUI at {cols} columns: exit {status}, "
              + (text[text.find('Traceback'):][:400] if "Traceback" in text else ""))
        check("NEEDS YOU" in text and "001" in text, f"TUI at {cols} columns shows no board")
        check("copied:" in text or "copy this:" in text or "nothing to copy" in text, f"TUI at {cols}: c gave no message")

    # .factory/ci with a fake `gh`: a PR that merged on the forge reports merge=merged, not
    # the UNKNOWN that mergeStateStatus is for a PR that is no longer open
    cd = os.path.join(tmp, "ci-repo", ".factory")
    os.makedirs(os.path.join(cd, "cache"))
    os.makedirs(os.path.join(tmp, "bin"))
    shutil.copy(os.path.join(SRC, "ci"), cd)
    json.dump({"forge": "github"}, open(os.path.join(cd, "config.json"), "w"))
    for jid in ("003-open",):
        jdir = os.path.join(cd, "jobs", jid)
        os.makedirs(jdir)
        json.dump(job(jid, "pr-open", pr_url="https://github.com/o/r/pull/" + str(len(jid)), branch="factory/" + jid),
                  open(os.path.join(jdir, "job.json"), "w"))
    gh = os.path.join(tmp, "bin", "gh")
    open(gh, "w").write("#!/bin/sh\n[ \"$1\" = run ] && { echo '[]'; exit 0; }\n"
                        "echo '{\"number\":1,\"state\":\"'$GH_STATE'\",\"mergeStateStatus\":\"'$GH_MERGE'\",\"statusCheckRollup\":[]}'\n")
    os.chmod(gh, 0o755)
    for state, merge, want in (("MERGED", "UNKNOWN", "merged"), ("CLOSED", "UNKNOWN", "closed"), ("OPEN", "CLEAN", "clean")):
        env = dict(os.environ, PATH=os.path.join(tmp, "bin") + os.pathsep + os.environ["PATH"],
                   GH_STATE=state, GH_MERGE=merge)
        subprocess.run([sys.executable, "-I", os.path.join(cd, "ci"), "--once", "--ttl", "0", "--quiet", "003-open"],
                       env=env, capture_output=True, text=True, cwd=tmp)
        c = json.load(open(os.path.join(cd, "cache", "ci-003-open.json")))
        check(c.get("merge") == want, f"ci: PR {state} (mergeStateStatus {merge}) gives merge={c.get('merge')}, want {want}")
finally:
    if os.environ.get("KEEP"):
        print("kept", tmp)
    else:
        shutil.rmtree(tmp, ignore_errors=True)

for f in fails:
    print("FAIL", f)
print(f"watch_test: {n - len(fails)}/{n} ok")
sys.exit(1 if fails else 0)
