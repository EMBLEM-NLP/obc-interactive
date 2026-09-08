#!/usr/bin/env python3
"""Check 14 - cross-volume resolution.

Volume 1 carried 1,054 citations whose targets were not in the file. After the
merge they must point at real Volume 2 nodes, and those targets must be of the
right kind - a Note citation must land on a note, a Supplementary Standard
citation on that standard.
"""
import sys, gzip, json
from collections import Counter
nodes = {}
for line in gzip.open("out/docgraph-merged.jsonl.gz", "rt"):
    r = json.loads(line)
    if not r.get("_meta"):
        nodes[r["id"]] = r
stat = Counter()
mistyped = []
for n in nodes.values():
    if n.get("volume") != 1:
        continue
    for r in n.get("refs", []):
        if r["kind"] not in ("note", "supp", "form"):
            continue
        stat[f"{r['kind']} total"] += 1
        t = r.get("target")
        if not t:
            stat[f"{r['kind']} unresolved"] += 1
            continue
        if t not in nodes:
            mistyped.append((r["kind"], t, "target missing")); continue
        want = {"note": "note", "supp": "supplementary_standard"}.get(r["kind"])
        if want and nodes[t]["type"] != want:
            mistyped.append((r["kind"], t, nodes[t]["type"]))
        elif nodes[t].get("volume") != 2:
            mistyped.append((r["kind"], t, "not in volume 2"))
        else:
            stat[f"{r['kind']} resolved into volume 2"] += 1
for k, v in sorted(stat.items()):
    print(f"   {v:>5}  {k}")
print(f"targets of the wrong kind or volume: {len(mistyped)} {mistyped[:4]}")
res = stat["note resolved into volume 2"] + stat["supp resolved into volume 2"]
tot = stat["note total"] + stat["supp total"]
print(f"note + supplementary citations resolved: {res} of {tot} ({100*res/max(1,tot):.1f}%)")
fails = []
if mistyped: fails.append(f"{len(mistyped)} mistyped targets")
if res / max(1, tot) < 0.95: fails.append(f"resolution {100*res/max(1,tot):.1f}% below 95%")
print("RESULT:", "PASS" if not fails else f"FAIL {fails}")
sys.exit(0 if not fails else 1)
