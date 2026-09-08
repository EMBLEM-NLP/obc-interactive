#!/usr/bin/env bash
# Phases 1-2. Deterministic: rerunning from the same source PDF reproduces
# every intermediate. Each stage reads the previous stage's file, not the PDF.
set -euo pipefail
SRC="${1:-/mnt/user-data/uploads/301880.pdf}"
python3 stage0_inventory.py "$SRC"
python3 stage1_geometry.py
python3 stage2_roles.py
python3 stage3_tree.py
echo "=== checks ==="
python3 checks/check0_coverage.py out/inventory.jsonl.gz "$SRC"
python3 checks/check1_regions.py
python3 checks/check2_headings.py | tail -6
python3 checks/check3_continuity.py | tail -4
python3 checks/check4b_capture.py
python3 stage4_tables.py
python3 stage5_bind.py
python3 checks/check5_tables.py
python3 stage6_figures.py "$SRC"
python3 stage7_refs.py
python3 checks/check6_figures.py
python3 checks/check7_refs.py
python3 stage8_links.py "$SRC"
python3 stage8b_inject.py "$SRC"
python3 checks/check8_build.py
python3 stage9_amendments.py
python3 checks/check9_amendments.py
python3 checks/check10_index.py
