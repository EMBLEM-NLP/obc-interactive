#!/bin/bash
cd "$(dirname "$0")/.."; export CLAUDE_PROJECT_DIR=$(pwd); H=.claude/hooks; FAILS=0
t() { local name="$1" want="$2" hook="$3" json="$4"; out=$(echo "$json" | bash "$hook" 2>&1 >/dev/null); rc=$?; if [ "$rc" = "$want" ]; then v="ok  "; else v="FAIL"; FAILS=$((FAILS+1)); fi; printf "  %s  %-46s exit %s (want %s)\n" "$v" "$name" "$rc" "$want"; }
# payload builders - quoting a JSON payload by hand is how a case ends up
# testing something other than what it names
bj() { python3 -c "import json,sys;print(json.dumps({'tool_name':'Bash','tool_input':{'command':sys.argv[1]}}))" "$1"; }
ej() { python3 -c "
import json,sys
print(json.dumps({'tool_name':'Edit','tool_input':dict(zip(('file_path','old_string','new_string'),sys.argv[1:4]))}))" "$1" "$2" "$3"; }
mj() { python3 -c "
import json,sys
print(json.dumps({'tool_name':'MultiEdit','tool_input':{'file_path':sys.argv[1],'edits':[{'old_string':sys.argv[2],'new_string':sys.argv[3]}]}}))" "$1" "$2" "$3"; }
mk() { python3 -c "import yaml,json,sys;d=yaml.safe_load(open('orchestration/tracks.yaml'));exec(sys.argv[1]);print(json.dumps({'tool_name':'Write','tool_input':{'file_path':'orchestration/tracks.yaml','content':yaml.safe_dump(d)}}))" "$1"; }
TY=orchestration/tracks.yaml
FR_OLD=$(printf '  FRULES:\n    title: Compliance checking — LegalRuleML / RASE\n    status: conditional')
FR_NEW=$(printf '  FRULES:\n    title: Compliance checking — LegalRuleML / RASE\n    status: ready')
A4_OLD=$(printf '  A4:\n    title: Declared schema (LinkML) with constraints\n    status: ready')
A4_NEW=$(printf '  A4:\n    title: Declared schema (LinkML) with constraints\n    status: done')
DEC1=$(python3 -c "s=open('$TY',encoding='utf-8').read();print(s[s.index('- id: DEC1'):s.index('- id: DEC2')],end='')")

echo "=== protect-checks (Edit|Write) ==="
t "edit a check script"           2 $H/protect-checks.sh '{"tool_name":"Edit","tool_input":{"file_path":"harden/checks/check35_controls.py"}}'
t "edit ci/checks.yaml"           2 $H/protect-checks.sh '{"tool_name":"Write","tool_input":{"file_path":"ci/checks.yaml","content":"x"}}'
t "edit a gate ledger"            2 $H/protect-checks.sh '{"tool_name":"Edit","tool_input":{"file_path":"gates/GATES-retrieval.md"}}'
t "edit a hook itself"            2 $H/protect-checks.sh '{"tool_name":"Edit","tool_input":{"file_path":".claude/hooks/gate-complete.sh"}}'
t "edit a stage (allowed)"        0 $H/protect-checks.sh '{"tool_name":"Edit","tool_input":{"file_path":"retrieval/stage18_definitions.py"}}'
t "edit a work package (allowed)" 0 $H/protect-checks.sh '{"tool_name":"Write","tool_input":{"file_path":"orchestration/work-packages/A4.md","content":"x"}}'
# What counts as machinery is defined once, in check41's PROTECTED, and this
# hook asks that file. These two cases exist because protect-checks kept its own
# copy of the list until 2026-09-08 and the copies had already drifted.
t "edit the CI workflow"          2 $H/protect-checks.sh '{"tool_name":"Edit","tool_input":{"file_path":".github/workflows/gates.yml"}}'
t "edit a non-workflow .github"   0 $H/protect-checks.sh '{"tool_name":"Write","tool_input":{"file_path":".github/ISSUE_TEMPLATE.md","content":"x"}}'
t "edit a schema (allowed)"       0 $H/protect-checks.sh '{"tool_name":"Edit","tool_input":{"file_path":"schema/obc.linkml.yaml"}}'

echo "=== guard-commit: is this a commit at all? ==="
# Command position, not substring. The old regex matched the verb anywhere in
# the string, so writing a message file with a heredoc was refused as a commit.
rm -f .regen.stamp
t "commit with no regen stamp"        2 $H/guard-commit-and-corpus.sh "$(bj 'git commit -m x')"
t "commit wrapped in bash -c"         2 $H/guard-commit-and-corpus.sh "$(bj "bash -c 'git commit -m x'")"
t "commit behind an env-var prefix"   2 $H/guard-commit-and-corpus.sh "$(bj 'GIT_AUTHOR_NAME=x git commit -m y')"
t "commit via git -C path"            2 $H/guard-commit-and-corpus.sh "$(bj 'git -C /repo commit -m x')"
t "the verb inside a heredoc body"    0 $H/guard-commit-and-corpus.sh "$(bj 'cat > /tmp/m.txt <<EOF
a message that mentions git commit -m x
EOF')"
t "the verb as a quoted argument"     0 $H/guard-commit-and-corpus.sh "$(bj 'echo "git commit -m x"')"
t "the verb as a grep pattern"        0 $H/guard-commit-and-corpus.sh "$(bj "grep -rn 'git commit' .")"
t "git log --grep, not a commit"      0 $H/guard-commit-and-corpus.sh "$(bj 'git log --grep=commit')"
t "multi-line quoted arg, no commit"  0 $H/guard-commit-and-corpus.sh "$(bj 'python3 -c "
import os
print(1)
"')"

echo "=== guard-commit: regen stamp and corpus mode ==="
touch .regen.stamp; sleep 1; touch README.md
t "commit after a post-regen edit"    2 $H/guard-commit-and-corpus.sh "$(bj 'git add . && git commit -m x')"
touch .regen.stamp
t "commit right after regen"          0 $H/guard-commit-and-corpus.sh "$(bj 'git commit -m x')"
t "check33b without corpus mode"      2 $H/guard-commit-and-corpus.sh "$(bj 'python3 checks/check33b_completeness.py --db x')"
t "check33b with --all-articles"      0 $H/guard-commit-and-corpus.sh "$(bj 'python3 checks/check33b_completeness.py --db x --all-articles')"
# Reading about a check is not running it. The old rule grepped the whole
# command string, so `grep` for the name and even `cat` on the file were refused.
t "grep FOR check33b (reading)"       0 $H/guard-commit-and-corpus.sh "$(bj "grep -rn 'check33b_completeness' .")"
t "cat check33b (reading)"            0 $H/guard-commit-and-corpus.sh "$(bj 'cat retrieval/checks/check33b_completeness.py')"
t "check33b run after cd, eval mode"  2 $H/guard-commit-and-corpus.sh "$(bj 'cd retrieval && python3 checks/check33b_completeness.py --db x')"
t "read the source PDF by path"       2 $H/guard-commit-and-corpus.sh "$(bj 'pdftotext /mnt/uploads/301880.pdf')"
t "read the built PDF (allowed)"      0 $H/guard-commit-and-corpus.sh "$(bj 'pdfinfo pdf/301880_built_from_model.pdf')"

echo "=== guard-machinery: absolute paths (the worktree escape) ==="
# A subagent in a worktree ran `touch /abs/path/harden/checks/check35_controls.py`
# and it SUCCEEDED, landing on the main checkout: the matcher only understood
# repo-relative paths, so the hit list came back empty and the guard allowed it.
t "absolute path to a check"          2 $H/guard-machinery.sh "$(bj 'touch /home/user/obc-interactive/harden/checks/check35_controls.py')"
t "absolute path to a hook"           2 $H/guard-machinery.sh "$(bj 'sed -i s/a/b/ /home/user/obc-interactive/.claude/hooks/decision-guard.sh')"
t "another checkout of the repo"      2 $H/guard-machinery.sh "$(bj 'cat > /home/user/obc-interactive/.claude/worktrees/agent-x/ci/checks.yaml')"
t "absolute path, not machinery"      0 $H/guard-machinery.sh "$(bj 'touch /home/user/obc-interactive/README.md')"
# The workflow that runs the board belongs with the runner it invokes.
t "write the CI workflow"             2 $H/guard-machinery.sh "$(bj 'cat > .github/workflows/gates.yml')"
t "sed -i the CI workflow, absolute"  2 $H/guard-machinery.sh "$(bj 'sed -i s/a/b/ /home/user/obc-interactive/.github/workflows/gates.yml')"
t "write a non-workflow .github"      0 $H/guard-machinery.sh "$(bj 'cat > .github/ISSUE_TEMPLATE.md')"

echo "=== guard-verify-readonly (wired only into verify-track) ==="
t "verifier: the board"               0 $H/guard-verify-readonly.sh "$(bj 'python3 ci/run_gates.py')"
t "verifier: schedule --check"        0 $H/guard-verify-readonly.sh "$(bj 'python3 orchestration/schedule.py --check')"
t "verifier: regenerate"              0 $H/guard-verify-readonly.sh "$(bj 'bash ci/regenerate.sh')"
t "verifier: read a check"            0 $H/guard-verify-readonly.sh "$(bj 'cat harden/checks/check35_controls.py')"
t "verifier: sed -n is a read"        0 $H/guard-verify-readonly.sh "$(bj "sed -n '1,5p' ci/run_gates.py")"
t "verifier: the probe that escaped"  2 $H/guard-verify-readonly.sh "$(bj 'echo hello > /tmp/verify_probe.txt')"
t "verifier: sed -i"                  2 $H/guard-verify-readonly.sh "$(bj "sed -i 's/a/b/' harden/checks/check35_controls.py")"
t "verifier: python3 -c"              2 $H/guard-verify-readonly.sh "$(bj 'python3 -c "print(1)"')"
t "verifier: bash -c"                 2 $H/guard-verify-readonly.sh "$(bj "bash -c 'echo x'")"
t "verifier: git checkout"            2 $H/guard-verify-readonly.sh "$(bj 'git checkout -- ci/run_gates.py')"
t "verifier: an unknown command"      2 $H/guard-verify-readonly.sh "$(bj 'curl https://example.com')"
t "verifier: garbage stdin"           2 $H/guard-verify-readonly.sh 'not json'

echo "=== decision-guard: Edit shapes (the fail-open the Write cases missed) ==="
t "Edit: flip FRULES to ready"        2 $H/decision-guard.sh "$(ej "$TY" "$FR_OLD" "$FR_NEW")"
t "Edit: delete the DEC1 entry"       2 $H/decision-guard.sh "$(ej "$TY" "$DEC1" "")"
t "MultiEdit: flip FRULES to ready"   2 $H/decision-guard.sh "$(mj "$TY" "$FR_OLD" "$FR_NEW")"
t "Edit: old_string is not in the file" 2 $H/decision-guard.sh "$(ej "$TY" "no such text anywhere" "x")"
t "Edit: result is unparseable yaml"  2 $H/decision-guard.sh "$(ej "$TY" "tracks:" "tracks:
  bad: [unclosed")"
t "Edit: mark A4 done (allowed)"      0 $H/decision-guard.sh "$(ej "$TY" "$A4_OLD" "$A4_NEW")"
t "Edit: a different file (allowed)"  0 $H/decision-guard.sh "$(ej README.md a b)"

echo "=== guard-machinery (Bash writes to verification machinery) ==="
# The deny list and protect-checks.sh are registered on Edit|Write|MultiEdit
# only. These are the routes that reach the checks through Bash instead.
t "sed -i a check"                    2 $H/guard-machinery.sh "$(bj "sed -i 's/x/y/' harden/checks/check35_controls.py")"
t "redirect into harden/checks"       2 $H/guard-machinery.sh "$(bj 'cat > harden/checks/evil.py')"
t "append to ci/checks.yaml"          2 $H/guard-machinery.sh "$(bj 'echo x >> ci/checks.yaml')"
t "chmod -x a hook"                   2 $H/guard-machinery.sh "$(bj 'chmod -x .claude/hooks/gate-complete.sh')"
t "delete a hook helper"              2 $H/guard-machinery.sh "$(bj 'rm .claude/hooks/_cmdstrip.py')"
t "overwrite settings.json"           2 $H/guard-machinery.sh "$(bj 'cp /tmp/x .claude/settings.json')"
t "git checkout a check"              2 $H/guard-machinery.sh "$(bj 'git checkout -- harden/checks/check23_controls.py')"
t "write a check via bash -c"         2 $H/guard-machinery.sh "$(bj "bash -c 'sed -i s/a/b/ ci/run_gates.py'")"
t "overwrite a gate ledger"           2 $H/guard-machinery.sh "$(bj 'mv /tmp/a gates/GATES-retrieval.md')"
t "CI1 seeds its own check (allowed)" 0 $H/guard-machinery.sh "$(bj 'python3 ci/run_gates.py --control')"
t "read a check (allowed)"            0 $H/guard-machinery.sh "$(bj 'cat harden/checks/check35_controls.py')"
t "grep the checks (allowed)"         0 $H/guard-machinery.sh "$(bj 'grep -rn RESULT harden/checks/')"
t "edit a stage (allowed)"            0 $H/guard-machinery.sh "$(bj "sed -i 's/a/b/' retrieval/stage18_definitions.py")"
t "write outside the tree (allowed)"  0 $H/guard-machinery.sh "$(bj 'echo hi > /tmp/scratch.txt')"

echo "=== decision-guard: whole-file Write shapes ==="
t "Write: flip FRULES to ready"       2 $H/decision-guard.sh "$(mk "d['tracks']['FRULES']['status']='ready'")"
t "Write: delete DEC1"                2 $H/decision-guard.sh "$(mk "d['decisions_pending']=[x for x in d['decisions_pending'] if x['id']!='DEC1']")"
t "Write: mark A4 done (allowed)"     0 $H/decision-guard.sh "$(mk "d['tracks']['A4']['status']='done'")"
rm -f .regen.stamp

echo "=== fail-closed ==="
for h in protect-checks guard-commit-and-corpus decision-guard guard-machinery; do echo "not json" | bash $H/$h.sh 2>/dev/null; rc=$?; [ "$rc" = 2 ] && v="ok  " || { v="FAIL"; FAILS=$((FAILS+1)); }; printf "  %s  %-46s exit %s (want 2)\n" "$v" "garbage stdin -> $h" "$rc"; done
# The helper is not optional: without it a commit cannot be told from a mention
# of one, and the guard must refuse rather than guess.
PARK=$(mktemp -d)
mv $H/_cmdstrip.py "$PARK/" 2>/dev/null
echo "$(bj 'git commit -m x')" | bash $H/guard-commit-and-corpus.sh >/dev/null 2>&1; rc=$?
echo "$(bj 'sed -i s/a/b/ harden/checks/check35_controls.py')" | bash $H/guard-machinery.sh >/dev/null 2>&1; rc2=$?
mv "$PARK/_cmdstrip.py" $H/ 2>/dev/null
[ "$rc" = 2 ] && v="ok  " || { v="FAIL"; FAILS=$((FAILS+1)); }
printf "  %s  %-46s exit %s (want 2)\n" "$v" "_cmdstrip.py missing -> guard-commit" "$rc"
[ "$rc2" = 2 ] && v="ok  " || { v="FAIL"; FAILS=$((FAILS+1)); }
printf "  %s  %-46s exit %s (want 2)\n" "$v" "_cmdstrip.py missing -> guard-machinery" "$rc2"
mv harden/checks/check41_machinery.py "$PARK/" 2>/dev/null
echo "$(bj 'sed -i s/a/b/ harden/checks/check35_controls.py')" | bash $H/guard-machinery.sh >/dev/null 2>&1; rc=$?
mv "$PARK/check41_machinery.py" harden/checks/ 2>/dev/null
rmdir "$PARK" 2>/dev/null
[ "$rc" = 2 ] && v="ok  " || { v="FAIL"; FAILS=$((FAILS+1)); }
printf "  %s  %-46s exit %s (want 2)\n" "$v" "check41 missing -> guard-machinery" "$rc"

echo "RESULT: $([ $FAILS = 0 ] && echo PASS || echo "FAIL $FAILS hook case(s)")"
exit $FAILS
