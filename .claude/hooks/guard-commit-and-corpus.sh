#!/bin/bash
# PreToolUse on Bash. (1) commit requires ci/regenerate.sh since the last edit;
# (2) check33b runs in corpus mode; (3) source PDFs are fetch-only.
eval "$(python3 "$(dirname "$0")/_input.py")"
if [ "$HOOK_OK" != "1" ]; then echo "BLOCKED (fail-closed): $HOOK_REASON (guard-commit)" >&2; exit 2; fi
[ -z "$HOOK_CMD" ] && exit 0
ROOT="${CLAUDE_PROJECT_DIR:-.}"
if echo "$HOOK_CMD" | grep -qE '(^|[;&|[:space:]])git[[:space:]]+commit\b'; then
  STAMP="$ROOT/.regen.stamp"
  if [ ! -f "$STAMP" ]; then
    echo "BLOCKED: no .regen.stamp. Run 'bash ci/regenerate.sh' (docs -> MANIFEST.sha256 -> provenance) before committing. (guard-commit)" >&2; exit 2; fi
  NEWER=$(find "$ROOT" -type f -newer "$STAMP" ! -path '*/.git/*' ! -path '*/__pycache__/*' ! -name '.regen.stamp' \
          ! -name 'gate-board.json' ! -path '*/verify/*/out/*' ! -path '*/pipeline/emitters/out/*' 2>/dev/null | head -3 | tr '\n' ' ')
  if [ -n "$NEWER" ]; then
    echo "BLOCKED: edited after the last regenerate: $NEWER. Run ci/regenerate.sh, then commit. (guard-commit)" >&2; exit 2; fi
fi
if echo "$HOOK_CMD" | grep -q 'check33b_completeness' && ! echo "$HOOK_CMD" | grep -q -- '--all-articles'; then
  echo "BLOCKED: check33b must run with --all-articles; corpus mode gates, eval mode is convenience. (guard-corpus)" >&2; exit 2; fi
if echo "$HOOK_CMD" | grep -qE '30188[01]\.pdf' && ! echo "$HOOK_CMD" | grep -qE 'built_from_model|fetch\.txt'; then
  echo "BLOCKED: the source PDFs are fetch-only (Crown copyright). CI fetches them via ci/fetch_sources.sh from secrets. (guard-source)" >&2; exit 2; fi
exit 0
