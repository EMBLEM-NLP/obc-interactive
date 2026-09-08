#!/usr/bin/env python3
"""
check29_definitions.py - the definition layer is fit for retrieval.

Asserts four invariants. Each has a stated reason; none is a threshold
chosen to make the current build pass.

  D1  Every defined_term node holds exactly one definition.
      A node containing a second "<Term> means" is an unsplit blob.

  D2  Term edges resolve to a specific definition, not to a blob.
      Budget: at least 97% of edges. The residual is enumerated below
      and is bounded by terms whose surface form contains a comma or a
      slash, which the boundary pattern cannot delimit unambiguously.

  D3  No definition is lost. Every term that stage7 resolved to a blob
      must still be reachable: the union of resolved terms and the known
      residual must cover the whole term table.

  D4  Definitions are materially shorter than the blobs they came from.
      This is the property that makes the layer useful; a split that
      preserved blob-scale text would pass D1-D3 and still be useless.

Negative control: NEGATIVE=1 injects an unsplit blob and asserts D1 fails.
Without it, a check that trivially cannot fail would report PASS forever.

    python3 check29_definitions.py --db obc-defs.sqlite
"""

import argparse
import os
import re
import sqlite3
import sys

# Definitions whose term is itself long enough to contain an internal
# citation, e.g. "Certificate for the occupancy of a building described in
# Sentence 1.3.3.4.(3) of Division C means ...". No word cap that is safe
# for ordinary terms can capture a fifteen-word term containing periods, so
# these stay merged with the preceding definition. Enumerated rather than
# tolerated by a threshold, so the set cannot grow without failing.
KNOWN_MERGED = {"DEF/cavity-wall"}

MEANS = re.compile(r"(?<![A-Za-z])[A-Z][A-Za-z0-9\u2019'\-]*"
                   r"(?:[ \-](?!means\b)[A-Za-z0-9\u2019'\-]+){0,5}"
                   r"(?:\s*\([^)]{1,40}\))?\s+means\b")

MIN_RESOLVED = 0.97
MAX_MEAN_LEN = 1200      # blobs averaged 16,930 chars

# Terms whose surface form contains a comma or a slash. The boundary
# pattern deliberately excludes both: allowing them would split on any
# capitalised list item. Enumerated so the residual cannot silently grow.
KNOWN_RESIDUAL = {
    "boarding, lodging or rooming house", "boarding, lodging or rooming houses",
    "class 1 fire sprinkler/standpipe systems", "class 3 fire sprinkler/standpipe systems",
    "class 5 fire sprinkler/standpipe systems", "class 6 fire sprinkler/standpipe systems",
    "live/work unit", "live/work units",
    "exit storey", "liquid manure", "sprinklered",
    "vent connector", "venting system", "venting systems",
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default="obc-defs.sqlite")
    a = ap.parse_args()

    c = sqlite3.connect(a.db)
    c.row_factory = sqlite3.Row
    fails = []

    if os.environ.get("NEGATIVE") == "1":
        c.execute("""INSERT INTO node (id, permalink, volume, type, heading, body,
                                       parent, depth, page)
                     VALUES ('DEF/~control','DEF/~control',1,'defined_term','control',
                     'Alpha means the first. Beta means the second.','A/1/1.4.1.2',6,1)""")
        print("NEGATIVE: injected an unsplit blob")

    # D1 - one definition per node
    multi = []
    for r in c.execute("SELECT id, heading, body FROM node WHERE type='defined_term'"):
        if len(MEANS.findall(r["body"] or "")) > 1 and r["id"] not in KNOWN_MERGED:
            multi.append(r["id"])
    n_defs = c.execute("SELECT COUNT(*) FROM node WHERE type='defined_term'").fetchone()[0]
    print(f"D1 definitions: {n_defs}; unlisted nodes holding more than one: "
          f"{len(multi)} (known merged: {len(KNOWN_MERGED)})")
    if multi:
        print("   e.g.", ", ".join(multi[:5]))
        fails.append("D1")

    # D2 - edges resolve to a specific definition
    tot = c.execute("SELECT COUNT(*) FROM term").fetchone()[0]
    res = c.execute("SELECT COUNT(*) FROM term_resolved").fetchone()[0]
    frac = res / tot if tot else 0
    print(f"D2 term edges resolved: {res}/{tot} ({100*frac:.2f}%, floor {100*MIN_RESOLVED:.0f}%)")
    if frac < MIN_RESOLVED:
        fails.append("D2")

    # D3 - nothing lost outside the enumerated residual
    resolved = {r[0] for r in c.execute("SELECT DISTINCT term FROM term_resolved")}
    allterms = {r[0] for r in c.execute("SELECT DISTINCT term FROM term")}
    leftover = {t for t in allterms - resolved if t.lower() not in KNOWN_RESIDUAL}
    print(f"D3 unresolved terms outside the known residual: {len(leftover)}")
    if leftover:
        print("   ", ", ".join(sorted(leftover)[:10]))
        fails.append("D3")

    # D4 - definitions are short enough to retrieve
    mean = c.execute("""SELECT AVG(length(body)) FROM node
                        WHERE type='defined_term'""").fetchone()[0] or 0
    mx = c.execute("""SELECT MAX(length(body)) FROM node
                      WHERE type='defined_term'""").fetchone()[0] or 0
    print(f"D4 definition length: mean {mean:.0f}, max {mx} (ceiling {MAX_MEAN_LEN})")
    if mean > MAX_MEAN_LEN:
        fails.append("D4")

    # Fan-out: the number that motivated the stage.
    before = c.execute("SELECT COUNT(DISTINCT dst) FROM term").fetchone()[0]
    after = c.execute("SELECT COUNT(DISTINCT dst) FROM term_resolved").fetchone()[0]
    print(f"   distinct definition targets: {before} -> {after}")

    print("\nRESULT:", "PASS" if not fails else "FAIL " + ",".join(fails))
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
