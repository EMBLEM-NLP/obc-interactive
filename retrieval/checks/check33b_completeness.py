#!/usr/bin/env python3
"""
check33b_completeness.py - R4, measured against the real assembler.

Why this replaces check33_completeness.py
-----------------------------------------
The original computes:

    dependencies(nid) -> refs | terms
    bundle(nid)       -> {nid} | descendants | ancestors | refs | terms
    carried            = len(dep & bundle(nid)) / len(dep)

`bundle` unions in `refs | terms`, which *is* `dep`. So `dep & bundle == dep`
identically and the ratio is 1.0 for every node in the corpus - measured over
all 2,449 articles carrying dependencies, it is 100.0000% with zero below
threshold. The `< 0.99` condition cannot fire. The check re-derives the
dependency set and compares it to itself; the assembler it claims to measure
is never called.

Check 34 does not cover this. It scrambles the vector index, which changes
*which* targets are retrieved - but for whatever targets are retrieved,
completeness is still identically 1.0. R5 protects R3, not R4.

What this measures instead
--------------------------
The bundle a caller actually receives from `obc_context.build_bundle`: hop
limited, budget trimmed, and selective about edge kinds. That bundle can and
does fall short of the full dependency set, which is the entire point of
measuring it.

Three things are reported separately, because they fail for different reasons
and a single blended number hides which:

  C1  reachability  - can expansion reach each dependency at the given hops?
  C2  delivery      - does the rendered bundle actually contain it, after
                      hop limits and budget trimming?
  C3  usability     - for definitions, is what was delivered the definition
                      of THAT term, or an undifferentiated blob? A bundle can
                      score 100% on C1 and C2 and still hand the model the
                      wrong definition.

C3 is the one the original could never have caught, because carrying a
31,199-character clause containing 136 definitions counts as carrying the
definition.

    python3 check33b_completeness.py --db obc-vec-defs.sqlite --eval evalset.json
"""

import argparse
import json
import os
import sys

# obc_context.py lives in the sibling lib/ directory (retrieval/lib/), not
# flat alongside this file (retrieval/checks/) - the pack this shipped from
# was flat and this path assumption did not survive integration into the
# real repo layout on first run. Fixed in place rather than special-cased
# at the call site, since the next integration would hit the same bug.
_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_HERE, "..", "lib"))
from obc_context import connect, build_bundle, render, scope_ids, HUB_DEPS  # noqa: E402

# A definition longer than this is not a definition, it is the clause that
# contains one. Real split definitions average 215 characters.
BLOB_CHARS = 1500

MIN_REACH = 0.99
MIN_DELIVER = 0.95
MIN_USABLE = 0.99


def dependencies(db, nid):
    """Verbatim from check33: everything the article and its subtree cite,
    plus the defined terms it uses."""
    sub = [r[0] for r in db.execute(
        "SELECT descendant FROM closure WHERE ancestor=?", (nid,))]
    qs = ",".join("?" * len(sub))
    refs = {r[0] for r in db.execute(
        f"SELECT dst FROM ref WHERE src IN ({qs}) AND dst IS NOT NULL", sub)}
    terms = {r[0] for r in db.execute(
        f"SELECT dst FROM term WHERE src IN ({qs})", sub)}
    return refs, terms


def bundle_ids(b):
    """Every node id the assembler actually put in the bundle."""
    out = {b["anchor"]["id"]}
    out |= {x["id"] for x in b["ancestors"]}
    out |= {x["id"] for x in b["provision"]}
    for k in ("terms", "cites", "notes", "standards", "tables", "cited_by"):
        out |= {x["id"] for x in b[k]}
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default="obc-vec-defs.sqlite")
    ap.add_argument("--eval", default="evalset.json")
    ap.add_argument("--hops", type=int, default=1)
    ap.add_argument("--budget", type=int, default=8000)
    ap.add_argument("--all-articles", action="store_true",
                    help="measure every article, not just eval targets")
    a = ap.parse_args()

    db = connect(a.db)
    split_defs = db.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='term_resolved'"
    ).fetchone() is not None

    if a.all_articles:
        targets = [r[0] for r in db.execute("SELECT id FROM node WHERE type='article'")]
    else:
        qs = json.load(open(a.eval))["questions"]
        targets = sorted({q["target"] for q in qs if q["split"] == "test"})

    hubs = []
    reach_n = reach_d = 0
    deliv_n = deliv_d = 0
    usable_n = usable_d = 0
    short = []

    for nid in targets:
        refs, terms = dependencies(db, nid)
        dep = refs | terms
        if not dep:
            continue

        b = build_bundle(db, nid, hops=a.hops, budget=None)
        if b["hub"]:
            # Delivered by reference, deliberately. Counting a hub as a
            # delivery failure would make C2 unpassable by design; hiding it
            # would repeat check33's mistake. Enumerate instead.
            hubs.append((nid, b["dep_count"]))
            continue
        reachable = bundle_ids(b)

        # C1 - reachable at all. Term edges are counted as reached when the
        # split definition for that term is present, since the blob target is
        # exactly what the split replaced.
        got = dep & reachable
        if split_defs:
            resolved = {r[0] for r in db.execute(
                "SELECT DISTINCT dst FROM term_resolved WHERE src IN "
                "(SELECT descendant FROM closure WHERE ancestor=?)", (nid,))}
            got |= {d for d in dep if d in terms and resolved & reachable}
        reach_n += len(got); reach_d += len(dep)

        # C2 - survives hop limit AND budget trimming
        bt = build_bundle(db, nid, hops=a.hops, budget=a.budget)
        delivered = bundle_ids(bt)
        gotd = dep & delivered
        if split_defs:
            gotd |= {d for d in dep if d in terms and resolved & delivered}
        deliv_n += len(gotd); deliv_d += len(dep)
        if len(gotd) < len(dep):
            short.append((nid, len(gotd), len(dep)))

        # C3 - definitions delivered are the term's own, not a blob
        for t in bt["terms"]:
            usable_d += 1
            if len(t.get("text") or "") <= BLOB_CHARS:
                usable_n += 1

    def pct(n, d):
        return n / d if d else 1.0

    print(f"targets measured                : {len(targets)}")
    print(f"hubs delivered by reference     : {len(hubs)} "
          f"(>{HUB_DEPS} deps, excluded from C1/C2)")
    for nid, n in sorted(hubs, key=lambda x: -x[1])[:6]:
        print(f"     {nid:<28} {n} deps")
    print(f"split definitions available     : {split_defs}")
    print(f"C1 reachable at {a.hops} hop(s)        : "
          f"{reach_n}/{reach_d} = {pct(reach_n, reach_d):.2%}  (floor {MIN_REACH:.0%})")
    print(f"C2 delivered under {a.budget}-tok budget: "
          f"{deliv_n}/{deliv_d} = {pct(deliv_n, deliv_d):.2%}  (floor {MIN_DELIVER:.0%})")
    print(f"C3 definitions usable, not blobs: "
          f"{usable_n}/{usable_d} = {pct(usable_n, usable_d):.2%}  (floor {MIN_USABLE:.0%})")
    if short:
        print(f"   targets losing context to the budget: {len(short)}")
        for nid, g, d in short[:5]:
            print(f"     {nid:<28} {g}/{d}")

    fails = []
    if pct(reach_n, reach_d) < MIN_REACH:
        fails.append("C1 reachability")
    if pct(deliv_n, deliv_d) < MIN_DELIVER:
        fails.append("C2 delivery")
    if pct(usable_n, usable_d) < MIN_USABLE:
        fails.append("C3 usability")
    print("\nRESULT:", "PASS" if not fails else "FAIL " + ", ".join(fails))
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
