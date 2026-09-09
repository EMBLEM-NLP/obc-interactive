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
#   bash ci/rebuild_all.sh --from vol2  # resume at a phase (v1|vol2|emitters|protect|retrieval)
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

# The SECOND blocker, ADDRESSED 2026-09-09 but not yet proven. Every stage writes
# into out/; data-manifest.json declares pdf/, model/, emitters/ and
# verify/data/. Nothing committed moved one to the other, and nothing encrypted
# anything - the only encryption references in the tree were PDF_ENCRYPT_NONE,
# in the two injectors, which write deliberately UNENCRYPTED masters.
#
# Two new pieces close it:
#   pipeline/stage14_protect.py   applies the ministry permission set. Tested
#                                 end to end on a synthetic PDF (--selftest),
#                                 with a control proving its verifier rejects an
#                                 unencrypted file.
#   harden/place_artifacts.py     maps every one of the 29 declared paths to the
#                                 stage output that fills it, and REFUSES to run
#                                 if any declared path is unaccounted for.
#
# Half of that map is marked INFERRED and has never run against a real out/,
# because this clone has none. `--plan` prints it without moving anything; run
# that first on a real rebuild and correct what is wrong. The map is a
# specification recovered by reading the stages, not a tested tool.
#
# Measured while building it: encrypted PDFs are NOT byte-reproducible. Same
# content, same password, different bytes every run, because PDF AES draws a
# random IV. data-manifest.json's sha256 for the two protected files therefore
# cannot be matched by any rebuild, ever. That is the format, not a defect - but
# it means "29 of 29 identical" is not an achievable result and never was.
PACKAGING_GAP="partial"

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
  if [ "${PACKAGING_GAP:-}" = "partial" ]; then
    echo "  Packaging exists now but is unproven. pipeline/stage14_protect.py applies the"
    echo "  permission set (tested on a synthetic PDF) and harden/place_artifacts.py maps"
    echo "  all 29 declared paths to the outputs that fill them - but half that map is"
    echo "  marked INFERRED and has never run against a real out/. Run"
    echo "    python3 harden/place_artifacts.py --plan"
    echo "  during the first real rebuild and correct any INFERRED line that is wrong."
    echo "  Note also: encrypted PDFs are not byte-reproducible, so the manifest's sha256"
    echo "  for the two protected files can never be matched. 27 of 29 is the ceiling."
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
  FROM=protect
fi

# --- Protect the built PDFs, then place everything --------------------------
if [ "$FROM" = "protect" ]; then
  say "applying the ministry permission set to the built PDFs"
  python3 pipeline/stage14_protect.py
  say "placing stage outputs at the paths data-manifest.json declares"
  python3 harden/place_artifacts.py
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
