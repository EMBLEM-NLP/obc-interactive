#!/bin/bash
# PreToolUse on Bash. Keeps Bash from writing to verification machinery.
#
# The deny list in .claude/settings.json and protect-checks.sh both cover
# Edit|Write|MultiEdit only. Bash was never covered, so `sed -i`, `cat >`,
# `tee`, `cp`, `chmod -x` on a hook, or `git checkout --` all reached
# harden/checks/ with nothing watching. Finding 4 of AUDIT-rev7.md.
#
# THIS IS NOT A GUARANTEE AND MUST NOT BE READ AS ONE. An executor holding Bash
# can defeat any Bash guard: rewrite this file, chmod it non-executable, or edit
# settings.json out from under it. A write can also hide inside a program -
# python3 -c "open(p, 'w')" modifies a file and no reading of the command string
# can know it.
#
# So this hook stops the ordinary case and gives an immediate reason. The
# guarantee is harden/checks/check41_machinery.py (gate E2), which compares the
# tree against HEAD and so sees the effect however it was produced, and which
# runs on the board - therefore in CI, and in gate-complete.sh before any
# session or subagent may finish.
eval "$(python3 "$(dirname "$0")/_input.py")"
if [ "$HOOK_OK" != "1" ]; then echo "BLOCKED (fail-closed): $HOOK_REASON (guard-machinery)" >&2; exit 2; fi
[ -z "$HOOK_CMD" ] && exit 0
ROOT="${CLAUDE_PROJECT_DIR:-.}"; D="$(dirname "$0")"
CHECK="$ROOT/harden/checks/check41_machinery.py"
if [ ! -f "$D/_cmdstrip.py" ] || [ ! -f "$CHECK" ]; then
  echo "BLOCKED (fail-closed): _cmdstrip.py or check41_machinery.py is missing, so a write to verification machinery cannot be told from any other write. (guard-machinery)" >&2; exit 2; fi
TARGETS=$(printf '%s' "$HOOK_CMD" | python3 "$D/_cmdstrip.py" --writes 2>/dev/null) || {
  echo "BLOCKED (fail-closed): could not analyse the command for write targets. (guard-machinery)" >&2; exit 2; }
[ -z "$TARGETS" ] && exit 0
HITS=$(printf '%s\n' "$TARGETS" | python3 "$CHECK" --is-protected 2>/dev/null) || {
  echo "BLOCKED (fail-closed): could not test the write targets against the protected set. (guard-machinery)" >&2; exit 2; }
[ -z "$HITS" ] && exit 0
echo "BLOCKED: this command writes to verification machinery: $(printf '%s' "$HITS" | tr '\n' ' '). Checks, gate ledgers, ci/ and hooks are read-only during a track (PROTOCOL.md). An executor that edits the check grading its own work has moved a gate, not passed one. Propose the change in the audit addendum and let a human commit it. (guard-machinery)" >&2
exit 2
