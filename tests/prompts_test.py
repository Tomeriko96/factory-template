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
check("SYNC: CLEAN" in texts.get("builder", "") and '"SYNC: CLEAN"' in JOB and "SYNC: CLEAN" in SKILL,
      "SYNC: CLEAN (a sync without conflicts) not in builder, job and SKILL.md")
check("Review sync N" in texts.get("reviewer-code", ""), "reviewer-code: no sync mode")
# Targeted tests during the build, the full suite once (precheck --validate)
check("validate.md" in texts.get("builder", "") and "Targeted tests only" in texts.get("builder", ""),
      "builder: targeted tests / validate.md not described")
for n, t in texts.items():
    if n.startswith("reviewer-"):
        check("Never run the full suite" in t and "coverage" in t, f"{n}: may still run the full suite or coverage")
check("cached validation" not in texts.get("reviewer-audit", "") and "not yours to measure" in texts.get("reviewer-audit", ""),
      "reviewer-audit: still starts from a full validation that only runs after the reviews")
check("--validate" in JOB and "VALIDATE: PENDING" in open(os.path.join(T, ".factory", "precheck")).read(),
      "job/precheck: --validate step missing")

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
# Bundle issues: the label, the candidate shape and the feature sections agree across script and prompts
check('BUNDLE_LABEL = "factory:bundle"' in JOB and "factory:bundle" in SKILL and "factory:bundle" in texts.get("triage", ""),
      "factory:bundle: not in job, SKILL.md and the triage agent")
check('"bundle": true' in texts.get("triage", "") and "`members`" in texts.get("triage", "")
      and "bundle=True, members=" in JOB, "bundle candidate shape (bundle, members): agent and job disagree")
check('f"## Bundle #' in JOB and "## Issue #" in JOB and "`## Bundle #<nr>: …`" in texts.get("spec-writer", "")
      and "`## Issue #<nr>: …`" in texts.get("spec-writer", ""), "bundle feature sections: job and spec-writer disagree")
check("sub_issues" in JOB and "/links" in JOB and "sub_issues" in SKILL and "/links" in SKILL,
      "bundle members from the forge (GitHub sub_issues, GitLab links): not in job and SKILL.md")
check('"groups"' in texts.get("triage", "") and '"skipped"' in texts.get("triage", "")
      and 'plan.get("groups")' in JOB and 'plan.get("skipped")' in JOB, "triage plan.json shape: agent and job disagree")

# Routing: every agent pins model and effort; the script prints EFFORT: and SKILL.md says how to pass it
LEVELS = ("low", "medium", "high", "xhigh", "max")
for n, t in texts.items():
    front = t.split("---", 2)[1] if t.startswith("---") else ""
    m = re.search(r"^effort: (\S+)$", front, re.M)
    check(m and m.group(1) in LEVELS, f"{n}: no valid effort: in the frontmatter")
    check(re.search(r"^model: (sonnet|opus|haiku)$", front, re.M), f"{n}: no model: in the frontmatter")
    want = "high" if n in ("builder", "reviewer-audit", "reviewer-security") else "medium"
    check(not m or m.group(1) == want, f"{n}: effort {m and m.group(1)}, want {want}")
check('f"EFFORT: ' in JOB and "ESCALATED: +" in JOB, "job: does not print EFFORT:/ESCALATED: lines")
check("`EFFORT:`" in SKILL and "`effort`" in SKILL and "## Routing" in SKILL, "SKILL.md: how to pass EFFORT: not described")
check("routing" in SKILL and "blocked_retries" in SKILL, "SKILL.md: config.routing not documented")
check("job report" in JOB.split('"""', 2)[1] and "job report" in SKILL, "job report: not in the usage text and SKILL.md")

# Vendored and distilled skills (see NOTICE)
NOTICE = open(os.path.join(ROOT, "NOTICE")).read()
FD = os.path.join(T, ".claude", "skills", "frontend-design")
check(os.path.exists(os.path.join(FD, "SKILL.md")) and "Apache License" in open(os.path.join(FD, "LICENSE.txt")).read(),
      "frontend-design: SKILL.md or its Apache LICENSE.txt missing")
for src in ("github.com/obra/superpowers", "MIT", "github.com/anthropics/skills", "Apache License 2.0"):
    check(src in NOTICE, f"NOTICE: {src} missing")
b_front = texts.get("builder", "").split("---", 2)[1]
check("frontend-design" not in b_front and "skills:" not in b_front, "builder: frontend-design preloaded again (read on UI work only)")
check("UI work:" in JOB and "frontend-design" in JOB and "`UI work:`" in texts.get("builder", ""),
      "UI work: line not printed by job or not explained to the builder")
_ui = re.search(r'^UI_GLOBS = \[(.*)\]$', JOB, re.M)
check(_ui and all(f"`{g}`" in texts.get("builder", "") for g in re.findall(r'"([^"]+)"', _ui.group(1))),
      "builder: default UI paths differ from job's UI_GLOBS")
for sec in ("Discipline", "Design reference (UI work only)", "Handling findings (round > 1)"):
    check(section(texts.get("builder", ""), sec), f"builder: no '## {sec}' section")
for word in ("obra/superpowers", "fail", "heavy", "should pass", "3 fixes", "poll"):
    check(word in (section(texts.get("builder", ""), "Discipline") or ""), f"builder Discipline: lacks {word!r}")
check("disputed" in texts.get("builder", "") and "One finding at a time" in texts.get("builder", ""),
      "builder: receiving-code-review rules missing")
tq = {g: section(texts.get(g, ""), "Test quality") for g in ("reviewer-code", "reviewer-audit")}
check(all(tq.values()) and len(set(tq.values())) == 1, "'## Test quality' missing or differs between reviewer-code and reviewer-audit")
check("mock" in (tq["reviewer-code"] or "") and "production" in (tq["reviewer-code"] or ""), "Test quality: mock/test-only rules missing")
check(section(texts.get("reviewer-audit", ""), "Red-green evidence and debugging"), "reviewer-audit: no red-green section")
dr = {g: section(texts.get(g, ""), "Design reference") for g in ("reviewer-ui", "reviewer-ux")}
check(all(dr.values()) and len(set(dr.values())) == 1, "'## Design reference' missing or differs between ui and ux")
check('"House style: ' in JOB or "House style: load" in JOB, "job: no House style: line")
check("house_style" in SKILL and "house_style" in SETUP, "house_style not documented in SKILL.md and setup.md")
check("check-style" in texts.get("reviewer-code", "") and "`gate`" in texts.get("builder", "") and "write-issue" in SKILL,
      "optional skills (check-style, gate, write-issue) not mentioned")
for n, t in list(texts.items()) + [("SKILL.md", SKILL), ("setup.md", SETUP)]:
    check(not re.search(r"cedanl|npuls", t, re.I), f"{n}: names an organisation (the template stays generic)")

# Hidden acceptance tests: writer, builder and audit agree with the job script
AW = texts.get("acceptance-writer", "")
check("ACCEPTANCE: WRITTEN" in AW and "ACCEPTANCE: NONE" in AW and "Run:" in AW, "acceptance-writer: output contract missing")
check('"ACCEPTANCE: WRITTEN"' in JOB and '"factory-acceptance-writer"' in JOB, "job: acceptance writer not wired")
check("Hidden acceptance tests:" in JOB and "`Hidden acceptance tests:`" in texts.get("reviewer-audit", ""),
      "audit: the Hidden acceptance tests: prompt line is not described")
check("trap" in (section(texts.get("reviewer-audit", ""), "Hidden acceptance tests") or ""), "audit: acceptance tests not removed in the same call")
check("Never open" in (section(texts.get("builder", ""), "Hidden acceptance tests") or ""), "builder: may read the hidden tests")
check("acceptance_tests" in SKILL and "factory-acceptance-writer" in SKILL, "SKILL.md: acceptance tests not documented")

# heavy's result line: printed by heavy, refused-when-piped by the guard, quoted by the builder
HEAVY_SRC = open(os.path.join(T, ".factory", "heavy")).read()
GUARD_SRC = open(os.path.join(T, ".factory", "guard")).read()
check("heavy: exit={rc} log=" in HEAVY_SRC and "heavy: exit=<n> log=<path>" in texts.get("builder", "")
      and "pipefail" in GUARD_SRC and "log=<path>" in (section(texts.get("builder", ""), "What `round-N/build.md` holds "
                                                        "(written last: see the final section)") or ""),
      "heavy result line: not printed by heavy, guarded, or quoted in build.md")

# Every agent's output file is its last, explicit step (an approver once gave MERGE only in its reply)
for n, t in texts.items():
    last = re.findall(r"^## (.+)$", re.sub(r"```.*?```", "", t, flags=re.S), re.M)
    check(last and last[-1] == "Last step: write the file", f"{n}: the last section is not 'Last step: write the file'")
    check("final, required step" in (section(t, "Last step: write the file") or ""), f"{n}: last step not marked required")
check("RESUME_HEAD" in JOB and "wrote no {file}; write it now from your previous" in JOB
      and "LAST_STEP" in JOB, "job: resume prompt head / last-step line missing")

for f in fails:
    print("FAIL", f)
print(f"prompts_test: {'ok' if not fails else str(len(fails)) + ' failure(s)'}")
sys.exit(1 if fails else 0)
