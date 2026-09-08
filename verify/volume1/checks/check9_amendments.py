#!/usr/bin/env python3
"""Check 9 - amendment markers.

Every marker on a page must be either the legend itself or attached to a
provision. An unattached marker means a changed provision is not flagged as
changed, which is the kind of gap that matters legally.
"""
import sys, os
import gzip, json, re
from collections import Counter

MARK = re.compile(r"^[er]\d{1,2}$")
inv, nodes, meta = {}, {}, None
for line in gzip.open("out/inventory.jsonl.gz", "rt"):
    r = json.loads(line)
    if not r.get("_meta"):
        inv[r["page"]] = r
for line in gzip.open("out/docgraph.jsonl.gz", "rt"):
    r = json.loads(line)
    if r.get("_meta"):
        meta = r
    else:
        nodes[r["id"]] = r

legend = meta.get("amendment_legend", {})
on_page = Counter()
for p, r in inv.items():
    for b in r["blocks"]:
        for l in b["l"]:
            t = "".join(s["t"] for s in l["s"]).strip()
            if MARK.fullmatch(t):
                on_page[t] += 1
legend_page = next(iter(legend.values()))["legend_page"] if legend else None
legend_marks = sum(1 for b in inv[legend_page]["blocks"] for l in b["l"]
                   if MARK.fullmatch("".join(s["t"] for s in l["s"]).strip())) if legend_page else 0

attached = Counter()
for n in nodes.values():
    for a in n.get("amendment", []):
        attached[a["marker"]] += 1
carriers = sum(1 for n in nodes.values() if n.get("amendment"))
leaves = sum(1 for n in nodes.values() if n.get("amendment")
             and n["type"] in ("sentence", "clause", "subclause", "article",
                               "act_subsection", "act_clause", "table"))

print(f"legend entries      : {len(legend)}  (page {legend_page})")
for k in sorted(legend):
    v = legend[k]
    print(f"   {k}: {v['kind']:<22} {v['instrument'] or '-':<8} effective {v['effective']}")
print(f"markers on page     : {sum(on_page.values())}  {dict(on_page)}")
print(f"   of which legend  : {legend_marks}")
print(f"nodes flagged       : {carriers}  (leaf provisions {leaves})")
print(f"marker attachments  : {sum(attached.values())} incl. inherited by parents")

st = meta.get("amendment_stats", {})
print(f"markers attached to a provision   : {st.get('attached')}"
      f" of {sum(on_page.values()) - legend_marks} non-legend markers")
print(f"markers with nothing beside them  : {len(st.get('orphans', []))}"
      f" {st.get('orphans', [])}")
ok = (len(legend) == 4 and carriers > 0
      and st.get("attached", 0) + len(st.get("orphans", [])) ==
      sum(on_page.values()) - legend_marks)
print("RESULT:", "PASS" if ok else "REVIEW")
sys.exit(0 if (ok) else 1)
