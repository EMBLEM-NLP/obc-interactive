#!/bin/bash
# Stop / SubagentStop. A track may not end until check35 (H10) passes and the
# board is green. Honors stop_hook_active so a prior block cannot wedge the session.
eval "$(python3 "$(dirname "$0")/_input.py")"
if [ "$HOOK_OK" != "1" ]; then echo "BLOCKED (fail-closed): $HOOK_REASON (gate-complete)" >&2; exit 2; fi
[ "$HOOK_STOP_ACTIVE" = "1" ] && exit 0
ROOT="${CLAUDE_PROJECT_DIR:-.}"; DB="${OBC_DB:-$ROOT/emitters/obc-mod.sqlite}"
cd "$ROOT" || { echo "BLOCKED: cannot cd to project root (gate-complete)" >&2; exit 2; }
# Data first, or every downstream failure is misattributed. Without this, a
# clone that never fetched the data reported "check35 (H10) failed - a ratio
# gate has no falsifying mutation" when no ratio gate was broken and the real
# cause was an absent database. A guard that names the wrong cause sends the
# next executor to fix something that is not wrong. Observed 2026-09-08.
if ! python3 harden/checks/check40_dataintegrity.py --quick > ${TMPDIR:-/tmp}/gc-data.log 2>&1; then
  echo "BLOCKED: the data the gates read is missing, truncated, or a pointer stub - this is NOT a gate failure. Run: bash ci/fetch_data.sh (needs OBC_DATA_URL, OBC_DATA_TARBALL or OBC_DATA_DIR). $(grep -E 'MISSING|STUBS|WRONG' ${TMPDIR:-/tmp}/gc-data.log | head -2 | tr '\n' ' ') (gate-complete)" >&2; exit 2; fi
if ! timeout 1200 python3 harden/checks/check35_controls.py --db "$DB" > ${TMPDIR:-/tmp}/gc-c35.log 2>&1; then
  echo "BLOCKED: check35 (H10) failed - a ratio gate has no falsifying mutation. $(tail -c 240 ${TMPDIR:-/tmp}/gc-c35.log | tr '\n' ' ') (gate-complete)" >&2; exit 2; fi
if ! timeout 1800 python3 ci/run_gates.py --fast --out ${TMPDIR:-/tmp}/gc-board.json > ${TMPDIR:-/tmp}/gc-board.log 2>&1; then
  echo "BLOCKED: gate board not green: $(grep -E 'FAIL|MISSING' ${TMPDIR:-/tmp}/gc-board.log | head -3 | tr '\n' ' ') (gate-complete)" >&2; exit 2; fi
exit 0
