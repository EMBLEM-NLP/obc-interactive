#!/usr/bin/env bash
# Regenerate every derived, measured artifact in dependency order.
# Run after ANY edit to the tree and before rebuilding the bag.
#   docs (README, FACTS)  ->  self-manifest  ->  provenance
# Doing these out of order is how H3 and G16d both went red on 2026-09-07:
# README was regenerated AFTER the manifest that lists its hash.
set -euo pipefail
cd "$(dirname "$0")/.."
# make_provenance.py hashes the built PDFs and databases; without them it dies
# with a pymupdf FileNotFoundError and MANIFEST.sha256 is silently left stale -
# which is worse than failing, because the stale manifest then lists 29 files
# that do not exist and every later gate is verified against fiction.
if ! python3 harden/checks/check40_dataintegrity.py --quick >/dev/null 2>&1; then
  echo "regenerate: data files are missing or are pointer stubs." >&2
  echo "  Run: bash ci/fetch_data.sh   (needs OBC_DATA_URL or OBC_DATA_DIR)" >&2
  echo "  Refusing to regenerate - a manifest built now would describe a tree that does not exist." >&2
  exit 1
fi
find . -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
rm -rf verify/*/out pipeline/emitters/out
python3 harden/gen_readme.py "$(pwd)" >/dev/null
python3 - <<'PY'
import os, hashlib
out=[]
for root,dirs,files in os.walk("."):
    dirs[:] = sorted(d for d in dirs if d not in (".git","__pycache__"))
    for f in sorted(files):
        # build outputs are never in the manifest that describes the package:
        # gate-board.json changes every run and put G16d red on the second run
        if f in ("MANIFEST.sha256",".regen.stamp","gate-board.json"): continue
        # data-manifest.json IS included here (it is a tracked input whose hash
        # should change if someone edits it) but is never REGENERATED - see
        # check40. Regenerating it would make check40 circular.
        p=os.path.join(root,f); out.append((hashlib.sha256(open(p,"rb").read()).hexdigest(), os.path.getsize(p), os.path.relpath(p,".")))
with open("MANIFEST.sha256","w") as fh:
    fh.write("# sha256  bytes  path\n")
    for h,n,rel in out: fh.write(f"{h}  {n:>10}  {rel}\n")
print(f"MANIFEST.sha256: {len(out)} entries")
PY
python3 harden/make_provenance.py "$(pwd)"
