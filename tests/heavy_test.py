"""Tests for template/.factory/heavy: the default limits, --timeout (the queue does not count) and
the capped output of a foreground run.

  python3 -I tests/heavy_test.py

Runs heavy from a throwaway directory with its own lock dir, so it never shares slots with real
factory sessions on this machine.
"""
import importlib.machinery, importlib.util, os, shutil, subprocess, sys, tempfile, time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "template", ".factory", "heavy")
fails, n = [], 0


def check(ok, msg):
    global n
    n += 1
    if not ok:
        fails.append(msg)


def load():
    sys.dont_write_bytecode = True
    loader = importlib.machinery.SourceFileLoader("factory_heavy", SRC)
    spec = importlib.util.spec_from_loader("factory_heavy", loader)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


H = load()
# Defaults (v0.19.0): slots = max(2, cores - 1), budget = cores. On a 4-core host the old ones
# (max(2, cores/2) = 2 slots, 75% = 3) left six commands queued at 34% CPU.
check(H.default_slots(4) == 3 and H.default_budget(4) == 4, f"4 cores: {H.default_slots(4)} slots, budget {H.default_budget(4)}")
check(H.default_slots(1) == 2 and H.default_budget(1) == 1, "1 core: at least 2 slots, budget 1")
check(H.default_slots(2) == 2 and H.default_slots(8) == 7 and H.default_budget(8) == 8, "2/8 cores")
check(H.limits()["cpu_max"] == 90.0 and H.limits()["load_max"] is None, "the CPU% and load_max guards changed")
check("cores - 1" in H.__doc__ and "cpu_budget = the\ncores" in H.__doc__, "the docstring does not state the new defaults")

tmp = tempfile.mkdtemp(prefix="factory-heavy-test.")
try:
    d = os.path.join(tmp, "repo")
    os.makedirs(os.path.join(d, ".factory"))
    shutil.copy(SRC, os.path.join(d, ".factory", "heavy"))
    heavy = os.path.join(d, ".factory", "heavy")
    env = dict(os.environ, FACTORY_LOCK_DIR=os.path.join(tmp, "locks"), FACTORY_CPU_MAX="100",
               FACTORY_HEAVY_SLOTS="1", FACTORY_CPU_BUDGET="8")
    env.pop("FACTORY_HEAVY", None)
    env.pop("FACTORY_HEAVY_TAIL", None)

    def run(*args, **kw):
        return subprocess.run([heavy, *args], cwd=d, env=dict(env, **kw.pop("extra", {})),
                              capture_output=True, text=True, timeout=120, **kw)

    # env overrides still win
    r = subprocess.run([sys.executable, "-c", "import importlib.machinery as m, importlib.util as u, sys;"
                        "sys.dont_write_bytecode=True;l=m.SourceFileLoader('h', sys.argv[1]);s=u.spec_from_loader('h', l);"
                        "h=u.module_from_spec(s);l.exec_module(h);x=h.limits();print(x['slots'], x['budget'])", heavy],
                       env=dict(env, FACTORY_HEAVY_SLOTS="5", FACTORY_CPU_BUDGET="6"), capture_output=True, text=True)
    check(r.stdout.split() == ["5", "6"], f"env overrides: {r.stdout!r} {r.stderr[-200:]!r}")

    # --timeout counts the run, not the queue: one slot, held 3 s by a background run; a 1 s
    # command with --timeout 2 waits ~3 s for the slot and still finishes
    r = run("--background", "--", "sleep", "3")
    check(r.returncode == 0 and r.stdout.startswith("ticket "), f"background: {r.stdout!r}")
    tid = r.stdout.split()[1]
    deadline = time.time() + 10
    while time.time() < deadline:   # until the background run holds the slot
        st = subprocess.run([heavy, "status"], cwd=d, env=env, capture_output=True, text=True).stdout
        if "sleep 3" in st:
            break
        time.sleep(0.2)
    t0 = time.time()
    r = run("--timeout", "2", "--", "sleep", "1")
    took = time.time() - t0
    check(r.returncode == 0, f"--timeout counted the queue: rc {r.returncode}, {took:.1f}s, {r.stderr[-300:]!r}")
    check(took > 1.8, f"the second command did not wait for the slot ({took:.1f}s)")
    run("wait", tid)
    # … and does stop a command that runs too long
    t0 = time.time()
    r = run("--timeout", "1", "--", "sleep", "20")
    check(r.returncode == 124 and time.time() - t0 < 10, f"--timeout did not stop the command: rc {r.returncode}")
    check("--timeout; the time it waited for a slot does not count" in r.stderr, f"--timeout message: {r.stderr[-300:]!r}")
    check(r.stdout.rstrip().splitlines()[-1].startswith("heavy: exit=124 log="), "no result line after --timeout")

    # a long output: the first 20 and the last 150 lines, the rest only in the run log
    prog = "import sys\nfor i in range(5000): print('line', i, 'x' * 60)\nsys.exit(3)\n"
    with open(os.path.join(d, "long.py"), "w") as f:
        f.write(prog)
    r = run("--", sys.executable, "long.py")
    lines = r.stdout.splitlines()
    check(r.returncode == 3, f"exit code not passed on: {r.returncode}")
    check(lines[0].startswith("line 0 ") and lines[19].startswith("line 19 "), "the head is missing")
    check("4830 lines omitted (all 5000 in" in lines[20], f"no omission line: {lines[20][:120]!r}")
    check(lines[-2].startswith("line 4999 ") and lines[-1].startswith("heavy: exit=3 log="), "the tail or the result line is missing")
    log = lines[-1].split("log=", 1)[1]
    check(sum(1 for _ in open(log)) >= 5000, "the run log does not hold the whole output")
    check("full output in " + log in r.stderr, "the log path is not named first (stderr)")
    print(f"heavy_test: 5000-line output: {len(r.stdout)} chars to the caller, {os.path.getsize(log)} before")
    check(len(r.stdout) < 20000, f"capped output still {len(r.stdout)} chars")
    r = run("--full-output", "--", sys.executable, "long.py")
    check(len(r.stdout.splitlines()) == 5001, "--full-output did not print everything")
    r = run("--", sys.executable, "long.py", extra={"FACTORY_HEAVY_TAIL": "0"})
    check(len(r.stdout.splitlines()) == 5001, "FACTORY_HEAVY_TAIL=0 did not print everything")
    r = run("--tail", "5", "--", sys.executable, "long.py")
    check(len(r.stdout.splitlines()) == 20 + 1 + 5 + 1, f"--tail 5: {len(r.stdout.splitlines())} lines")
    # a file the caller redirected to gets everything (data, not context)
    with open(os.path.join(d, "out.txt"), "w") as out:
        rc = subprocess.run([heavy, "--", sys.executable, "long.py"], cwd=d, env=env, stdout=out,
                            stderr=subprocess.DEVNULL).returncode
    check(rc == 3 and sum(1 for _ in open(os.path.join(d, "out.txt"))) == 5001, "a redirected stdout was cut")
    # a short output is unchanged
    r = run("--", "echo", "hi")
    check(r.stdout.splitlines() == ["hi", r.stdout.splitlines()[-1]] and r.returncode == 0, f"short output: {r.stdout!r}")

    # exit 75 says it is no result and what to do
    r = run("--background", "--", "sleep", "4")
    tid = r.stdout.split()[1]
    time.sleep(1)
    r = run("--wait-max", "1", "--", "echo", "never")
    check(r.returncode == 75 and "no result, not a pass" in r.stderr and "--background" in r.stderr,
          f"exit 75 message: rc {r.returncode} {r.stderr[-300:]!r}")
    # heavy wait on a queued ticket: still queued, not a failure
    r2 = run("--background", "--", "echo", "queued")
    tq = r2.stdout.split()[1]
    r = run("wait", tq, "--timeout", "1")
    check(r.returncode == 124 and "still queued" in r.stderr and "not a failure" in r.stderr,
          f"wait on a queued ticket: rc {r.returncode} {r.stderr[-300:]!r}")
    run("wait", tid)
    run("wait", tq)
finally:
    shutil.rmtree(tmp, ignore_errors=True)

for f in fails:
    print("FAIL", f)
print(f"heavy_test: {n - len(fails)}/{n} ok")
sys.exit(1 if fails else 0)
