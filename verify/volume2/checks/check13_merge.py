#!/usr/bin/env python3
"""Check 13 - the merged model.

Both volumes must be present, ids must not collide, and every node must still
reach a root. A merge that silently drops or overwrites is worse than no merge.
"""
import sys, os, gzip, json
from collections import Counter
nodes, meta = {}, None
for line in gzip.open("out/docgraph-merged.jsonl.gz", "rt"):
    r = json.loads(line)
    if r.get("_meta"):
        meta = r
    else:
        if r["id"] in nodes:
            print("RESULT: FAIL duplicate id", r["id"]); sys.exit(1)
        nodes[r["id"]] = r
v = Counter(n.get("volume") for n in nodes.values())
orphan = [n["id"] for n in nodes.values()
          if n.get("parent") and n["parent"] not in nodes]
roots = [n["id"] for n in nodes.values() if not n.get("parent")]
print(f"merged nodes     : {len(nodes)}")
print(f"   volume 1      : {v[1]}")
print(f"   volume 2      : {v[2]}")
print(f"roots            : {len(roots)}  {sorted(roots)[:12]}")
print(f"nodes with a missing parent: {len(orphan)} {orphan[:5]}")
fails = []
if v[1] < 20000: fails.append("volume 1 nodes missing")
if v[2] < 1000: fails.append("volume 2 nodes missing")
if orphan: fails.append(f"{len(orphan)} nodes lost their parent")
print("RESULT:", "PASS" if not fails else f"FAIL {fails}")
sys.exit(0 if not fails else 1)
