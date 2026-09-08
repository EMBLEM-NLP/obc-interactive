#!/usr/bin/env python3
"""Check 1 - two-way region validation.

A caption is only a caption if the line is the designator alone AND it is bound
by a following "Forming Part of ..." line (or is a "(Cont'd)"). Matching a line
that merely starts with "Table 3.2.3.7. shall be met." produced 23 phantom
failures on the first run - the detector was fine, the test was wrong.
"""
import sys
import gzip, json, re
inv, geo = {}, {}
with gzip.open("out/inventory.jsonl.gz", "rt") as fh:
    for line in fh:
        r = json.loads(line)
        if not r.get("_meta"):
            inv[r["page"]] = r
with gzip.open("out/geometry.jsonl.gz", "rt") as fh:
    for line in fh:
        r = json.loads(line)
        geo[r["page"]] = r
CAP = re.compile(r"^(Table|Figure)\s+[A-Z]?-?\d+(?:\.\d+)*\.?(?:-[A-Z0-9/]+)?\s*(\(Cont)?", re.I)
declared = {}
for p, r in inv.items():
    lines = sorted(((l["b"][1], "".join(s["t"] for s in l["s"]).strip())
                    for b in r["blocks"] for l in b["l"]), key=lambda x: x[0])
    lines = [x for x in lines if x[1]]
    for i, (y, t) in enumerate(lines):
        m = CAP.match(t)
        if not m:
            continue
        nxt = " ".join(x[1] for x in lines[i + 1:i + 4])
        if "Forming Part of" in nxt or m.group(2):
            declared.setdefault(p, set()).add(m.group(1).title())
res = {}
for kind, key in (("Table", "tables"), ("Figure", "figures")):
    dec = {p for p, v in declared.items() if kind in v}
    det = {p for p, g in geo.items() if g[key]}
    res[kind] = (dec, det, sorted(dec - det), sorted(det - dec))
    print(f"{kind}: declared {len(dec)} pages | detected {len(det)} pages")
    print(f"   declared but not detected: {len(dec-det)} {sorted(dec-det)[:10]}")
    print(f"   detected but not declared: {len(det-dec)} {sorted(det-dec)[:10]}")
fail = res["Table"][2] or res["Figure"][2]
print("RESULT:", "PASS" if not fail else f"FAIL ({len(fail)} declared regions not detected)")
sys.exit(0 if not fail else 1)
