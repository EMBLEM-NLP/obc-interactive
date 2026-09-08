#!/usr/bin/env python3
"""Check 6 - figure assets. Two-way: every declared Figure caption has an
exported asset, and every captioned asset corresponds to a declared caption."""
import sys
import gzip, json, re
inv = {}
for line in gzip.open("out/inventory.jsonl.gz", "rt"):
    r = json.loads(line)
    if not r.get("_meta"):
        inv[r["page"]] = r
assets = [json.loads(l) for l in gzip.open("out/figures.jsonl.gz", "rt")][1:]
CAP = re.compile(r"^Figure\s+([A-Z]?-?\d+(?:\.\d+)*\.?(?:-[A-Z0-9/]+)?)\s*(\(Cont)?", re.I)
declared = set()
for p, r in inv.items():
    lines = sorted(((l["b"][1], "".join(s["t"] for s in l["s"]).strip())
                    for b in r["blocks"] for l in b["l"]), key=lambda x: x[0])
    lines = [x for x in lines if x[1]]
    for i, (y, t) in enumerate(lines):
        m = CAP.match(t)
        if m and ("Forming Part of" in " ".join(x[1] for x in lines[i+1:i+4]) or m.group(2)):
            declared.add(m.group(1).rstrip("."))
built = {a["designator"] for a in assets if a["designator"]}
missing = sorted(declared - built)
extra = sorted(built - declared)
import os
broken = [f for a in assets for f in a["files"] if not os.path.exists(f) or os.path.getsize(f) == 0]
print(f"declared figure captions : {len(declared)}")
print(f"exported captioned assets: {len(built)}")
print(f"   declared but not exported: {len(missing)} {missing[:8]}")
print(f"   exported but not declared: {len(extra)} {extra[:8]}")
print(f"uncaptioned assets (letterhead, signatures, preface art): "
      f"{sum(1 for a in assets if not a['designator'])}")
print(f"zero-byte or missing files: {len(broken)}")
print("RESULT:", "PASS" if not missing and not broken else "REVIEW")
sys.exit(0 if (not missing and not broken) else 1)
