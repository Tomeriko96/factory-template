"""Consistency checks for the agent prompts and SKILL.md, so copies do not drift apart.

  python3 -I tests/prompts_test.py

Each agent file is loaded on its own, so shared text is duplicated on purpose; this test
keeps the duplicates identical and the contracts between prompts and scripts in step.
"""
import glob, hashlib, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
T = os.path.join(ROOT, "template")
AGENTS = sorted(glob.glob(os.path.join(T, ".claude", "agents", "factory-*.md")))
SKILL = open(os.path.join(T, ".claude", "skills", "factory", "SKILL.md")).read()
JOB = open(os.path.join(T, ".factory", "job")).read()
# Reviewers whose "## Heavy commands" section must be the same text
SAME_HEAVY = [["reviewer-code", "reviewer-data-quality", "reviewer-llm-safety", "reviewer-methodology",
               "reviewer-privacy", "reviewer-security"], ["reviewer-ui", "reviewer-ux"]]

fails = []


def check(ok, msg):
    if not ok:
        fails.append(msg)


def name(path):
    return os.path.basename(path)[8:-3]


def section(text, title):
    m = re.search(rf"## {re.escape(title)}\n(.*?)(?=\n## |\Z)", text, re.S)
    return m.group(1) if m else None


texts = {name(p): open(p).read() for p in AGENTS}
check(len(texts) >= 12, f"expected at least 12 agents, found {len(texts)}")
for n, t in texts.items():
    front = t.split("---", 2)[1] if t.startswith("---") else ""
    if n == "triage":   # not a job agent: no worktree, and no Bash (it reads untrusted issue text)
        check(re.search(r"^tools:.*\bBash\b", front, re.M) is None, "triage: must not have Bash")
        check("model: sonnet" in front and re.search(r"^effort: \w+", front, re.M), "triage: model and effort not pinned")
        continue
    check('.factory/guard' in front and "PreToolUse" in front, f"{n}: no guard hook in the frontmatter")
    check("paths block (Repo, Worktree, Job, Base, Branch, Tmp)" in t, f"{n}: paths block without Tmp")
    check("/tmp/factory-<job-id>" not in t, f"{n}: old /tmp/factory-<job-id> prefix (use <Tmp>)")
    if n.startswith("reviewer-"):
        r = n[9:]
        check(f"review-{r}.md" in t, f"{n}: does not name its file round-N/review-{r}.md")
        check("VERDICT: PASS" in t and "VERDICT: CHANGES" in t, f"{n}: verdict line not described")
        check(f"factory-reviewer-{r}" in t.split("---", 2)[1], f"{n}: frontmatter name mismatch")
for group in SAME_HEAVY:
    digests = {g: hashlib.sha1((section(texts.get(g, ""), "Heavy commands") or "").encode()).hexdigest()[:8]
               for g in group}
    check(len(set(digests.values())) == 1, f"'## Heavy commands' differs within {group}: {digests}")
check("BUILD: DONE" in texts.get("builder", "") and "BUILD: BLOCKED" in texts.get("builder", ""),
      "builder: BUILD verdict line not described")
check("SYNC: RESOLVED" in texts.get("builder", ""), "builder: sync verdict not described")
check("Review sync N" in texts.get("reviewer-code", ""), "reviewer-code: no sync mode")

# Stages the job script uses must all be documented in SKILL.md
stages = set()
for const in ("ACTIVE", "AT_REST"):
    m = re.search(rf"^{const} = \(([^)]*)\)", JOB, re.M)
    check(bool(m), f"job: {const} not found")
    if m:
        stages |= set(re.findall(r'"([a-z-]+)"', m.group(1)))
for st in sorted(stages | {"queued"}):
    check(f"`{st}`" in SKILL, f"SKILL.md does not mention stage `{st}`")
# Every action kind the script prints is explained in SKILL.md
for act in sorted(set(re.findall(r'"ACTION: ([a-z-]+)', JOB))):
    check(f"ACTION: {act}" in SKILL, f"SKILL.md does not explain ACTION: {act}")

# Auto-merge gate: what the script prints and reads is what the prompts describe
SETUP = open(os.path.join(T, ".claude", "skills", "factory", "setup.md")).read()
INSTALL = open(os.path.join(ROOT, "install")).read()
PRECHECK = open(os.path.join(T, ".factory", "precheck")).read()
check('"AUTO-MERGE: yes"' in JOB and "AUTO-MERGE: no (" in JOB, "job: does not print the AUTO-MERGE line")
check("AUTO-MERGE: yes" in SKILL and "AUTO-MERGE: no" in SKILL, "SKILL.md does not explain the AUTO-MERGE line")
check('startswith("HOLD:")' in JOB and "`HOLD: <reason>`" in texts.get("approver", ""),
      "approver HOLD line: not in both the approver prompt and the job script")
check("AUTO-MERGE: " in PRECHECK and "auto_merge_never" in PRECHECK, "precheck: no AUTO-MERGE line / auto_merge_never")
check("auto_merge_never" in SKILL and "auto_merge_never" in SETUP, "auto_merge_never not described in SKILL.md and setup.md")
check("--disable-auto" in SKILL and "cancel_merge_when_pipeline_succeeds" in SKILL,
      "SKILL.md: how to switch auto-merge off on GitHub and GitLab")
check("forgecheck" in INSTALL and "forgecheck" in SETUP and "forgecheck" in SKILL, "forgecheck not in install, setup.md and SKILL.md")
for word in ("CI-ON-DRAFT", "REQUIRED-CHECKS"):
    check(word in SETUP and word in open(os.path.join(T, ".factory", "forgecheck")).read(), f"{word}: not in both forgecheck and setup.md")

# Triage and bundles: what the script prints and reads is what SKILL.md and the agent describe
SKILL_FRONT = SKILL.split("---", 2)[1]
check(re.search(r"^effort: (low|medium|high)$", SKILL_FRONT, re.M), "SKILL.md: effort not pinned in the frontmatter")
for sub in ("triage prepare", "triage plan", "triage start"):
    check(f"job {sub}" in SKILL, f"SKILL.md does not explain `job {sub}`")
    check(f"job {sub}" in JOB.split('"""', 2)[1], f"job: {sub} missing from the usage text")
for lab in ("factory:docs|light|full", "factory:solo"):
    check(lab in SKILL and lab in texts.get("triage", ""), f"{lab}: not in both SKILL.md and the triage agent")
for word in ("GROUP", "SKIPPED:", "LEFT-OUT:"):
    check(word in SKILL and word in JOB, f"{word}: not in both SKILL.md and job")
check("factory:ready" not in SETUP.split("**Issues:**", 1)[1].split("**Delivery**", 1)[0], "setup.md: still creates a factory:ready label")
check('"groups"' in texts.get("triage", "") and '"skipped"' in texts.get("triage", "")
      and 'plan.get("groups")' in JOB and 'plan.get("skipped")' in JOB, "triage plan.json shape: agent and job disagree")

for f in fails:
    print("FAIL", f)
print(f"prompts_test: {'ok' if not fails else str(len(fails)) + ' failure(s)'}")
sys.exit(1 if fails else 0)
