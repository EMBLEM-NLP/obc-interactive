#!/bin/bash
# SessionStart. Installs dependencies and verifies the data ONLY where they may
# be absent - a hosted or CI environment. Locally this is a no-op so sessions
# start instantly.
#
# CLAUDE_CODE_REMOTE is set to "true" only in cloud sessions.
[ "${CLAUDE_CODE_REMOTE:-false}" = "true" ] || [ -n "${CI:-}" ] || exit 0
ROOT="${CLAUDE_PROJECT_DIR:-.}"; cd "$ROOT" || exit 0
python3 -c "import mcp, yaml, bagit" 2>/dev/null || pip install -q --break-system-packages -r requirements.txt >&2
if ! python3 harden/checks/check40_dataintegrity.py --quick >/dev/null 2>&1; then
  echo "Data files are missing or are LFS pointer stubs. Run: bash ci/fetch_data.sh (needs OBC_DATA_URL or OBC_DATA_DIR). Gates that read data will fail until then." >&2
fi
exit 0
