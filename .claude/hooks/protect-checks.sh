#!/bin/bash
# PreToolUse on Edit|Write. Verification machinery is read-only to executors.
# Every vacuous gate this project shipped was green; an agent told to make the
# board pass will edit the check. exit 2 = block, stderr is the reason to Claude.
eval "$(python3 "$(dirname "$0")/_input.py")"
if [ "$HOOK_OK" != "1" ]; then echo "BLOCKED (fail-closed): $HOOK_REASON (protect-checks)" >&2; exit 2; fi
[ -z "$HOOK_FILE" ] && exit 0
case "$HOOK_FILE" in
  *harden/checks/*|*retrieval/checks/*|*verify/*/checks/*|*pipeline/checks/*|*pipeline/*/checks/*| \
  *ci/checks.yaml|*ci/run_gates.py|*ci/regenerate.sh|*gates/GATES-*.md|*.claude/hooks/*|*.claude/settings.json)
    echo "BLOCKED: $HOOK_FILE is verification machinery, read-only during a track. Propose the change in the audit addendum for human review. (protect-checks)" >&2
    exit 2 ;;
esac
exit 0
