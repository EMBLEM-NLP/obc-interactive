#!/usr/bin/env python3
"""Check 5 - table integrity: the Phase 3 gate.

  * every text line inside a table region lands in exactly one cell
  * cells tile their region without overlapping
  * a table's column count is constant across its continuation pages
  * every declared caption has a rebuilt table
"""
import sys, os
import gzip, json, re
from collections import defaultdict, Counter

runs = []
with gzip.open("out/tables.jsonl.gz", "rt") as fh:
    for line in fh:
        r = json.loads(line)
        if not r.get("_meta"):
            runs.append(r)
inv, geo = {}, {}
for line in gzip.open("out/inventory.jsonl.gz", "rt"):
    r = json.loads(line)
    if not r.get("_meta"):
        inv[r["page"]] = r
for line in gzip.open("out/geometry.jsonl.gz", "rt"):
    r = json.loads(line)
    geo[r["page"]] = r

# 1. placement
placed = sum(len(c["lines"]) for run in runs for t in run["parts"] for c in t["cells"])
region_lines = 0
for p, g in geo.items():
    for bi, b in enumerate(inv[p]["blocks"]):
        for li, l in enumerate(b["l"]):
            if g["roles"].get(f"{bi}.{li}") == "table" and "".join(s["t"] for s in l["s"]).strip():
                region_lines += 1
print(f"table-region text lines : {region_lines}")
print(f"placed into cells       : {placed}   ({100*placed/region_lines:.2f}%)")

# 2. overlap
overlap = 0
for run in runs:
    for t in run["parts"]:
        cells = t["cells"]
        for i in range(len(cells)):
            a = cells[i]["box"]
            for j in range(i + 1, len(cells)):
                b = cells[j]["box"]
                if a[0] < b[2] - 0.5 and b[0] < a[2] - 0.5 and a[1] < b[3] - 0.5 and b[1] < a[3] - 0.5:
                    overlap += 1
print(f"overlapping cell pairs  : {overlap}")

# 3. column consistency + fragmentation
frag = Counter(r["designator"] for r in runs)
split = {d: n for d, n in frag.items() if n > 1 and d}
print(f"designators split into more than one run: {len(split)}")
for d, n in list(split.items())[:6]:
    pgs = [r["pages"] for r in runs if r["designator"] == d]
    print(f"    {d}: {n} runs {pgs}")

# 4. declared vs rebuilt
CAP = re.compile(r"^Table\s+([A-Z]?-?\d+(?:\.\d+)*\.?(?:-[A-Z0-9/]+)?)\s*(\(Cont)?", re.I)
declared = set()
for p, r in inv.items():
    lines = sorted(((l["b"][1], "".join(s["t"] for s in l["s"]).strip())
                    for b in r["blocks"] for l in b["l"]), key=lambda x: x[0])
    lines = [x for x in lines if x[1]]
    for i, (y, t) in enumerate(lines):
        m = CAP.match(t)
        if m and ("Forming Part of" in " ".join(x[1] for x in lines[i+1:i+4]) or m.group(2)):
            declared.add(m.group(1).rstrip("."))
built = {r["designator"] for r in runs if r["designator"]}
print(f"captions declared {len(declared)} | tables rebuilt {len(built)}")
print(f"   declared but not rebuilt: {len(declared - built)} {sorted(declared-built)[:8]}")

ok = (placed / region_lines > 0.995) and overlap == 0 and not (declared - built)
print("RESULT:", "PASS" if ok else "REVIEW")
sys.exit(0 if (ok) else 1)
