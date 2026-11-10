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
        why = guard.heavy_reason(cmd)
    except Exception as e:  # the hook allows on errors; a crash here is a bug either way
        why = None
        print(f"CRASH {cmd!r}: {e!r}")
    got = "R" if why else "A"
    if got != want:
        bad += 1
        print(f"want {want} got {got}: {cmd}" + (f"   ({why})" if why else ""))
print(f"{total - bad}/{total} ok")
sys.exit(1 if bad else 0)
