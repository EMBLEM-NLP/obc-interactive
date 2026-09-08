#!/bin/bash
# PreToolUse on Edit|Write of orchestration/tracks.yaml. The four decisions
# require a human: flipping FRULES off 'conditional' or deleting a
# decisions_pending entry is blocked.
eval "$(python3 "$(dirname "$0")/_input.py")"
if [ "$HOOK_OK" != "1" ]; then echo "BLOCKED (fail-closed): $HOOK_REASON (decision-guard)" >&2; exit 2; fi
case "$HOOK_FILE" in *orchestration/tracks.yaml) ;; *) exit 0;; esac
[ -z "$HOOK_NEW" ] && exit 0
ROOT="${CLAUDE_PROJECT_DIR:-.}"
HOOK_NEW="$HOOK_NEW" python3 - "$ROOT/orchestration/tracks.yaml" <<'PY'
import os, sys, yaml
cur = yaml.safe_load(open(sys.argv[1]))
try: new = yaml.safe_load(os.environ["HOOK_NEW"])
except Exception: sys.exit(0)          # partial edit: cannot judge, do not block
if not isinstance(new, dict): sys.exit(0)
cd = {d["id"] for d in (cur.get("decisions_pending") or [])}
nd = {d["id"] for d in (new.get("decisions_pending") or [])} if "decisions_pending" in new else cd
if cd - nd:
    print(f"BLOCKED: removing decision(s) {sorted(cd-nd)}. Decisions are resolved by a human and recorded in the commit message. (decision-guard)", file=sys.stderr); sys.exit(2)
t = new.get("tracks") or {}
if "FRULES" in t and cur["tracks"]["FRULES"]["status"] == "conditional" and t["FRULES"].get("status") not in (None, "conditional"):
    print("BLOCKED: FRULES may not leave 'conditional' until DEC1 (assist or judge) is answered by a human. (decision-guard)", file=sys.stderr); sys.exit(2)
PY
