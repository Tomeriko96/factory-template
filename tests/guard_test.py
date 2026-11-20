"""Check .factory/guard against tests/guard_cases.txt.

  python3 -I tests/guard_test.py                        (template guard, all cases)
  python3 -I tests/guard_test.py <guard> <cases>
"""
import importlib.machinery, importlib.util, os, sys

sys.dont_write_bytecode = True  # do not leave __pycache__ in template/.factory

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GUARD = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "template", ".factory", "guard")
CASES = sys.argv[2] if len(sys.argv) > 2 else os.path.join(ROOT, "tests", "guard_cases.txt")

loader = importlib.machinery.SourceFileLoader("guard", GUARD)
spec = importlib.util.spec_from_loader("guard", loader)
guard = importlib.util.module_from_spec(spec)
loader.exec_module(guard)

bad = total = 0
for line in open(CASES):
    line = line.rstrip("\n")
    if not line.strip() or line.startswith("#"):
        continue
    want, cmd = line[0], line[2:]
    total += 1
    try:
        why = guard.refusal(cmd)
    except Exception as e:  # the hook allows on errors; a crash here is a bug either way
        why = None
        print(f"CRASH {cmd!r}: {e!r}")
    got = "R" if why else "A"
    if got != want:
        bad += 1
        print(f"want {want} got {got}: {cmd}" + (f"   ({why.splitlines()[0][:160]})" if why else ""))
# The heavy refusal names the exact rewritten command, at the agent's priority
H = os.path.join(os.path.dirname(os.path.abspath(GUARD)), "heavy")
for cmd, agent, want in [
        ("npm test", "factory-builder", f"  {H} --priority high -- npm test\n"),
        ("pytest -q tests/test_a.py", None, f"  {H} --priority normal -- pytest -q tests/test_a.py\n"),
        ("cd web && npm run build", "factory-reviewer-audit", f"  {H} --priority low -- bash -c 'cd web && npm run build'\n"),
        ("CI=1 pytest", "factory-reviewer-code", f"  {H} --priority normal -- bash -c 'CI=1 pytest'\n")]:
    total += 1
    msg = guard.refusal(cmd, agent) or ""
    if want not in msg:
        bad += 1
        print(f"rewrite of {cmd!r} ({agent}): want {want.strip()!r} in\n{msg}")
print(f"{total - bad}/{total} ok")
sys.exit(1 if bad else 0)
