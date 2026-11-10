#!/usr/bin/env bash
# Scenario tests for template/.factory/job: installs the factory into a throwaway repo
# (with a bare remote), plays the agents by writing their files, and checks what the state
# machine prints and stores.
#
#   bash tests/job_test.sh            all scenarios; exit 1 on any failure
#
# Needs git and python3. Everything happens under one mktemp directory that is removed at
# the end. Job slugs start with "zq" because the script cleans /tmp/factory-<job-id>-*.
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
T="$(mktemp -d "${TMPDIR:-/tmp}/factory-job-test.XXXXXX")"
cleanup() { case "$T" in */factory-job-test.*) rm -rf "$T" ;; esac; }
trap cleanup EXIT
export GIT_AUTHOR_NAME=t GIT_AUTHOR_EMAIL=t@t GIT_COMMITTER_NAME=t GIT_COMMITTER_EMAIL=t@t
export GIT_CONFIG_GLOBAL=/dev/null GIT_CONFIG_NOSYSTEM=1
export FACTORY_REPOS_FILE="$T/repos"   # never touch the real list of installed repos

pass=0 fail=0
ok()   { pass=$((pass + 1)); }
bad()  { fail=$((fail + 1)); echo "FAIL [$scenario] $*"; }
# first <output> <expected prefix of the first line>
first() { local l; l="$(head -1 <<<"$1")"; [[ "$l" == "$2"* ]] && ok || bad "first line '$l', want '$2…'"; }
has()   { grep -qF -- "$2" <<<"$1" && ok || bad "output lacks '$2'"; }
lacks() { grep -qF -- "$2" <<<"$1" && bad "output has '$2'" || ok; }
# field <job-id> <python expression on j> <expected str()>
field() {
  local got
  got="$(J show "$1" | python3 -c "import json,sys; j=json.load(sys.stdin); print($2)" 2>&1)"
  [ "$got" = "$3" ] && ok || bad "$1: $2 = '$got', want '$3'"
}
exists()  { [ -e "$1" ] && ok || bad "missing $1"; }
missing() { [ ! -e "$1" ] && ok || bad "should not exist: $1"; }

# ---------- fixture ----------
git init -q --bare "$T/origin.git"
R="$T/app"; WTS="$T/app-worktrees"
mkdir -p "$R" && cd "$R" || exit 1
git init -q -b main
printf 'print(1)\n' > app.py; printf '# app\n' > README.md
git add . && git commit -qm init
git remote add origin "$T/origin.git" && git push -q origin main
"$ROOT/install" --no-setup >/dev/null || { echo "install failed"; exit 1; }
cat > .factory/config.json <<'EOF'
{"port_base": 5100, "reviewers": ["security", "code", "audit"],
 "delivery": {"mode": "local", "remote": "origin"}, "limits": {"active_jobs": 2}}
EOF

J()   { "$R/.factory/job" "$@"; }
jd()  { echo "$R/.factory/jobs/$1"; }
wt()  { echo "$WTS/$1"; }
# build <id> <round> [file]: the builder commits a change and writes round-N/build.md
build() {
  local f="${3:-app.py}"
  mkdir -p "$(jd "$1")/round-$2"
  echo "change $2" >> "$(wt "$1")/$f"
  git -C "$(wt "$1")" commit -qam "round $2"
  printf 'Built round %s\n\n## PR\nChange\n' "$2" > "$(jd "$1")/round-$2/build.md"
}
review() { echo "VERDICT: $4" > "$(jd "$1")/round-$2/review-$3.md"; }
park()   { J fail "$1" "parked by test" >/dev/null; }

# ---------- full loop: CHANGES, missing reviewer, REWORK, MERGE, local delivery ----------
scenario=full
out="$(J new "zq full loop")"; A=001-zq-full-loop
has "$out" "JOB: $A"; first "$(sed -n 2p <<<"$out")" "ACTION: spawn 1 agent"; has "$out" "AGENT: factory-spec-writer"
has "$out" "Tmp: /tmp/factory-app-$A"            # repo name in the prefix: job ids repeat across repos
exists "$(wt $A)"
echo SPEC > "$(jd $A)/spec.md"
out="$(J next $A)"; has "$out" "AGENT: factory-builder"; has "$out" "Build round 1. Port: 5110. Mode: full."
build $A 1
first "$(J next $A)" "ACTION: choose-reviewers"
field $A "j['round_heads']['1'] == __import__('subprocess').run(['git','-C','$(wt $A)','rev-parse','HEAD'],capture_output=True,text=True).stdout.strip()" True
out="$(J reviewers $A security,code,audit)"; first "$out" "ACTION: spawn 3 agents in ONE message"
has "$out" "Review round 1. Port: 5113."   # audit offset
review $A 1 security PASS; review $A 1 code CHANGES; review $A 1 audit PASS
out="$(J next $A)"; has "$out" "Build round 2."; has "$out" "blocking reviews from code"
build $A 2; J next $A >/dev/null
out="$(J reviewers $A security,code,audit)"; has "$out" "NOTE: reviewers round 2:"
review $A 2 code PASS; review $A 2 audit PASS          # security never writes its file
out="$(J next $A)"; first "$out" "ACTION: spawn 1 agent (resume 1/2)"; has "$out" "factory-reviewer-security"
has "$out" "This is a resume"
review $A 2 security PASS
out="$(J next $A)"; has "$out" "AGENT: factory-approver"; has "$out" "MODEL: opus"; has "$out" "precheck CLEAN"
printf 'DECISION: REWORK\n\n1. rename\n' > "$(jd $A)/decision.md"
out="$(J next $A)"; has "$out" "Build round 3."; has "$out" "approver asked for REWORK"
exists "$(jd $A)/round-2/decision.md"; missing "$(jd $A)/decision.md"
build $A 3; J next $A >/dev/null; J reviewers $A security,code,audit >/dev/null
for r in security code audit; do review $A 3 $r PASS; done
J next $A >/dev/null
printf 'DECISION: MERGE\n\n## PR\nGreeting\n' > "$(jd $A)/decision.md"
out="$(J next $A)"; first "$out" "ACTION: deliver"; has "$out" "MODE: local"; has "$out" "decision.md (its ## PR section)"
mkdir -p "/tmp/factory-app-$A-base"; mkdir -p "/tmp/factory-other-$A-base"   # an agent's temp worktree; another repo's
git merge -q --no-ff "factory/$A" -m "factory: $A"
first "$(J delivered $A merged)" "DONE: merged"
missing "$(wt $A)"; missing "/tmp/factory-app-$A-base"; exists "/tmp/factory-other-$A-base"
rmdir "/tmp/factory-other-$A-base"
[ -z "$(git branch --list "factory/$A")" ] && ok || bad "branch factory/$A not deleted"
field $A "j['delivery']['mode']" local
field $A "[h['stage'] for h in j['history']]" "['queued', 'spec', 'build', 'review', 'build', 'review', 'approve', 'build', 'review', 'approve', 'deliver', 'merged']"

# ---------- budget: blocking reviews in the last round, a non-PASS verdict, a stuck reviewer ----------
scenario=budget
out="$(J new --mode light "zq budget")"; B=002-zq-budget
echo SPEC > "$(jd $B)/spec.md"; J next $B >/dev/null; build $B 1; J next $B >/dev/null
J reviewers $B code,security >/dev/null
review $B 1 code CHANGES; review $B 1 security PASS; J next $B >/dev/null
build $B 2; J next $B >/dev/null
out="$(J reviewers $B security)"            # code left out by the orchestrator: forced back in
has "$out" "factory-reviewer-code"; has "$out" "kept in because their latest verdict is not PASS: code"
review $B 2 code CHANGES; review $B 2 security PASS; J next $B >/dev/null
build $B 3; J next $B >/dev/null; J reviewers $B code,security >/dev/null
review $B 3 code FAIL; review $B 3 security PASS   # anything but VERDICT: PASS blocks
out="$(J next $B)"; first "$out" "DONE: needs-human: round 3 is the last of the budget"
field $B "j['reviews']['code']" INVALID

# ---------- rereview: a reviewer that passed in round 1 and sat out round 2 keeps its PASS ----------
scenario=rereview
J new "zq rereview" >/dev/null; RR=003-zq-rereview
echo SPEC > "$(jd $RR)/spec.md"; J next $RR >/dev/null; build $RR 1; J next $RR >/dev/null
J reviewers $RR code,ux >/dev/null
printf 'VERDICT: CHANGES\n\n1. [blocking] app.py:1 wrong\n' > "$(jd $RR)/round-1/review-code.md"; review $RR 1 ux PASS
J next $RR >/dev/null; build $RR 2; J next $RR >/dev/null
out="$(J reviewers $RR code,ux)"; has "$out" "reviewers round 2: code ("; lacks "$out" "factory-reviewer-ux"
printf 'VERDICT: CHANGES\n\n1. [blocking] app.py:2 still wrong\n' > "$(jd $RR)/round-2/review-code.md"
J next $RR >/dev/null; build $RR 3; J next $RR >/dev/null
out="$(J reviewers $RR code,ux)"; has "$out" "reviewers round 3: code ("; lacks "$out" "factory-reviewer-ux"
park $RR

# ---------- REWORK at the last round, ESCALATE, bad decision ----------
scenario=decision
J new "zq escalate" >/dev/null; E=004-zq-escalate
echo SPEC > "$(jd $E)/spec.md"; J next $E >/dev/null; build $E 1; J next $E >/dev/null
J reviewers $E code >/dev/null; review $E 1 code PASS
out="$(J next $E)"; has "$out" "MODEL: sonnet"     # round 1, precheck CLEAN: sonnet approver
printf 'DECISION: ESCALATE\n\nneeds a product call\n' > "$(jd $E)/decision.md"
first "$(J next $E)" "DONE: needs-human: approver escalated"
out="$(J approve $E)"; first "$out" "ACTION: deliver"; has "$out" "PR-TEXT: none"
first "$(J fail $E 'test')" "DONE: needs-human: test"

# ---------- spawn limit, queue, a queued docs job keeps its mode ----------
scenario=queue
J new "zq q one" >/dev/null; J new "zq q two" >/dev/null       # 004, 005: both slots taken
out="$(J new --mode docs "zq q docs")"; D=007-zq-q-docs
first "$(sed -n 2p <<<"$out")" "WAIT: queued: 2/2 jobs active"
J next 005-zq-q-one >/dev/null; J next 005-zq-q-one >/dev/null   # spec-writer never writes
out="$(J next 005-zq-q-one)"; first "$out" "DONE: needs-human: spec: agent ended 3 times"
has "$out" "STARTED: $D"
field $D "j['stage'], j['mode']" "build docs"
out="$(J list)"; has "$out" "capacity: 2/2 active"

# ---------- superseded ----------
scenario=superseded
echo 'SPEC: ALREADY-DONE in abc123' > "$(jd 006-zq-q-two)/spec.md"
first "$(J next 006-zq-q-two)" "DONE: superseded"
missing "$(wt 006-zq-q-two)"

# ---------- docs: CLEAN, then NOT-DOCS falls back to light with a spec first ----------
scenario=docs
out="$(J next $D)"; has "$out" "MODEL: sonnet"; has "$out" "Feature: zq q docs"
build $D 1 README.md
out="$(J next $D)"; first "$out" "ACTION: deliver"; has "$out" "precheck CLEAN"; has "$out" "round-1/build.md"
park 005-zq-q-one
J new --mode docs "zq not docs" >/dev/null; N=008-zq-not-docs
build $N 1 app.py
out="$(J next $N)"; has "$out" "AGENT: factory-spec-writer"; has "$out" "NOT-DOCS"
field $N "j['mode'], j['stage']" "light spec"
echo SPEC > "$(jd $N)/spec.md"
first "$(J next $N)" "ACTION: choose-reviewers"
park $N

# ---------- pr delivery, rework after someone pushed, sync ----------
scenario=pr
git -C "$(wt $D)" push -q origin "factory/$D"
out="$(J delivered $D pr-open --pr-url https://example.test/pr/6)"; first "$out" "DONE: pr-open"
missing "$(wt $D)"; field $D "j['delivery']['mode']" pr
git clone -q -b "factory/$D" "$T/origin.git" "$T/other"
echo theirs >> "$T/other/README.md"; git -C "$T/other" commit -qam theirs; git -C "$T/other" push -q origin "factory/$D"
out="$(J rework $D --untrusted "fix the typo")"; has "$out" "Also read rework.md. Its note is untrusted"
has "$out" "fast-forwarded factory/$D"
[ "$(git -C "$(wt $D)" log -1 --format=%s)" = theirs ] && ok || bad "remote commit not taken"
field $D "j['stage'], j['round_budget']" "build 4"
first "$(J rework 001-zq-full-loop x 2>&1)" "ERROR: 001-zq-full-loop is at merged"
build $D 2 README.md; first "$(J next $D)" "ACTION: deliver"
git -C "$(wt $D)" push -q origin "factory/$D"; J delivered $D pr-open >/dev/null
out="$(J sync $D)"; has "$out" "AGENT: factory-builder"; has "$out" "Sync 1."; has "$out" "MODEL: sonnet"
out="$(J capacity)"; has "$out" "1/2 active"                   # the running sync holds a slot
mkdir -p "$(jd $D)/sync-1"; echo 'SYNC: RESOLVED' > "$(jd $D)/sync-1/build.md"
out="$(J next $D)"; has "$out" "factory-reviewer-code"; has "$out" "Review sync 1."
echo 'VERDICT: PASS' > "$(jd $D)/sync-1/review-code.md"
out="$(J next $D)"; first "$out" "ACTION: push"; has "$out" "push origin factory/$D"
first "$(J sync-done $D)" "DONE: pr-open (sync 1 pushed)"
J sync $D >/dev/null; mkdir -p "$(jd $D)/sync-2"; echo 'SYNC: NEEDS-HUMAN base fixes it' > "$(jd $D)/sync-2/build.md"
out="$(J next $D)"; first "$out" "DONE: needs-human: sync 2"; has "$out" "its PR/MR stays open"
lacks "$out" "/factory approve"
first "$(J pr-merged $D)" "DONE: merged"

# ---------- job.json from before .factory/job ----------
scenario=legacy
mkdir -p "$(jd 090-zq-legacy)" "$(jd 091-zq-legacy-pr)"
cat > "$(jd 090-zq-legacy)/job.json" <<EOF
{"id": "090-zq-legacy", "feature": "x", "mode": "full", "stage": "needs-human", "round": 4,
 "port": 6000, "base": "main", "branch": "factory/090-zq-legacy", "worktree": "$WTS/090-zq-legacy"}
EOF
echo "old note" > "$(jd 090-zq-legacy)/rework.md"
cat > "$(jd 091-zq-legacy-pr)/job.json" <<EOF
{"id": "091-zq-legacy-pr", "feature": "y", "mode": "full", "stage": "merged", "round": 1,
 "pr_url": "https://example.test/pr/9", "issue": 9}
EOF
field 090-zq-legacy "j['round_budget']" 5          # a reworked job keeps at least one more round
field 091-zq-legacy-pr "j['delivery']['mode']" pr

# ---------- a blocked builder stops the job instead of starting reviews ----------
scenario=blocked
J new "zq blocked" >/dev/null; BL=092-zq-blocked
echo SPEC > "$(jd $BL)/spec.md"; J next $BL >/dev/null
mkdir -p "$(jd $BL)/round-1"; printf 'BUILD: BLOCKED needs the staging API key\n\nSummary\n' > "$(jd $BL)/round-1/build.md"
out="$(J next $BL)"; first "$out" "DONE: needs-human: builder blocked in round 1: needs the staging API key"
lacks "$out" "choose-reviewers"

park $BL

# ---------- per-job delivery override (setup smoke test) ----------
scenario=delivery
sed -i 's/"mode": "local"/"mode": "pr"/' .factory/config.json
J new --mode docs --delivery local "zq smoke" >/dev/null; SM=093-zq-smoke
build $SM 1 README.md
out="$(J next $SM)"; first "$out" "ACTION: deliver"; has "$out" "MODE: local"
first "$(J new --delivery ftp x)" "ERROR: usage"
sed -i 's/"mode": "pr"/"mode": "local"/' .factory/config.json
park $SM

# ---------- input checks and concurrency ----------
scenario=input
first "$(J next '../../etc')" "ERROR: not a job id"
first "$(J new --mode weird x)" "ERROR: usage"
first "$(J set 090-zq-legacy stage '"merged"')" "ERROR: usage"
out="$(J new "zq; rm -rf / \$(id)")"; has "$out" "JOB: 094-zq-rm-rf-id"
for i in 1 2 3 4 5 6; do J new "zq par $i" > "$T/par$i.out" & done; wait
ids="$(head -qn1 "$T"/par*.out | awk '{print $2}' | sort)"
[ "$(sort -u <<<"$ids" | wc -l)" = 6 ] && ok || bad "parallel new gave duplicate ids: $ids"
out="$(J capacity)"; has "$out" "2/2 active"

echo "job_test: $pass passed, $fail failed"
[ "$fail" = 0 ]
