#!/usr/bin/env bash
# Re-verify every gate in this package from the artifacts it ships.
#
#   GATE_CHECK=/path/to/unlazy/scripts/gate-check.mjs \
#     ./verify/verify.sh /path/to/301880.pdf /path/to/301881.pdf
#
# The two source PDFs are not redistributed here; download them from
# Publications Ontario (#301880, #301881). Everything else is included.
#
# Working sets are materialised by linking the package's own artifacts, so
# nothing is duplicated inside the archive.
set -u
here="$(cd "$(dirname "$0")" && pwd)"
root="$(cd "$here/.." && pwd)"
export OBC_SRC_V1="${1:?give the path to 301880.pdf}"
export OBC_SRC_V2="${2:?give the path to 301881.pdf}"
export OBC_BASELINE="$here/baseline/v9-baseline.json"
export OBC_ZIP="${OBC_ZIP:-$root/../obc-interactive.zip}"
export OBC_PROTECTED="$root/pdf/301880_built_from_model_protected.pdf"
export OBC_MASTER="$root/pdf/301880_built_from_model.pdf"
GC="${GATE_CHECK:?set GATE_CHECK to the path of unlazy/scripts/gate-check.mjs}"

link() { mkdir -p "$(dirname "$2")"; ln -sf "$1" "$2" 2>/dev/null || cp "$1" "$2"; }

# volume 1 working set
for f in "$here"/data/v1/*; do link "$f" "$here/volume1/out/$(basename "$f")"; done
link "$root/pdf/301880_built_from_model.pdf" "$here/volume1/out/301880_built.pdf"
link "$root/pdf/301881_built_from_model.pdf" "$here/volume1/out/301881_built.pdf"
# volume 2 working set
for f in "$here"/data/v2/*; do link "$f" "$here/volume2/out/$(basename "$f")"; done
link "$here/data/v2/docgraph-merged.jsonl.gz" "$here/volume2/out/docgraph.jsonl.gz"
link "$root/pdf/301881_built_from_model.pdf" "$here/volume2/out/301881_built.pdf"
link "$root/pdf/301880_built_from_model.pdf" "$here/volume2/out/301880_built.pdf"
# emitters working set
link "$root/emitters/obc.sqlite" "$here/emitters/out/obc.sqlite"
link "$here/data/v2/docgraph-merged.jsonl.gz" "$here/emitters/out/docgraph-merged.jsonl.gz"
mkdir -p "$here/emitters/out"
tar xzf "$root/emitters/markdown.tar.gz" -C "$here/emitters/out"
tar xzf "$root/emitters/html.tar.gz"     -C "$here/emitters/out"

rc=0
for scope in volume1 volume2 emitters; do
  echo "=== $scope ==="
  ( cd "$here/$scope" && node "$GC" --approve GATES.md ) || rc=1
done
exit $rc
