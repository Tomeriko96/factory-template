"""Checks for .factory/forgecheck: does CI run on a draft, are checks required before a merge.

  python3 -I tests/forgecheck_test.py

Throwaway repos with workflow files and a fake `gh`/`glab` on PATH.
"""
import json, os, shutil, subprocess, sys, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "template", ".factory", "forgecheck")
fails, n = [], 0


def check(ok, msg):
    global n
    n += 1
    if not ok:
        fails.append(msg)


tmp = tempfile.mkdtemp(prefix="factory-forgecheck-test.")


def repo(forge, files, name):
    r = os.path.join(tmp, name)
    os.makedirs(os.path.join(r, ".factory"))
    shutil.copy(SRC, os.path.join(r, ".factory"))
    json.dump({"forge": forge}, open(os.path.join(r, ".factory", "config.json"), "w"))
    for path, text in files.items():
        os.makedirs(os.path.dirname(os.path.join(r, path)) or r, exist_ok=True)
        open(os.path.join(r, path), "w").write(text)
    subprocess.run(["git", "init", "-q", "-b", "main", r], check=True)
    return r


def run(r, *args, env=None):
    e = dict(os.environ, **(env or {}))
    p = subprocess.run([sys.executable, "-I", os.path.join(r, ".factory", "forgecheck"), *args],
                       capture_output=True, text=True, cwd=r, env=e)
    return json.loads(p.stdout) if "--json" in args else p.stdout


def fake(name, body):
    d = os.path.join(tmp, "bin")
    os.makedirs(d, exist_ok=True)
    p = os.path.join(d, name)
    open(p, "w").write("#!/bin/sh\n" + body + "\n")
    os.chmod(p, 0o755)
    return {"PATH": d + os.pathsep + os.environ["PATH"]}


try:
    gh = lambda on, extra="": {".github/workflows/ci.yml": f"name: ci\non:\n{on}\njobs:\n  t:\n{extra}    runs-on: x\n"}
    cases = [
        ("plain pull_request", gh("  pull_request:\n    branches: [main]"), "yes"),
        ("inline list", {".github/workflows/ci.yml": "on: [push, pull_request]\njobs: {}\n"}, "yes"),
        ("types opened + ready", gh("  pull_request:\n    types: [opened, synchronize, ready_for_review]"), "yes"),
        ("only ready_for_review", gh("  pull_request:\n    types: [ready_for_review]"), "no"),
        ("if draft == false", gh("  pull_request:\n    branches: [main]", "    if: github.event.pull_request.draft == false\n"), "no"),
        ("push only", gh("  push:\n    branches: [main]"), "no"),
        ("no workflows", {}, "no"),
        ("types under push is not ours", gh("  pull_request:\n    branches: [main]\n  push:\n    types: [x]"), "yes"),
    ]
    for label, files, want in cases:
        r = repo("github", files, "gh-" + label.replace(" ", "-"))
        got = run(r, "--offline", "--json")["ci_on_draft"]
        check(got == want, f"github {label}: ci_on_draft={got}, want {want}")
    r = repo("github", {**gh("  pull_request:\n    types: [ready_for_review]"),
                        ".github/workflows/lint.yml": "on: pull_request\njobs: {}\n"}, "gh-mixed")
    check(run(r, "--offline", "--json")["ci_on_draft"] == "unknown", "github: one workflow skips drafts, one runs: unknown")

    r = repo("gitlab", {".gitlab-ci.yml": "workflow:\n  rules:\n    - if: $CI_MERGE_REQUEST_IID\n"}, "gl-mr")
    check(run(r, "--offline", "--json")["ci_on_draft"] == "yes", "gitlab merge request pipelines: yes")
    r = repo("gitlab", {".gitlab-ci.yml": "workflow:\n  rules:\n    - if: $CI_MERGE_REQUEST_TITLE =~ /^Draft:/\n      when: never\n"}, "gl-draft")
    check(run(r, "--offline", "--json")["ci_on_draft"] == "no", "gitlab title rule on Draft: no")
    r = repo("gitlab", {}, "gl-none")
    check(run(r, "--offline", "--json")["ci_on_draft"] == "unknown", "gitlab without .gitlab-ci.yml: unknown")
    r = repo("none", {".gitlab-ci.yml": "workflow:\n  rules:\n    - if: $CI_MERGE_REQUEST_IID\n"}, "no-forge-1")
    check(run(r, "--offline", "--json", "--forge", "gitlab")["ci_on_draft"] == "yes", "--forge overrides a missing config")
    r = repo("none", {}, "no-forge-2")
    check(run(r, "--offline", "--json")["ci_on_draft"] == "unknown", "no forge: unknown")

    # required checks, with a fake gh / glab
    r = repo("github", gh("  pull_request:\n    branches: [main]"), "gh-req")
    env = fake("gh", 'case "$2" in *rules/branches*) echo \'[{"type":"required_status_checks"}]\';; *) exit 1;; esac')
    check(run(r, "--json", env=env)["required_checks"] == "yes", "github ruleset with required_status_checks: yes")
    env = fake("gh", 'case "$2" in *rules/branches*) echo "[]";; *protection*) echo \'{"contexts":["unit"],"checks":[]}\';; esac')
    check(run(r, "--json", env=env)["required_checks"] == "yes", "github branch protection contexts: yes")
    env = fake("gh", 'case "$2" in *rules/branches*) echo "[]";; *protection*) echo \'{"contexts":[],"checks":[]}\';; esac')
    check(run(r, "--json", env=env)["required_checks"] == "no", "github protection without contexts: no")
    env = fake("gh", "echo denied >&2; exit 1")
    check(run(r, "--json", env=env)["required_checks"] == "unknown", "github api error: unknown, not no")
    out = run(r, env=env)
    check("CI-ON-DRAFT: yes" in out and "REQUIRED-CHECKS: unknown" in out and "ask the user to confirm" in out,
          "text output lacks the verdict lines or the advice")
    r = repo("gitlab", {".gitlab-ci.yml": "x: {}\n"}, "gl-req")
    env = fake("glab", 'echo \'{"only_allow_merge_if_pipeline_succeeds": true}\'')
    check(run(r, "--json", env=env)["required_checks"] == "yes", "gitlab pipeline must succeed: yes")
    env = fake("glab", 'echo \'{"only_allow_merge_if_pipeline_succeeds": false}\'')
    res = run(r, "--json", env=env)
    check(res["required_checks"] == "no" and any("do not switch on delivery.auto_merge" in x for x in res["recommend"]),
          "gitlab merge without pipeline: no, with the auto_merge warning")
finally:
    shutil.rmtree(tmp, ignore_errors=True)

for f in fails:
    print("FAIL", f)
print(f"forgecheck_test: {n - len(fails)}/{n} ok")
sys.exit(1 if fails else 0)
