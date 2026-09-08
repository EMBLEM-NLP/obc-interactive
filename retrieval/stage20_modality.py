#!/usr/bin/env python3
"""
stage20_modality.py - persist deontic modality onto text-bearing leaves.

Why a stage and not a query
---------------------------
`obc_context.py` derives modality at render time. Anything derived at render
time is never validated: there is no artifact to check, no negative control to
run against it, and no way to notice when the rules drift. Modality is the
deontic core any compliance layer consumes, so it belongs in the model with a
check attached.

Classification
--------------
Four categories plus a residual, in evaluation order. Order is load-bearing:
"shall not" must be tested before "shall", or every prohibition is recorded as
an obligation.

  prohibition   shall not, shall in no case, is not permitted
  obligation    shall, must, is required to
  permission    is permitted, may
  exemption     need not, is not required, except
  statement     none of the above - definitions, scope, application text

The residual is large (~49%) and that is correct: roughly half the Code is
scope, application and definitional text carrying no deontic force at all.
Forcing it into a normative bucket would be the error.

Writes a new database; never mutates the input.

    python3 stage20_modality.py --in obc-defs.sqlite --out obc-mod.sqlite
"""

import argparse
import re
import shutil
import sqlite3
import sys

LEAF = ("sentence", "clause", "subclause",
        "act_subsection", "act_clause", "act_subclause")

# (name, pattern). Evaluated in order; first match wins.
RULES = [
    ("prohibition", re.compile(
        r"\bshall\s+not\b|\bshall\s+in\s+no\s+case\b|\bis\s+not\s+permitted\b"
        r"|\bare\s+not\s+permitted\b|\bmay\s+not\b", re.I)),
    ("obligation", re.compile(
        r"\bshall\b|\bmust\b|\bis\s+required\s+to\b|\bare\s+required\s+to\b", re.I)),
    ("permission", re.compile(
        r"\bis\s+permitted\b|\bare\s+permitted\b|\bmay\s+be\b|\bmay\b", re.I)),
    ("exemption", re.compile(
        r"\bneed\s+not\b|\bis\s+not\s+required\b|\bare\s+not\s+required\b"
        r"|\bexcept\b", re.I)),
]


def classify(text):
    for name, rx in RULES:
        if rx.search(text or ""):
            return name
    return "statement"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="src", default="obc-defs.sqlite")
    ap.add_argument("--out", dest="dst", default="obc-mod.sqlite")
    a = ap.parse_args()

    shutil.copyfile(a.src, a.dst)
    c = sqlite3.connect(a.dst)
    c.row_factory = sqlite3.Row

    cols = {r["name"] for r in c.execute("PRAGMA table_info(node)")}
    if "modality" not in cols:
        c.execute("ALTER TABLE node ADD COLUMN modality TEXT")
    c.execute("CREATE INDEX IF NOT EXISTS node_modality ON node(modality)")

    rows = c.execute(
        f"""SELECT id, body FROM node
            WHERE type IN {LEAF} AND body IS NOT NULL AND TRIM(body) != ''"""
    ).fetchall()

    counts = {}
    for r in rows:
        m = classify(r["body"])
        counts[m] = counts.get(m, 0) + 1
        c.execute("UPDATE node SET modality=? WHERE id=?", (m, r["id"]))
    c.commit()

    total = sum(counts.values())
    print(f"text-bearing leaves classified: {total}")
    for k, v in sorted(counts.items(), key=lambda x: -x[1]):
        print(f"  {v:>6}  {100*v/total:5.1f}%  {k}")
    normative = counts.get("obligation", 0) + counts.get("prohibition", 0)
    print(f"\nnormative (obligation + prohibition): {normative}")

    # Sanity invariant, not a threshold: every prohibition contains a negation.
    bad = c.execute(
        """SELECT COUNT(*) FROM node WHERE modality='prohibition'
           AND body NOT LIKE '%not%' AND body NOT LIKE '%Not%'""").fetchone()[0]
    print(f"prohibitions with no negation in the text: {bad}")
    print("\nRESULT:", "PASS" if bad == 0 else f"FAIL {bad} malformed prohibitions")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
