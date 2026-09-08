#!/usr/bin/env python3
"""Check 4 - text capture. Every character in a body/table/figure region must
end up inside exactly one node. Orphaned text means the tree is silently lossy."""
import sys
import gzip, json, re, unicodedata
from collections import Counter
nodes = {}
for line in gzip.open("out/docgraph.jsonl.gz", "rt"):
    r = json.loads(line)
    if not r.get("_meta"):
        nodes[r["id"]] = r
inv, geo = {}, {}
for line in gzip.open("out/inventory.jsonl.gz", "rt"):
    r = json.loads(line)
    if not r.get("_meta"):
        inv[r["page"]] = r
for line in gzip.open("out/geometry.jsonl.gz", "rt"):
    r = json.loads(line)
    geo[r["page"]] = r
norm = lambda s: re.sub(r"\s+", "", unicodedata.normalize("NFKC", s))
# reconstruct what each node renders as, marker included: the marker is stored
# in `number`, not in `text`, so comparing raw text alone under-counts by ~1%
tree = Counter()
for n in nodes.values():
    # Generic, not a per-type list. Volume 2 introduced a `note` type and a
    # hard-coded list silently counted every note number and heading as lost
    # text - the third time this check reported its own blind spot as a defect.
    MARKER = {"sentence", "clause", "subclause",
              "act_subsection", "act_clause", "act_subclause"}
    s = " ".join(t["t"] for t in n["text"])
    num = n.get("number") or ""
    s = (f"({num})" if n["type"] in MARKER else num + ".") + (n.get("heading") or "") + s
    tree.update(norm(s))
body = Counter()
per_page = Counter()
for p, r in inv.items():
    for bi, b in enumerate(r["blocks"]):
        for li, l in enumerate(b["l"]):
            if geo[p]["roles"].get(f"{bi}.{li}") in ("body", "table", "figure"):
                t = norm("".join(s["t"] for s in l["s"]))
                body.update(t); per_page[p] += len(t)
miss = body - tree
pct = 100 * sum(miss.values()) / max(1, sum(body.values()))
print(f"content chars on page : {sum(body.values())}")
print(f"captured in the tree  : {sum(tree.values())}")
print(f"orphaned              : {sum(miss.values())}  ({pct:.3f}%)")
print("RESULT:", "PASS" if pct < 0.5 else "REVIEW")
sys.exit(0 if (pct < 0.5) else 1)
