"""Infra classification of failed CI jobs (template/.factory/ci): recorded log snippets.

  python3 -I tests/ci_infra_test.py

An infra failure (OOMKilled, exit 137, runner/scheduler, a registry push error after green tests)
is retried once and never becomes a rework round; anything with a failing test stays a code failure.
"""
import importlib.machinery, importlib.util, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.dont_write_bytecode = True
loader = importlib.machinery.SourceFileLoader("factory_ci", os.path.join(ROOT, "template", ".factory", "ci"))
spec = importlib.util.spec_from_loader("factory_ci", loader)
ci = importlib.util.module_from_spec(spec)
loader.exec_module(ci)

# onderwijsdata-chat jobs 1981060 and 1981318 (git.sdp.surf.nl, 2026-11-25)
OOM = """tests/test_zz.py ........                                                [100%]
\x1b[32m================ 916 passed, 94 skipped in 412.31s (0:06:52) =================\x1b[0m
section_end:1795600000:step_script
Cleaning up project directory and file based variables
ERROR: Job failed: Error in container build: exit code: 137, reason: 'OOMKilled'
"""
SYSTEM = """Running with gitlab-runner 17.5.0
Preparing the "kubernetes" executor
ERROR: Job failed (system failure): prepare environment: waiting for pod running: timed out
"""
KILLED = "=== 120 passed in 30s ===\nmake: *** [test] Error 137\nprocess exited with code 137\n"
REGISTRY = """=== 916 passed, 94 skipped ===
Pushing image cr.surf.nl/ceda/onderwijsdata-chat:abc123
error pushing image: denied: quota exceeded for project ceda
ERROR: Job failed: exit code 1
"""
REGISTRY_RED = """FAILED tests/test_api.py::test_login - AssertionError
=== 1 failed, 915 passed ===
error pushing image: denied: quota exceeded
"""
CODE = "collecting ...\nE   assert 2 == 3\nFAILED tests/test_x.py::test_y\n=== 1 failed, 915 passed ===\nERROR: Job failed: exit code 1\n"
LINT = "src/app.py:3:1: F401 'os' imported but unused\nFound 1 error.\nERROR: Job failed: exit code 1\n"
GH_RUNNER = "##[error]The runner has received a shutdown signal. This can happen when the runner service is stopped.\n"
OOM_RED = "=== 2 failed, 914 passed ===\nERROR: Job failed: exit code 137, reason: 'OOMKilled'\n"

CASES = [
    (OOM, "OOMKilled"), (SYSTEM, "runner system failure"), (KILLED, "exit code 137"),
    (REGISTRY, "registry push error (error pushing)"), (REGISTRY_RED, None), (CODE, None), (LINT, None),
    (GH_RUNNER, "runner lost"), (OOM_RED, None), ("", None), (None, None),
]
fails, n = [], 0
for i, (log, want) in enumerate(CASES):
    n += 1
    got = ci.log_infra_reason(log)
    if got != want:
        fails.append(f"case {i}: {got!r}, want {want!r}: {(log or '')[:60]!r}")


def jobs(*specs):
    return [{"name": nm, "status": st, "id": i, **({"failure_reason": fr} if fr else {})}
            for i, (nm, st, fr) in enumerate(specs, 1)]


def expect(got, want, what):
    global n
    n += 1
    if got != want:
        fails.append(f"{what}: {got!r}, want {want!r}")


# a whole pipeline: infra only when every failed job is infra
expect(ci.infra_reason(jobs(("test", "failed", None), ("lint", "success", None)), {"test": OOM}), "OOMKilled", "one OOM job")
expect(ci.infra_reason(jobs(("test", "failed", None), ("lint", "failed", None)), {"test": OOM, "lint": LINT}), None,
       "OOM + lint failure")
expect(ci.infra_reason(jobs(("test", "failed", None), ("push", "failed", None)), {"test": OOM, "push": REGISTRY}),
       "OOMKilled, registry push error (error pushing)", "OOM + registry")
expect(ci.infra_reason(jobs(("deploy", "failed", "runner_system_failure")), {}), "runner system failure",
       "GitLab failure_reason without a log")
expect(ci.infra_reason(jobs(("deploy", "failed", "script_failure")), {"deploy": CODE}), None, "script_failure")
expect(ci.infra_reason(jobs(("test", "success", None)), {}), None, "no failed job")

for f in fails:
    print("FAIL", f)
print(f"ci_infra_test: {n - len(fails)}/{n} ok")
sys.exit(1 if fails else 0)
