#!/bin/bash
# PreToolUse on Bash, wired ONLY into .claude/agents/verify-track.md.
#
# The verifier must not write. Its spec tried to say so two ways, and both
# failed: first a sentence ("You have no write tools") while granting plain
# Bash, then a scoped `tools: Bash(...)` allowlist that a probe showed the
# harness does not enforce - `echo hello > /tmp/verify_probe.txt` ran with no
# refusal on 2026-09-08. The same probe showed a PreToolUse hook DOES fire
# inside a worktree and DID refuse a write to a check. So the allowlist lives
# here, where enforcement was observed rather than assumed.
#
# Default is refusal: anything not recognised as read-only is blocked.
eval "$(python3 "$(dirname "$0")/_input.py")"
if [ "$HOOK_OK" != "1" ]; then echo "BLOCKED (fail-closed): $HOOK_REASON (verify-readonly)" >&2; exit 2; fi
[ -z "$HOOK_CMD" ] && exit 0
D="$(dirname "$0")"
if [ ! -f "$D/_verify_allow.py" ]; then
  echo "BLOCKED (fail-closed): .claude/hooks/_verify_allow.py is missing, so a read-only command cannot be told from a write. (verify-readonly)" >&2; exit 2; fi
VERDICT=$(printf '%s' "$HOOK_CMD" | python3 "$D/_verify_allow.py" 2>/dev/null) || {
  echo "BLOCKED (fail-closed): could not judge the command against the verifier allowlist. (verify-readonly)" >&2; exit 2; }
case "$VERDICT" in
  ALLOW) exit 0 ;;
  DENY*) echo "BLOCKED: ${VERDICT#DENY: }. You verify; you do not fix, and you do not write. Run only the commands in your specification. If you believe this command is necessary to verify the track, say so in your report and stop. (verify-readonly)" >&2; exit 2 ;;
  *)     echo "BLOCKED (fail-closed): unrecognised verdict from the allowlist. (verify-readonly)" >&2; exit 2 ;;
esac
