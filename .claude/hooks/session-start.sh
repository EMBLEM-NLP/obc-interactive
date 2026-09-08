#!/bin/bash
# SessionStart. Installs dependencies and verifies the data ONLY where they may
# be absent - a hosted or CI environment. Locally this is a no-op so sessions
# start instantly.
#
# CLAUDE_CODE_REMOTE is set to "true" only in cloud sessions.
[ "${CLAUDE_CODE_REMOTE:-false}" = "true" ] || [ -n "${CI:-}" ] || exit 0
ROOT="${CLAUDE_PROJECT_DIR:-.}"; cd "$ROOT" || exit 0
# Light dependencies only. requirements.txt pulls sentence-transformers, whose
# default torch wheel is a ~2.5 GB CUDA build this project never touches; it hit
# ENOSPC twice on 2026-09-07, and a hook is the worst place for it - unattended,
# inside a 600 s timeout, with no shell to intervene. So this hook no longer
# installs the embedding stack at all. R1/R3/R5 SKIP with a stated reason
# without it, which is a visible gap rather than a wedged session. The CPU-only
# two-step install is documented in requirements.txt and done by gates.yml and
# .devcontainer/devcontainer.json, which are attended and budgeted for it.
python3 -c "import mcp, yaml, bagit" 2>/dev/null || python3 -m pip install -q --break-system-packages pyyaml bagit mcp >&2
python3 -c "import sentence_transformers" 2>/dev/null || echo "sentence-transformers absent: R1/R3/R5 will SKIP. See requirements.txt for the CPU-only install." >&2
if ! python3 harden/checks/check40_dataintegrity.py --quick >/dev/null 2>&1; then
  echo "Data files are missing or are LFS pointer stubs. Run: bash ci/fetch_data.sh (needs OBC_DATA_URL or OBC_DATA_DIR). Gates that read data will fail until then." >&2
fi
exit 0
