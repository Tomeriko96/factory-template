"""Checks for ./install: every skill the template ships is installed and git-excluded.

  python3 -I tests/install_test.py

Throwaway repos; FACTORY_REPOS_FILE keeps the real list of installed repos untouched.
"""
import os, shutil, subprocess, sys, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILLS = sorted(d for d in os.listdir(os.path.join(ROOT, "template", ".claude", "skills"))
                if os.path.isdir(os.path.join(ROOT, "template", ".claude", "skills", d)))
fails, n = [], 0


def check(ok, msg):
    global n
    n += 1
    if not ok:
        fails.append(msg)


def sh(cmd, cwd, env):
    return subprocess.run(cmd, cwd=cwd, env=env, capture_output=True, text=True)


tmp = tempfile.mkdtemp(prefix="factory-install-test.")
try:
    env = dict(os.environ, GIT_CONFIG_GLOBAL="/dev/null", GIT_CONFIG_NOSYSTEM="1",
               GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t", GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@t",
               FACTORY_REPOS_FILE=os.path.join(tmp, "repos"))

    def repo(name, own_skill=False):
        r = os.path.join(tmp, name)
        os.makedirs(r)
        sh(["git", "init", "-q", "-b", "main"], r, env)
        open(os.path.join(r, "a.txt"), "w").write("a\n")
        if own_skill:   # the repo tracks its own copy of a vendored skill
            os.makedirs(os.path.join(r, ".claude", "skills", "frontend-design"))
            open(os.path.join(r, ".claude", "skills", "frontend-design", "SKILL.md"), "w").write("own\n")
        sh(["git", "add", "-A"], r, env)
        sh(["git", "commit", "-qm", "init"], r, env)
        return r

    check("factory" in SKILLS and "frontend-design" in SKILLS, f"template skills: {SKILLS}")
    r = repo("plain")
    p = sh([os.path.join(ROOT, "install"), "--no-setup"], r, env)
    check(p.returncode == 0, f"install failed: {p.stderr or p.stdout}")
    exclude = open(os.path.join(r, ".git", "info", "exclude")).read()
    for s in SKILLS:
        check(os.path.exists(os.path.join(r, ".claude", "skills", s, "SKILL.md")), f"{s}: not installed")
        check(f"/.claude/skills/{s}/" in exclude, f"{s}: no exclude line")
        check(sh(["git", "check-ignore", "-q", f".claude/skills/{s}/SKILL.md"], r, env).returncode == 0,
              f"{s}: not ignored by git")
    cmds = sorted(os.listdir(os.path.join(ROOT, "template", ".claude", "skills", "factory", "commands")))
    check(cmds and all(os.path.exists(os.path.join(r, ".claude", "skills", "factory", "commands", c)) for c in cmds),
          "factory: commands/*.md (read on demand by SKILL.md) not installed")
    check(os.access(os.path.join(r, ".factory", "serve-with"), os.X_OK), ".factory/serve-with not installed executable")
    check(os.path.exists(os.path.join(ROOT, "template", ".claude", "skills", "factory", "commands", "sync.md")),
          "template: commands/sync.md missing")
    check(os.path.exists(os.path.join(r, ".claude", "skills", "frontend-design", "LICENSE.txt")),
          "frontend-design: LICENSE.txt not installed with it")
    st = sh(["git", "status", "--porcelain", "--untracked-files=all"], r, env).stdout
    check(st.strip() == "", f"git sees installed files: {st!r}")
    p = sh([os.path.join(ROOT, "install"), "--no-setup"], r, env)   # re-install: one block, not two
    exclude = open(os.path.join(r, ".git", "info", "exclude")).read()
    check(p.returncode == 0 and exclude.count("# factory:begin") == 1, "re-install: duplicated exclude block")
    p = sh([os.path.join(ROOT, "install"), "--remove", "--purge"], r, env)
    check(p.returncode == 0, f"remove failed: {p.stderr or p.stdout}")
    for s in SKILLS:
        check(not os.path.exists(os.path.join(r, ".claude", "skills", s)), f"{s}: left behind by --remove")
    check("factory:begin" not in open(os.path.join(r, ".git", "info", "exclude")).read(), "exclude block left behind")

    r = repo("own", own_skill=True)
    p = sh([os.path.join(ROOT, "install"), "--no-setup"], r, env)
    check(p.returncode == 0 and "frontend-design is tracked" in p.stdout, f"own skill: {p.stdout} {p.stderr}")
    check(open(os.path.join(r, ".claude", "skills", "frontend-design", "SKILL.md")).read() == "own\n",
          "own skill: the repo's copy was overwritten")
    check("/.claude/skills/frontend-design/" not in open(os.path.join(r, ".git", "info", "exclude")).read(),
          "own skill: excluded although the repo tracks it")
    sh([os.path.join(ROOT, "install"), "--remove", "--purge"], r, env)
    check(os.path.exists(os.path.join(r, ".claude", "skills", "frontend-design", "SKILL.md")),
          "own skill: removed by --remove")
finally:
    shutil.rmtree(tmp, ignore_errors=True)

for f in fails:
    print("FAIL", f)
print(f"install_test: {n - len(fails)}/{n} ok")
sys.exit(1 if fails else 0)
