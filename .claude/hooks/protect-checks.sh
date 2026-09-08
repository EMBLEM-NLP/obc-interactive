#!/bin/bash
# PreToolUse on Edit|Write|MultiEdit. Verification machinery is read-only to
# executors. Every vacuous gate this project shipped was green; an agent told to
# make the board pass will edit the check. exit 2 = block, stderr is the reason.
#
# What counts as machinery is NOT defined here. It is PROTECTED in
# harden/checks/check41_machinery.py, and this hook asks that file.
#
# It used to keep its own `case` statement, which made three copies of one
# policy - the deny list in settings.json, this case, and PROTECTED - and they
# drifted: the case covered gates/GATES-*.md and the deny list did not, and when
# .github/workflows/* was added to PROTECTED this hook alone would have kept
# permitting Edit on the workflow that runs the board. AUDIT-rev10 claimed
# PROTECTED was already the single definition. It was not; this makes it so.
eval "$(python3 "$(dirname "$0")/_input.py")"
if [ "$HOOK_OK" != "1" ]; then echo "BLOCKED (fail-closed): $HOOK_REASON (protect-checks)" >&2; exit 2; fi
[ -z "$HOOK_FILE" ] && exit 0
ROOT="${CLAUDE_PROJECT_DIR:-.}"
CHECK="$ROOT/harden/checks/check41_machinery.py"
[ -f "$CHECK" ] || CHECK="$(dirname "$0")/../../harden/checks/check41_machinery.py"
if [ ! -f "$CHECK" ]; then
  echo "BLOCKED (fail-closed): harden/checks/check41_machinery.py is missing, so verification machinery cannot be told from ordinary source. (protect-checks)" >&2; exit 2; fi
HIT=$(printf '%s\n' "$HOOK_FILE" | python3 "$CHECK" --is-protected 2>/dev/null) || {
  echo "BLOCKED (fail-closed): could not test the path against the protected set. (protect-checks)" >&2; exit 2; }
[ -z "$HIT" ] && exit 0
echo "BLOCKED: $HOOK_FILE is verification machinery, read-only during a track. Propose the change in the audit addendum for human review. (protect-checks)" >&2
exit 2
