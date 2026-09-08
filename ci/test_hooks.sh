#!/bin/bash
cd "$(dirname "$0")/.."; export CLAUDE_PROJECT_DIR=$(pwd); H=.claude/hooks; FAILS=0
t() { local name="$1" want="$2" hook="$3" json="$4"; out=$(echo "$json" | bash "$hook" 2>&1 >/dev/null); rc=$?; if [ "$rc" = "$want" ]; then v="ok  "; else v="FAIL"; FAILS=$((FAILS+1)); fi; printf "  %s  %-44s exit %s (want %s)\n" "$v" "$name" "$rc" "$want"; }
echo "=== protect-checks (Edit|Write) ==="
t "edit a check script"           2 $H/protect-checks.sh '{"tool_name":"Edit","tool_input":{"file_path":"harden/checks/check35_controls.py"}}'
t "edit ci/checks.yaml"           2 $H/protect-checks.sh '{"tool_name":"Write","tool_input":{"file_path":"ci/checks.yaml","content":"x"}}'
t "edit a gate ledger"            2 $H/protect-checks.sh '{"tool_name":"Edit","tool_input":{"file_path":"gates/GATES-retrieval.md"}}'
t "edit a hook itself"            2 $H/protect-checks.sh '{"tool_name":"Edit","tool_input":{"file_path":".claude/hooks/gate-complete.sh"}}'
t "edit a stage (allowed)"        0 $H/protect-checks.sh '{"tool_name":"Edit","tool_input":{"file_path":"retrieval/stage18_definitions.py"}}'
t "edit a work package (allowed)" 0 $H/protect-checks.sh '{"tool_name":"Write","tool_input":{"file_path":"orchestration/work-packages/A4.md"}}'
echo "=== guard-commit-and-corpus (Bash) ==="
rm -f .regen.stamp
t "commit with no regen stamp"    2 $H/guard-commit-and-corpus.sh '{"tool_name":"Bash","tool_input":{"command":"git commit -m x"}}'
touch .regen.stamp; sleep 1; touch README.md
t "commit after a post-regen edit" 2 $H/guard-commit-and-corpus.sh '{"tool_name":"Bash","tool_input":{"command":"git add . && git commit -m x"}}'
touch .regen.stamp
t "commit right after regen"      0 $H/guard-commit-and-corpus.sh '{"tool_name":"Bash","tool_input":{"command":"git commit -m x"}}'
t "check33b without corpus mode"  2 $H/guard-commit-and-corpus.sh '{"tool_name":"Bash","tool_input":{"command":"python3 checks/check33b_completeness.py --db x"}}'
t "check33b with --all-articles"  0 $H/guard-commit-and-corpus.sh '{"tool_name":"Bash","tool_input":{"command":"python3 checks/check33b_completeness.py --db x --all-articles"}}'
t "read the source PDF by path"   2 $H/guard-commit-and-corpus.sh '{"tool_name":"Bash","tool_input":{"command":"pdftotext /mnt/uploads/301880.pdf"}}'
t "read the built PDF (allowed)"  0 $H/guard-commit-and-corpus.sh '{"tool_name":"Bash","tool_input":{"command":"pdfinfo pdf/301880_built_from_model.pdf"}}'
echo "=== decision-guard (tracks.yaml) ==="
mk() { python3 -c "import yaml,json,sys;d=yaml.safe_load(open('orchestration/tracks.yaml'));exec(sys.argv[1]);print(json.dumps({'tool_name':'Write','tool_input':{'file_path':'orchestration/tracks.yaml','content':yaml.safe_dump(d)}}))" "$1"; }
t "flip FRULES to ready"          2 $H/decision-guard.sh "$(mk "d['tracks']['FRULES']['status']='ready'")"
t "delete DEC1"                   2 $H/decision-guard.sh "$(mk "d['decisions_pending']=[x for x in d['decisions_pending'] if x['id']!='DEC1']")"
t "mark A4 done (allowed)"        0 $H/decision-guard.sh "$(mk "d['tracks']['A4']['status']='done'")"
rm -f .regen.stamp
echo "=== fail-closed ==="
for h in protect-checks guard-commit-and-corpus decision-guard; do echo "not json" | bash $H/$h.sh 2>/dev/null; rc=$?; [ "$rc" = 2 ] && v="ok  " || { v="FAIL"; FAILS=$((FAILS+1)); }; printf "  %s  %-44s exit %s (want 2)\n" "$v" "garbage stdin -> $h" "$rc"; done
echo "RESULT: $([ $FAILS = 0 ] && echo PASS || echo "FAIL $FAILS hook case(s)")"
exit $FAILS
