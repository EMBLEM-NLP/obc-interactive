#!/usr/bin/env python3
"""Stage 10 - merge the two volumes into one model.

The id scheme already namespaces by container, so Volume 2's nodes join without
collision: APPA/A-3.1.2., SB-3/2.1., SA-1/... alongside B/9/9.10.16.1.
"""
import gzip, json
V1 = "/home/claude/obc/out/docgraph-v1only.jsonl.gz"
V2 = "out/docgraph-vol2only.jsonl.gz"   # explicit: out/docgraph.jsonl.gz
# is overwritten with the merged graph downstream, so reading it here made
# a rerun merge the merge into itself and collide on id "A"
OUT = "out/docgraph-merged.jsonl.gz"
meta = {}
nodes, order = {}, []
for path, vol in ((V1, 1), (V2, 2)):
    for line in gzip.open(path, "rt"):
        r = json.loads(line)
        if r.get("_meta"):
            meta[f"volume{vol}"] = {k: v for k, v in r.items() if k != "_meta"}
            # hoist the keys downstream checks read from the top level. Without
            # this the merge silently drops the amendment legend and the Volume 2
            # container list, and two gates that had passed go quietly unmet.
            for k in ("amendment_legend", "amendment_stats", "containers", "parts"):
                if k in r:
                    meta.setdefault(k, r[k])
            continue
        if r["id"] in nodes:
            raise SystemExit(f"id collision across volumes: {r['id']}")
        r["volume"] = vol
        nodes[r["id"]] = r
        order.append(r["id"])
with gzip.open(OUT, "wt", encoding="utf-8") as fh:
    fh.write(json.dumps({"_meta": True, "merged": True, "nodes": len(nodes), **meta}) + "\n")
    for nid in order:
        fh.write(json.dumps(nodes[nid], ensure_ascii=False) + "\n")
from collections import Counter
print("merged nodes:", len(nodes))
print("by volume   :", dict(Counter(n["volume"] for n in nodes.values())))
print("->", OUT)
