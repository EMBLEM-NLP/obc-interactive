#!/bin/bash
# PreToolUse on Bash. (1) a commit requires ci/regenerate.sh since the last
# edit; (2) check33b runs in corpus mode; (3) source PDFs are fetch-only.
eval "$(python3 "$(dirname "$0")/_input.py")"
if [ "$HOOK_OK" != "1" ]; then echo "BLOCKED (fail-closed): $HOOK_REASON (guard-commit)" >&2; exit 2; fi
[ -z "$HOOK_CMD" ] && exit 0
ROOT="${CLAUDE_PROJECT_DIR:-.}"
D="$(dirname "$0")"

# Whether this command RUNS a git-commit invocation is decided by _cmdstrip.py,
# which lexes the command instead of grepping it. The previous regex matched the
# verb anywhere in the string, so writing a message file with a heredoc that
# mentioned it was refused as though it were a real commit (observed 2026-09-08).
# Grepping cannot tell data from code; a stripper that removed quoted spans
# would tell them apart the WRONG way and wave through bash -c '<the verb> ...'.
if [ ! -f "$D/_cmdstrip.py" ]; then
  echo "BLOCKED (fail-closed): .claude/hooks/_cmdstrip.py is missing, so a commit cannot be distinguished from a mention of one. (guard-commit)" >&2; exit 2; fi
VERDICT=$(printf '%s' "$HOOK_CMD" | python3 "$D/_cmdstrip.py" 2>/dev/null)
if [ $? -ne 0 ] || { [ "$VERDICT" != "COMMIT" ] && [ "$VERDICT" != "NONE" ]; }; then
  echo "BLOCKED (fail-closed): could not analyse the command for a commit invocation. (guard-commit)" >&2; exit 2; fi

if [ "$VERDICT" = "COMMIT" ]; then
  STAMP="$ROOT/.regen.stamp"
  if [ ! -f "$STAMP" ]; then
    echo "BLOCKED: no .regen.stamp. Run 'bash ci/regenerate.sh' (docs -> MANIFEST.sha256 -> provenance) before committing. (guard-commit)" >&2; exit 2; fi
  NEWER=$(find "$ROOT" -type f -newer "$STAMP" ! -path '*/.git/*' ! -path '*/__pycache__/*' ! -name '.regen.stamp' \
          ! -name 'gate-board.json' ! -path '*/verify/*/out/*' ! -path '*/pipeline/emitters/out/*' 2>/dev/null | head -3 | tr '\n' ' ')
  if [ -n "$NEWER" ]; then
    echo "BLOCKED: edited after the last regenerate: $NEWER. Run ci/regenerate.sh, then commit. (guard-commit)" >&2; exit 2; fi
fi

# Whether check33b is being RUN, and in which mode, is decided by lexing - not
# by grepping the command string. The old test refused `grep -rn
# check33b_completeness .` and even `cat` on the file, because reading about a
# check looked identical to running it.
MODE=$(printf '%s' "$HOOK_CMD" | python3 "$D/_cmdstrip.py" --check33b 2>/dev/null) || {
  echo "BLOCKED (fail-closed): could not determine whether check33b is being run. (guard-corpus)" >&2; exit 2; }
if [ "$MODE" = "EVAL" ]; then
  echo "BLOCKED: check33b must run with --all-articles; corpus mode gates, eval mode is convenience. (guard-corpus)" >&2; exit 2; fi
if echo "$HOOK_CMD" | grep -qE '30188[01]\.pdf' && ! echo "$HOOK_CMD" | grep -qE 'built_from_model|fetch\.txt'; then
  echo "BLOCKED: the source PDFs are fetch-only (Crown copyright). CI fetches them via ci/fetch_sources.sh from secrets. (guard-source)" >&2; exit 2; fi
exit 0
