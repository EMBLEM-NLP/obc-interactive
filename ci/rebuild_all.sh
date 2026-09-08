#!/usr/bin/env bash
# Rebuild every derived artifact from the two source PDFs, in dependency order.
#
# Why this exists
# ---------------
# `.gitignore` says of the 338 MB of derived data: "315 MB, all regenerable or
# re-fetchable". Nothing had ever tested that claim, and until this file there
# was no sequence anywhere in the repository that could. `pipeline/run.sh` is
# stages 0-5 and says so in its own header ("Phases 1-2"); stages 6-9 are loose
# scripts; `pipeline/vol2/` and `pipeline/emitters/` have no entry point at all.
# "Rebuild the data" was knowledge held by whoever last ran it, and nowhere else.
#
# What it needs
#   OBC_SRC_V1, OBC_SRC_V2   the two Crown-copyright source PDFs. Fetch-only:
#                            ci/fetch_sources.sh retrieves them from secret URLs
#                            into /tmp/obc-src and exports these. Never
#                            committed, never redistributed.
#
#   bash ci/rebuild_all.sh              # everything
#   bash ci/rebuild_all.sh --preflight  # only report whether a rebuild can work
#   bash ci/rebuild_all.sh --from vol2  # resume at a phase
set -euo pipefail
cd "$(dirname "$0")/.."
PKG="$(pwd)"
FROM=v1
[ "${1:-}" = "--from" ] && FROM="${2:-v1}"

say() { printf '\n=== %s ===\n' "$*"; }

# ---------------------------------------------------------------------------
# PREFLIGHT, fail-closed, BEFORE any work - because the alternative is finding
# out forty minutes into a hosted run.
#
# R7 says every path resolves from the package root with an env override, and
# PORT rewrote 31 literals across 10 files to make that true. PORT's title is
# "every CHECK runs from the bag", and the pipeline STAGES were outside its
# scope: nobody could re-run them without the fetch-only sources anyway, so the
# gap never showed. It shows now. Three Volume 2 stages hard-wire absolute paths
# belonging to the machine that built the package, with no argv and no env
# fallback, so they read a tree that does not exist in any clone.
#
# stage13_inject2.py reads SOURCE_DATE_EPOCH from the environment nineteen lines
# above its hard-wired sources, so the idiom was known and simply not applied.
#
# This script does not patch them. Editing pipeline stages is track work with
# its own gates, and doing it from inside a rebuild script would be a change
# nobody reviewed, in a file nobody was looking at, to make a number go green.
# ---------------------------------------------------------------------------
# Any build-machine path in a vol2 stage, in ANY assignment form. The first
# version of this anchored on `^(SRC|V1|V2)=` followed immediately by the path
# and so caught stage10 alone: stage12 and stage13 write
# `SRC = {1: "...", 2: "..."}`, where the path sits after a dict key. A
# preflight that reports one of three blockers is worse than none, because it
# reads as though the other two were checked.
BLOCKERS=$(grep -rlE '(/home/claude|/mnt/user-data)' pipeline/vol2/*.py 2>/dev/null || true)

# The SECOND blocker, and the larger one. Every stage writes into out/. Nothing
# committed moves those artifacts to the paths data-manifest.json declares -
# pdf/, model/, verify/data/v1, verify/data/v2 - and nothing encrypts anything.
# The only encryption references in the tree are PDF_ENCRYPT_NONE, in the two
# injectors, which write deliberately UNENCRYPTED files:
#
#   pipeline/stage8b_inject.py:160        encryption=pymupdf.PDF_ENCRYPT_NONE
#   pipeline/vol2/stage13_inject2.py:97   encryption=pymupdf.PDF_ENCRYPT_NONE
#
# So the two *_protected.pdf files - AES-256 per README, 19,524,281 and
# 27,629,429 bytes per the manifest - cannot be produced by any code in this
# repository. harden/make_bag.py does not fill the gap: it shutil.copytree's a
# tree that is already packaged.
#
# 24 of the 29 declared files are stage outputs that a placement step could move
# into position. The 2 protected PDFs need an encryption step that has no
# implementation here at all. Packaging was done by hand, or by something never
# committed, and this is the first time anything has looked.
PACKAGING_GAP=1

preflight() {
  local bad=0
  say "preflight"
  for v in OBC_SRC_V1 OBC_SRC_V2; do
    if [ -z "${!v:-}" ]; then
      echo "  $v unset - run ci/fetch_sources.sh first"; bad=1
    elif [ ! -f "${!v}" ]; then
      echo "  $v points at a file that does not exist: ${!v}"; bad=1
    else
      echo "  $v ok"
    fi
  done
  for m in fitz yaml; do
    if python3 -c "import $m" 2>/dev/null; then echo "  python $m ok"
    else echo "  python $m MISSING"; bad=1; fi
  done
  if [ -n "$BLOCKERS" ]; then
    echo "  Volume 2 cannot run in this checkout. These stages hard-wire a build-machine"
    echo "  path with no argv and no env override, so they read a tree that is not here:"
    for f in $BLOCKERS; do
      echo "    $f"
      grep -nE '(/home/claude|/mnt/user-data)' "$f" | sed 's/^/        /'
    done
    echo "  Fix them under a track, with a gate (R7), before expecting a full rebuild."
    bad=2
  fi
  if [ -n "${PACKAGING_GAP:-}" ]; then
    echo "  No committed code places stage outputs at their shipped paths, and none"
    echo "  encrypts a PDF. Stages write into out/; the manifest declares pdf/, model/"
    echo "  and verify/data/. The only encryption in the tree is PDF_ENCRYPT_NONE, so"
    echo "  the two *_protected.pdf files cannot be produced here by anything at all."
    echo "  A rebuild can therefore regenerate the intermediates and still not populate"
    echo "  the 29 declared paths. This is a gap in the repository, not in this script."
    bad=2
  fi
  return $bad
}

manifest_status() {
  python3 - "$PKG" <<'PY'
import json, os, sys
pkg = sys.argv[1]
files = json.load(open(os.path.join(pkg, "data-manifest.json")))["files"]
by = {}
for f in files:
    area = f["path"].split("/")[0]
    row = by.setdefault(area, [0, 0])
    row[1] += 1
    if os.path.exists(os.path.join(pkg, f["path"])):
        row[0] += 1
have = sum(v[0] for v in by.values())
print(f"  manifest: {have} of {len(files)} present  " +
      "  ".join(f"{k} {v[0]}/{v[1]}" for k, v in sorted(by.items())))
PY
}

if [ "${1:-}" = "--preflight" ]; then
  set +e; preflight; rc=$?; set -e
  manifest_status
  echo
  if [ "$rc" -eq 0 ]; then
    echo "RESULT: PASS - a rebuild can proceed"
  else
    echo "RESULT: FAIL - a rebuild cannot complete in this checkout (see above)"
  fi
  exit "$rc"
fi

preflight || { echo; echo "Refusing to start: preflight failed. Nothing was written."; exit 1; }

# --- Volume 1 ---------------------------------------------------------------
if [ "$FROM" = "v1" ]; then
  say "Volume 1, stages 0-5 (pipeline/run.sh) and their checks"
  ( cd pipeline && bash run.sh "$OBC_SRC_V1" )
  say "Volume 1, stages 6-9"
  ( cd pipeline
    python3 stage6_figures.py "$OBC_SRC_V1"
    python3 stage7_refs.py
    python3 stage8_links.py "$OBC_SRC_V1"
    python3 stage8b_inject.py "$OBC_SRC_V1"
    python3 stage9_amendments.py )
  manifest_status
  FROM=vol2
fi

# --- Volume 2 and the cross-volume merge ------------------------------------
if [ "$FROM" = "vol2" ]; then
  say "Volume 2 and the cross-volume merge"
  ( cd pipeline/vol2
    python3 stage3v2_tree.py
    python3 stage10_merge.py
    python3 stage11_crossvol.py
    python3 stage12_links2.py
    python3 stage13_inject2.py )
  manifest_status
  FROM=emitters
fi

# --- Emitters ---------------------------------------------------------------
if [ "$FROM" = "emitters" ]; then
  say "emitters: SQLite, Markdown, HTML"
  ( cd pipeline/emitters
    python3 stage15_sqlite.py
    python3 stage16_markdown.py
    python3 stage17_html.py )
  manifest_status
  FROM=retrieval
fi

# --- Retrieval layer, including the ONE embed (R8) --------------------------
if [ "$FROM" = "retrieval" ]; then
  say "retrieval: embed once, then definitions and modality"
  bash retrieval/run.sh
  manifest_status
fi

say "verifying the rebuild against data-manifest.json"
python3 harden/checks/check40_dataintegrity.py || {
  echo
  echo "check40 reports the tree does not match the manifest."
  echo "That is a FINDING about determinism, not a step to retry. data-manifest.json"
  echo "carries a sha256 per file and a deterministic pipeline should reproduce them"
  echo "exactly. Record the per-file difference in an audit revision. Do NOT regenerate"
  echo "the manifest to match - verifying data against a manifest derived from the same"
  echo "tree is the circularity the manifest's own note exists to prevent."
  exit 1
}
say "done"
