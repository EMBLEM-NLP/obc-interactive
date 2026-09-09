#!/usr/bin/env python3
"""Place stage outputs at the paths data-manifest.json declares.

Why this did not exist
----------------------
Every pipeline stage writes into `out/`. `data-manifest.json` declares 29 files
under `model/`, `pdf/`, `emitters/` and `verify/data/`. Nothing committed moved
one to the other. A rebuild could regenerate every intermediate correctly and
still leave all 29 declared paths empty, which is what ci/rebuild_all.sh's
preflight found on 2026-09-09.

The map below is the knowledge that was lost when the machine that built the
package in September went away. It was a Claude desktop session; the container
is gone, and with it the only place the packaging steps were ever performed.

READ THIS BEFORE TRUSTING THE MAP
---------------------------------
Entries marked INFERRED were derived by reading what each stage writes and
matching it to what the manifest declares. They have NOT been executed against a
real `out/` directory, because this clone has none and the sources are
fetch-only. Entries marked CONFIRMED are ones where a stage names the
destination itself.

So this file is a specification first and a tool second. `--plan` prints the map
and what it would do without touching anything; run that against a real rebuild
before running the tool, and correct any INFERRED line that turns out wrong.
Shipping a confident mapping that has never run is the mistake AUDIT-rev9 named,
and marking the inference is the difference between a proposal and a claim.

    python3 harden/place_artifacts.py --plan     # show the map, move nothing
    python3 harden/place_artifacts.py --volume 1 # snapshot out/ as verify/data/v1
    python3 harden/place_artifacts.py            # place everything it can
"""
import argparse
import gzip
import json
import os
import shutil
import sys

_PKG = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
OUT = os.environ.get("OBC_OUT", os.path.join(_PKG, "out"))

# destination (as declared in data-manifest.json) -> (source under out/, how, confidence)
#   how: "copy" | "gzip" (compress on the way) | "insitu" (the stage already
#        writes the destination) | "stage14" (produced by the protect stage)
MAP = {
    "model/docgraph-merged.jsonl.gz": ("docgraph-merged.jsonl.gz", "copy", "INFERRED"),
    "model/figures-v1.jsonl.gz":      ("figures.jsonl.gz",         "copy", "INFERRED"),
    "model/tables-v1.jsonl.gz":       ("tables.jsonl.gz",          "copy", "INFERRED"),
    "model/pdf-links-v1.json.gz":     ("pdf-links-v1.json",        "gzip", "INFERRED"),
    "model/pdf-links-v2.json.gz":     ("pdf-links-v2.json",        "gzip", "INFERRED"),
    # stage8b_inject and stage13_inject2 name out/<n>_built.pdf themselves; the
    # shipped name differs, which is why a rename step has to exist somewhere.
    "pdf/301880_built_from_model.pdf": ("301880_built.pdf", "copy", "CONFIRMED"),
    "pdf/301881_built_from_model.pdf": ("301881_built.pdf", "copy", "CONFIRMED"),
    "pdf/301880_built_from_model_protected.pdf": (None, "stage14", "CONFIRMED"),
    "pdf/301881_built_from_model_protected.pdf": (None, "stage14", "CONFIRMED"),
    # The emitter stages resolve emitters/ from the package root via
    # emit_common._PKG and write there directly, so nothing needs moving.
    "emitters/obc.sqlite":      (None, "insitu", "CONFIRMED"),
    "emitters/obc-vec.sqlite":  (None, "insitu", "CONFIRMED"),
    "emitters/obc-mod.sqlite":  (None, "insitu", "CONFIRMED"),
    "emitters/markdown.tar.gz": (None, "insitu", "INFERRED"),
    "emitters/html.tar.gz":     (None, "insitu", "INFERRED"),
}

# verify/data/v1 and v2 are SNAPSHOTS of out/ taken after each volume's stages,
# and taking them is not optional housekeeping - it is the missing mechanism the
# whole Volume 2 problem rests on. Both volumes write into one out/, so Volume
# 2's stage0-2 overwrite Volume 1's inventory, geometry and roles. That is why
# stage10_merge.py hard-codes /home/claude/obc/out/docgraph-v1only.jsonl.gz:
# somebody had to stash Volume 1's graph before Volume 2 clobbered it. Snapshot
# per volume and the hard-coded path stops being necessary.
SNAPSHOT = {
    1: ["inventory.jsonl.gz", "geometry.jsonl.gz", "roles.jsonl.gz", "docgraph.jsonl.gz",
        "figures.jsonl.gz", "tables.jsonl.gz", "labels.json", "pdf-links.json"],
    2: ["inventory.jsonl.gz", "geometry.jsonl.gz", "roles.jsonl.gz", "docgraph.jsonl.gz",
        "docgraph-vol2only.jsonl.gz", "docgraph-merged.jsonl.gz", "pdf-links-v2.json"],
}


def declared():
    return [f["path"] for f in json.load(
        open(os.path.join(_PKG, "data-manifest.json")))["files"]]


def coverage():
    """Every declared path must be accounted for by MAP or SNAPSHOT. A placement
    step that silently skips a file is how 29 declared paths stay empty."""
    covered = set(MAP)
    for vol, names in SNAPSHOT.items():
        covered |= {f"verify/data/v{vol}/{n}" for n in names}
    want = set(declared())
    return sorted(want - covered), sorted(covered - want)


def place(dst_rel, src_name, how, dry):
    dst = os.path.join(_PKG, dst_rel)
    if how == "insitu":
        return "already written there by its stage" if os.path.exists(dst) else "MISSING - stage did not run"
    if how == "stage14":
        return "already written there" if os.path.exists(dst) else "run pipeline/stage14_protect.py"
    src = os.path.join(OUT, src_name)
    if not os.path.exists(src):
        return f"source absent: out/{src_name}"
    if dry:
        return f"would {how} out/{src_name}"
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    if how == "gzip":
        with open(src, "rb") as fh, gzip.GzipFile(dst, "wb", mtime=0) as gz:
            shutil.copyfileobj(fh, gz)          # mtime=0: gzip headers carry a
    else:                                        # timestamp, and a timestamp in a
        shutil.copy2(src, dst)                   # digested artifact is H1's problem
    return f"{how}ed from out/{src_name}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--plan", action="store_true", help="show the map, move nothing")
    ap.add_argument("--volume", type=int, choices=(1, 2), help="snapshot out/ for one volume")
    a = ap.parse_args()
    dry = a.plan

    missing, extra = coverage()
    if missing:
        print("These declared paths are covered by NOTHING in this file:")
        for m in missing:
            print(f"  {m}")
        print("\nRefusing to run. A placement step that cannot account for every declared")
        print("path would leave a rebuild silently incomplete, which is the failure it exists")
        print("to prevent.")
        sys.exit(1)
    if extra:
        print("Mapped but not declared in data-manifest.json (harmless, worth knowing):")
        for e in extra:
            print(f"  {e}")

    if a.volume:
        rows = [(f"verify/data/v{a.volume}/{n}", n, "copy", "INFERRED")
                for n in SNAPSHOT[a.volume]]
    else:
        rows = [(d, s, h, c) for d, (s, h, c) in MAP.items()]

    print(f"{'destination':46} {'confidence':10} action")
    print("-" * 100)
    for dst_rel, src_name, how, conf in rows:
        print(f"  {dst_rel:44} {conf:10} {place(dst_rel, src_name, how, dry)}")

    n_inf = sum(1 for r in rows if r[3] == "INFERRED")
    print(f"\n{len(rows)} entries, {n_inf} INFERRED and never executed against a real out/.")
    print("Run --plan against a real rebuild and correct any INFERRED line that is wrong")
    print("before trusting this to place anything.")


if __name__ == "__main__":
    main()
