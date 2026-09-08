#!/usr/bin/env bash
# Retrieval-layer build. Reads emitters/obc.sqlite, writes obc-mod.sqlite.
# Each stage reads the previous stage's file, matching pipeline/run.sh's
# convention. This file did not exist before 2026-09-07: stage19_embed.py
# and checks 30-34 were previously run individually with no shared entry
# point. Added as part of integrating the remediation pack (see
# gates/GATES-remediation.md), not as a separate initiative.
#
# Usage:
#   sh run.sh                 # start from emitters/obc.sqlite, embed + fix
#   sh run.sh emitters/obc-vec.sqlite   # already-embedded input, skip stage19
set -euo pipefail
cd "$(dirname "$0")"
IN="${1:-}"

if [ -z "$IN" ]; then
  echo "=== stage19: embed articles ==="
  python3 stage19_embed.py --in ../emitters/obc.sqlite --out ../emitters/obc-vec.sqlite
  IN=../emitters/obc-vec.sqlite
fi

echo "=== stage18: split definition blobs ==="
python3 stage18_definitions.py --in "$IN" --out ../emitters/obc-defs.sqlite

echo "=== check29 (D1) ==="
python3 checks/check29_definitions.py --db ../emitters/obc-defs.sqlite

echo "=== check29 negative control (must FAIL) ==="
cp ../emitters/obc-defs.sqlite /tmp/neg29.sqlite
if NEGATIVE=1 python3 checks/check29_definitions.py --db /tmp/neg29.sqlite >/dev/null 2>&1; then
  echo "RESULT: FAIL - negative control passed, D1 is void"; exit 1
fi
echo "RESULT: PASS - control correctly failed"
rm -f /tmp/neg29.sqlite

echo "=== stage20: persist deontic modality ==="
python3 stage20_modality.py --in ../emitters/obc-defs.sqlite --out ../emitters/obc-mod.sqlite

echo "=== check33b (R4a/b/c): whole corpus ==="
python3 checks/check33b_completeness.py --db ../emitters/obc-mod.sqlite --all-articles

echo "=== check35 (H10): every ratio must be falsifiable ==="
python3 ../harden/checks/check35_controls.py --db ../emitters/obc-mod.sqlite

echo
echo "done -> emitters/obc-mod.sqlite"
