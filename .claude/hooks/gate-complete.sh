#!/bin/bash
# Stop / SubagentStop. A track may not end until check35 (H10) passes and the
# board is green. Honors stop_hook_active so a prior block cannot wedge the session.
eval "$(python3 "$(dirname "$0")/_input.py")"
if [ "$HOOK_OK" != "1" ]; then echo "BLOCKED (fail-closed): $HOOK_REASON (gate-complete)" >&2; exit 2; fi
[ "$HOOK_STOP_ACTIVE" = "1" ] && exit 0
ROOT="${CLAUDE_PROJECT_DIR:-.}"; DB="${OBC_DB:-$ROOT/emitters/obc-mod.sqlite}"
cd "$ROOT" || { echo "BLOCKED: cannot cd to project root (gate-complete)" >&2; exit 2; }
if ! timeout 1200 python3 harden/checks/check35_controls.py --db "$DB" > ${TMPDIR:-/tmp}/gc-c35.log 2>&1; then
  echo "BLOCKED: check35 (H10) failed - a ratio gate has no falsifying mutation. $(tail -c 240 ${TMPDIR:-/tmp}/gc-c35.log | tr '\n' ' ') (gate-complete)" >&2; exit 2; fi
if ! timeout 1800 python3 ci/run_gates.py --fast --out ${TMPDIR:-/tmp}/gc-board.json > ${TMPDIR:-/tmp}/gc-board.log 2>&1; then
  echo "BLOCKED: gate board not green: $(grep -E 'FAIL|MISSING' ${TMPDIR:-/tmp}/gc-board.log | head -3 | tr '\n' ' ') (gate-complete)" >&2; exit 2; fi
exit 0
