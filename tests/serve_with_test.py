"""Checks for .factory/serve-with: servers up for the command, always down afterwards.

  python3 -I tests/serve_with_test.py

Two dummy `python3 -m http.server` servers (one on a free port the test picks, one on
`--port auto`), a command that fetches both, then: both process groups and ports are gone,
also after a failing command, a server that never starts and a SIGINT; two runs side by side
get different ports and temporary dirs; shoot's `--serve` builds the serve-with call.
"""
import importlib.machinery, importlib.util, os, re, shutil, signal, socket, subprocess, sys, time

sys.dont_write_bytecode = True
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SW = os.path.join(ROOT, "template", ".factory", "serve-with")
fails, n = [], 0


def check(ok, msg):
    global n
    n += 1
    if not ok:
        fails.append(msg)


def free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def in_use(port):
    with socket.socket() as s:
        s.settimeout(0.5)
        return s.connect_ex(("127.0.0.1", port)) == 0


def alive(pgid):
    try:
        os.killpg(pgid, 0)
        return True
    except ProcessLookupError:
        return False


SERVER = f"{sys.executable} -m http.server {{port}} --bind 127.0.0.1"
if shutil.which("curl"):
    FETCH = "curl -sf -o /dev/null http://127.0.0.1:{p}/"
else:
    FETCH = sys.executable + " -c \"import urllib.request; urllib.request.urlopen('http://127.0.0.1:{p}/')\""


def run(cmd_after, *servers, extra=(), timeout=60):
    argv = [SW, *extra]
    for port in servers:
        argv += ["--server", SERVER, "--port", str(port), "--ready", "/"]
    p = subprocess.run(argv + ["--"] + cmd_after, capture_output=True, text=True, timeout=timeout)
    pgids = [int(x) for x in re.findall(r"\(pgid (\d+)\)", p.stderr)]
    ports = [int(x) for x in re.findall(r"ready on port (\d+)", p.stderr)]
    return p, pgids, ports


def gone(pgids, ports, what):
    time.sleep(0.2)
    check(pgids and not any(alive(g) for g in pgids), f"{what}: a server process group is still alive: {pgids}")
    check(ports and not any(in_use(p) for p in ports), f"{what}: a port is still in use: {ports}")


# 1. two servers, a command that fetches both, everything gone afterwards
fixed = free_port()
both = FETCH.format(p="{port1}") + " && " + FETCH.format(p="{port2}") + " && echo fetched $SERVE_WITH_PORTS"
p, pgids, ports = run(["sh", "-c", both], fixed, "auto")
check(p.returncode == 0, f"two servers: exit {p.returncode}\n{p.stderr}")
check("fetched" in p.stdout and len(ports) == 2 and ports[0] == fixed and ports[1] != fixed,
      f"two servers: command did not reach both: {p.stdout!r} {ports}")
gone(pgids, ports, "two servers")

# 2. a failing command: its exit code, still torn down
p, pgids, ports = run(["sh", "-c", FETCH.format(p="{port}") + " && exit 7"], "auto", "auto")
check(p.returncode == 7, f"failing command: exit {p.returncode}, want 7\n{p.stderr}")
gone(pgids, ports, "failing command")

# 3. a fixed port that is in use is refused; a server that dies is exit 3, the other one stopped
with socket.socket() as busy:
    busy.bind(("127.0.0.1", 0))
    busy.listen()
    p, _, _ = run(["true"], busy.getsockname()[1])
    check(p.returncode == 3 and "already in use" in p.stderr, f"busy port: exit {p.returncode} {p.stderr!r}")
p = subprocess.run([SW, "--timeout", "20", "--server", SERVER, "--port", "auto", "--ready", "/",
                    "--server", "echo boom; exit 5", "--port", "auto", "--", "true"],
                   capture_output=True, text=True, timeout=60)
pg = [int(x) for x in re.findall(r"\(pgid (\d+)\)", p.stderr)]
check(p.returncode == 3 and "boom" in p.stderr, f"dying server: exit {p.returncode}, no log tail: {p.stderr!r}")
check(not any(alive(g) for g in pg), "dying server: the healthy server was left running")

# 4. SIGINT (Ctrl-C) while the command runs: everything stopped, exit 130
proc = subprocess.Popen([SW, "--server", SERVER, "--port", "auto", "--ready", "/", "--",
                         "sh", "-c", "echo CMDPID=$$ >&2; exec sleep 60"], stderr=subprocess.PIPE, text=True)
err, end = "", time.time() + 30
while not re.search(r"CMDPID=\d", err) and time.time() < end:
    err += proc.stderr.readline()
cmd_pid = int(re.search(r"CMDPID=(\d+)", err).group(1))
proc.send_signal(signal.SIGINT)
err += proc.communicate(timeout=30)[1]
pgids = [int(x) for x in re.findall(r"\(pgid (\d+)\)", err)]
ports = [int(x) for x in re.findall(r"ready on port (\d+)", err)]
check(proc.returncode == 130, f"SIGINT: exit {proc.returncode}\n{err}")
gone(pgids, ports, "SIGINT")
check(not alive(cmd_pid), "SIGINT: the command was left running")

# 5. two runs side by side: own ports, own temporary dirs, both removed
cmd = ["sh", "-c", "echo $SERVE_WITH_TMP {name} {port}; sleep 1"]
a = subprocess.Popen([SW, "--server", SERVER, "--port", "auto", "--", *cmd], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
b = subprocess.Popen([SW, "--server", SERVER, "--port", "auto", "--", *cmd], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
oa, ob = a.communicate(timeout=60)[0].split(), b.communicate(timeout=60)[0].split()
check(a.returncode == 0 and b.returncode == 0, f"parallel: exits {a.returncode} {b.returncode}")
check(len(oa) == 3 and len(ob) == 3 and all(x != y for x, y in zip(oa, ob)), f"parallel runs share a name/dir/port: {oa} {ob}")
check(oa and ob and not os.path.exists(oa[0]) and not os.path.exists(ob[0]), "parallel: temporary dirs left behind")

# 6. usage errors
for argv, why in ([[SW, "--server", "x", "--", "true"], "no --port"], [[SW, "--port", "1", "--", "true"], "--port first"],
                  [[SW, "--server", "x", "--port", "auto"], "no --"]):
    check(subprocess.run(argv, capture_output=True).returncode == 2, f"usage: {why} not exit 2")

# 7. shoot --serve: the call runs again under serve-with, without the --serve options
loader = importlib.machinery.SourceFileLoader("shoot", os.path.join(ROOT, "template", ".factory", "shoot"))
spec = importlib.util.spec_from_loader("shoot", loader)
shoot = importlib.util.module_from_spec(spec)
loader.exec_module(shoot)   # no playwright needed: it is imported in main()
got = shoot.serve_argv(["http://localhost:{port}", "--out", "o", "--serve", "npm run dev", "--serve-cwd=/w",
                        "--serve-env", "A=1", "--axe"], me=["SHOOT"])
check(got and got[0] == SW and got[got.index("--server") + 1] == "npm run dev" and ["--cwd", "/w"] == got[got.index("--cwd"):got.index("--cwd") + 2]
      and ["--port", "auto"] == got[got.index("--port"):got.index("--port") + 2] and "--env" in got
      and got[got.index("--") + 1:] == ["SHOOT", "http://localhost:{port}", "--out", "o", "--axe"],
      f"shoot --serve: {got}")
check(shoot.serve_argv(["http://x", "--out", "o"]) is None, "shoot without --serve wraps anyway")

for f in fails:
    print("FAIL", f)
print(f"serve_with_test: {n - len(fails)}/{n} ok")
sys.exit(1 if fails else 0)
