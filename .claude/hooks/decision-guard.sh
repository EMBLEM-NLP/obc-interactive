#!/bin/bash
# PreToolUse on Edit|Write|MultiEdit of orchestration/tracks.yaml. The four
# decisions require a human: removing a decisions_pending entry, or moving
# FRULES off 'conditional', is blocked.
#
# This judges the document the edit WOULD PRODUCE, not the payload fragment.
#
# The first version parsed `new_string` on its own and looked for top-level
# `tracks` / `decisions_pending` keys. A partial Edit never carries them, so
# `t = new.get("tracks") or {}` was empty and nothing was checked: an Edit
# flipping FRULES to ready, and an Edit deleting DEC1, both returned exit 0 and
# changed the file. Whole-file Write payloads were judged correctly - and those
# were the only shapes ci/test_hooks.sh sent, so gate E1 stayed green over the
# defect. R1 inside the enforcement layer: a gate that cannot go red is a light.
# Observed under Claude Code and reproduced as scripts, 2026-09-08.
eval "$(python3 "$(dirname "$0")/_input.py")"
if [ "$HOOK_OK" != "1" ]; then echo "BLOCKED (fail-closed): $HOOK_REASON (decision-guard)" >&2; exit 2; fi
case "$HOOK_FILE" in *orchestration/tracks.yaml) ;; *) exit 0;; esac
ROOT="${CLAUDE_PROJECT_DIR:-.}"
HOOK_RAW="$HOOK_RAW" python3 - "$ROOT/orchestration/tracks.yaml" <<'PY'
import base64, json, os, sys


def block(msg):
    print(f"BLOCKED: {msg} (decision-guard)", file=sys.stderr)
    sys.exit(2)


try:
    import yaml
except ImportError:
    block("pyyaml is not installed, so this edit cannot be judged")

path = sys.argv[1]
try:
    current = open(path, encoding="utf-8").read()
    cur = yaml.safe_load(current)
except Exception as e:
    block(f"the current tracks.yaml cannot be read ({type(e).__name__})")

try:
    payload = json.loads(base64.b64decode(os.environ.get("HOOK_RAW", "")).decode("utf-8"))
except Exception as e:
    block(f"the hook payload cannot be reconstructed ({type(e).__name__})")

ti = payload.get("tool_input") or {}
tool = payload.get("tool_name") or "the tool"


def apply_edit(text, e):
    old, new = e.get("old_string"), e.get("new_string")
    if old is None or new is None:
        block("an edit carries no old_string/new_string, so its result cannot be determined")
    if old == "":
        block("an edit has an empty old_string, so its result cannot be determined")
    if old not in text:
        block("an edit's old_string does not appear in tracks.yaml, so its result cannot be determined")
    return text.replace(old, new) if e.get("replace_all") else text.replace(old, new, 1)


# Reconstruct the candidate document. Every branch that cannot produce one
# refuses; the previous version exited 0 on each of these.
if "content" in ti:                                   # Write
    candidate = ti.get("content")
    if candidate is None:
        block("a write carries no content")
elif "edits" in ti:                                   # MultiEdit
    candidate = current
    for e in (ti.get("edits") or []):
        candidate = apply_edit(candidate, e)
elif "old_string" in ti:                              # Edit
    candidate = apply_edit(current, ti)
else:
    block(f"unrecognised {tool} payload for tracks.yaml; refusing rather than guessing")

try:
    new = yaml.safe_load(candidate)
except Exception as e:
    block(f"this edit would leave tracks.yaml unparseable ({type(e).__name__})")
if not isinstance(new, dict):
    block("this edit would leave tracks.yaml without a top-level mapping")

cd = {d.get("id") for d in (cur.get("decisions_pending") or [])}
nd = {d.get("id") for d in (new.get("decisions_pending") or [])}
gone = sorted(x for x in (cd - nd) if x)
if gone:
    block(f"removing decision(s) {gone}. Decisions are resolved by a human and recorded in the commit message")

cf = ((cur.get("tracks") or {}).get("FRULES") or {}).get("status")
nf = ((new.get("tracks") or {}).get("FRULES") or {}).get("status")
if cf == "conditional" and nf != "conditional":
    block("FRULES may not leave 'conditional' until DEC1 (assist or judge) is answered by a human")
sys.exit(0)
PY
