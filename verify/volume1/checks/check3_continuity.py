#!/usr/bin/env python3
"""Check 3 - numbering continuity: the Phase 2 gate.

Within every parent, children must run consecutively from 1 (or from 'a' / 'i').
A gap is a defect unless the document says Reserved or Repealed there. This
catches parse errors and genuine holes in the source with the same test.
"""
import sys, os
import gzip, json, re
from collections import defaultdict

nodes = {}
with gzip.open("out/docgraph.jsonl.gz", "rt") as fh:
    for line in fh:
        r = json.loads(line)
        if not r.get("_meta"):
            nodes[r["id"]] = r

ROMAN = ["i", "ii", "iii", "iv", "v", "vi", "vii", "viii", "ix", "x", "xi", "xii",
         "xiii", "xiv", "xv", "xvi", "xvii", "xviii", "xix", "xx", "xxi", "xxii",
         "xxiii", "xxiv", "xxv"]

def body(nid):
    n = nodes[nid]
    s = " ".join(t["t"] for t in n["text"])[:200]
    return (n.get("heading") or "") + " " + s

def tail(num):
    t = num.split(".")[-1] if "." in num else num
    return re.sub(r"[A-Z]+$", "", t)      # 7.6.2.5A belongs at position 5

gaps = defaultdict(list)
checked = 0
for nid, n in nodes.items():
    kids = [nodes[c] for c in n["children"]]
    if len(kids) < 2:
        continue
    kinds = {k["type"] for k in kids}
    if len(kinds) != 1:
        continue
    kind = kinds.pop()
    checked += 1
    if kind in ("section", "subsection", "article"):
        seq = []
        for k in kids:
            t = tail(k["number"])
            if t.isdigit():
                seq.append((int(t), k["id"]))
    elif kind == "sentence":
        seq = [(int(float(k["number"])), k["id"]) for k in kids
               if re.fullmatch(r"\d+(\.\d+)?", k["number"])]
    elif kind == "clause":
        seq = [(ord(k["number"][0]) - 96, k["id"]) for k in kids
               if re.fullmatch(r"[a-z](\.\d+)?", k["number"])]
    elif kind == "subclause":
        seq = [(ROMAN.index(k["number"]) + 1, k["id"]) for k in kids
               if k["number"] in ROMAN]
    else:
        continue
    seq.sort()
    if not seq:
        continue
    seen = {v for v, _ in seq}
    lo, hi = 1, max(seen)
    for v in range(lo, hi + 1):
        if v in seen:
            continue
        nb = " ".join(body(i) for _, i in seq)
        excused = bool(re.search(r"Reserved|REPEALED|Repealed", nb))
        gaps[kind].append((nid, v, excused))

print(f"parents checked: {checked}")
tot = unexcused = 0
for kind, g in gaps.items():
    ue = [x for x in g if not x[2]]
    tot += len(g); unexcused += len(ue)
    print(f"  {kind:<11} gaps {len(g):<5} unexplained {len(ue)}")
    for nid, v, _ in ue[:6]:
        print(f"      {nid}  missing #{v}")
print(f"\ntotal gaps {tot} | unexplained {unexcused}")
print("RESULT:", "PASS" if unexcused == 0 else "REVIEW")
sys.exit(0 if (unexcused == 0) else 1)
