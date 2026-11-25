"""Release guard: every version a commit subject announces, `… (vX.Y.Z)`, has its tag.

  python3 -I tests/release_test.py

`install` writes `git describe --tags` into .factory/VERSION, so a release without its tag installs
as the previous version (v0.14.2 shipped untagged and installed as v0.14.1). The check runs on this
repo's history and on a throwaway repo (the guard itself). It is skipped for a pull request (the tag
comes with the push to main): on a push to main CI fails until the tag is pushed too
(`git push origin main vX.Y.Z`).
"""
import os, re, subprocess, sys, tempfile, shutil

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ANNOUNCE = re.compile(r"\((v\d+\.\d+\.\d+)\)")
fails, n = [], 0


def check(ok, msg):
    global n
    n += 1
    if not ok:
        fails.append(msg)


def git(repo, *args, env=None):
    return subprocess.run(["git", "-C", repo, *args], capture_output=True, text=True, env=env)


def untagged(repo, env=None):
    """[(version, commit, subject)] for each announced version without a tag that contains its commit."""
    log = git(repo, "log", "--format=%H%x09%s", env=env).stdout.splitlines()
    out = []
    for line in log:
        sha, _, subject = line.partition("\t")
        for v in ANNOUNCE.findall(subject):
            tag = git(repo, "rev-parse", "-q", "--verify", f"refs/tags/{v}^{{commit}}", env=env).stdout.strip()
            if not tag or git(repo, "merge-base", "--is-ancestor", sha, tag, env=env).returncode != 0:
                out.append((v, sha[:12], subject))
    return out


# the guard itself, on a throwaway repo
tmp = tempfile.mkdtemp(prefix="factory-release-test.")
try:
    env = dict(os.environ, GIT_CONFIG_GLOBAL="/dev/null", GIT_CONFIG_NOSYSTEM="1", GIT_AUTHOR_NAME="t",
               GIT_AUTHOR_EMAIL="t@t", GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@t")
    git(tmp, "init", "-q", "-b", "main", env=env)
    git(tmp, "commit", "-q", "--allow-empty", "-m", "feat: one (v9.1.0)", env=env)
    git(tmp, "tag", "-a", "v9.1.0", "-m", "v9.1.0", env=env)
    git(tmp, "commit", "-q", "--allow-empty", "-m", "docs: no version here", env=env)
    check(untagged(tmp, env) == [], "a tagged release counted as untagged")
    git(tmp, "commit", "-q", "--allow-empty", "-m", "fix: two (v9.1.1)", env=env)
    got = untagged(tmp, env)
    check([v for v, _, _ in got] == ["v9.1.1"], f"untagged v9.1.1 not found: {got}")
    git(tmp, "tag", "v9.1.1", "HEAD~1", env=env)   # a tag on the wrong commit does not count
    check([v for v, _, _ in untagged(tmp, env)] == ["v9.1.1"], "a tag before the release commit counted")
    git(tmp, "tag", "-f", "v9.1.1", "HEAD", env=env)
    check(untagged(tmp, env) == [], "v9.1.1 still untagged after tagging")
finally:
    shutil.rmtree(tmp, ignore_errors=True)

# this repository
if os.environ.get("GITHUB_EVENT_NAME") == "pull_request":
    print("release_test: pull request: this repo's tags are checked on the push to main")
elif git(ROOT, "rev-parse", "--is-shallow-repository").stdout.strip() == "true":
    fails.append("shallow clone: fetch with tags (actions/checkout fetch-depth: 0)")
else:
    for v, sha, subject in untagged(ROOT):
        fails.append(f"{sha} announces {v} without a tag: git tag -a {v} {sha} -m {v} && git push origin {v}")
    n += 1

for f in fails:
    print("FAIL", f)
print(f"release_test: {n - len(fails)}/{n} ok")
sys.exit(1 if fails else 0)
