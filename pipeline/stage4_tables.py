#!/usr/bin/env python3
"""Stage 4 - table lattice reconstruction.

Rebuilds each table as a real cell grid from the ruling lines isolated in
stage 1: row and column boundaries are clustered from the rules, minimal cells
are merged into spans wherever an interior rule is absent, and text lines are
assigned to cells by containment. Continuations are stitched by caption and
identical column geometry.
"""
import gzip, json, re, sys, time
from collections import defaultdict, Counter

TOL_ALIGN = 2.5      # rules within this distance are the same boundary
TOL_COVER = 3.0      # a rule may fall short of a cell edge by this much

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

CAP = re.compile(r"^(Table|Figure)\s+([A-Z]?-?\d+(?:\.\d+)*\.?(?:-[A-Z0-9/]+)?)\s*(\(Cont)?", re.I)

def cluster(vals, tol=TOL_ALIGN):
    out = []
    for v in sorted(vals):
        if out and v - out[-1][-1] <= tol:
            out[-1].append(v)
        else:
            out.append([v])
    return [sum(g) / len(g) for g in out]

def in_box(b, box, pad=2.0):
    cx, cy = (b[0] + b[2]) / 2, (b[1] + b[3]) / 2
    return box[0] - pad <= cx <= box[2] + pad and box[1] - pad <= cy <= box[3] + pad

def build(page, box):
    """-> (rows, cols, cells) for one table region"""
    hseg, vseg = [], []
    for g in inv[page]["draws"]:
        x0, y0, x1, y1 = g["b"]
        if not (x0 >= box[0] - 4 and x1 <= box[2] + 4 and y0 >= box[1] - 4 and y1 <= box[3] + 4):
            continue
        w, h = x1 - x0, y1 - y0
        if h <= 3 and w > h:
            hseg.append((x0, x1, (y0 + y1) / 2))
        elif w <= 3 and h > w:
            vseg.append((y0, y1, (x0 + x1) / 2))
    if len(hseg) < 2 or len(vseg) < 2:
        return None
    rows = cluster([s[2] for s in hseg])
    cols = cluster([s[2] for s in vseg])
    if len(rows) < 2 or len(cols) < 2:
        return None

    def has_h(y, x0, x1):
        for a, b, yc in hseg:
            if abs(yc - y) <= TOL_ALIGN and a <= x0 + TOL_COVER and b >= x1 - TOL_COVER:
                return True
        return False

    def has_v(x, y0, y1):
        for a, b, xc in vseg:
            if abs(xc - x) <= TOL_ALIGN and a <= y0 + TOL_COVER and b >= y1 - TOL_COVER:
                return True
        return False

    R, C = len(rows) - 1, len(cols) - 1
    taken = [[False] * C for _ in range(R)]
    cells = []
    for r in range(R):
        for c in range(C):
            if taken[r][c]:
                continue
            cs = 1
            while c + cs < C and not has_v(cols[c + cs], rows[r], rows[r + 1]):
                cs += 1
            rs = 1
            while r + rs < R and all(not has_h(rows[r + rs], cols[c + k], cols[c + k + 1])
                                     for k in range(cs)):
                rs += 1
            for dr in range(rs):
                for dc in range(cs):
                    taken[r + dr][c + dc] = True
            cells.append({"r": r, "c": c, "rowspan": rs, "colspan": cs,
                          "box": [round(cols[c], 1), round(rows[r], 1),
                                  round(cols[c + cs], 1), round(rows[r + rs], 1)],
                          "lines": []})
    return rows, cols, cells

t0 = time.time()
tables = []
unassigned_total = assigned_total = 0
for p in sorted(geo):
    regions = geo[p]["tables"]
    if not regions:
        continue
    # caption(s) on this page, in reading order
    caps = []
    for b in inv[p]["blocks"]:
        for l in b["l"]:
            t = "".join(s["t"] for s in l["s"]).strip()
            m = CAP.match(t)
            if m and m.group(1).lower() == "table":
                caps.append((l["b"][1], m.group(2).rstrip("."), bool(m.group(3))))
    caps.sort()
    # table-region text lines
    reg_lines = []
    for bi, b in enumerate(inv[p]["blocks"]):
        for li, l in enumerate(b["l"]):
            if geo[p]["roles"].get(f"{bi}.{li}") != "table":
                continue
            t = "".join(s["t"] for s in l["s"]).strip()
            if t:
                reg_lines.append((l["b"], t))
    for ri, box in enumerate(regions):
        built = build(p, box)
        if not built:
            continue
        rows, cols, cells = built
        mine = [(b, t) for b, t in reg_lines if in_box(b, box)]
        for b, t in mine:
            hit = None
            for cell in cells:
                if in_box(b, cell["box"]):
                    hit = cell
                    break
            if hit is None:
                unassigned_total += 1
            else:
                hit["lines"].append({"b": [round(v, 1) for v in b], "t": t})
                assigned_total += 1
        above = [c for c in caps if c[0] < box[1] + 6]
        cap = above[-1] if above else (caps[0] if caps else None)
        tables.append({"page": p, "region": ri,
                       "designator": cap[1] if cap else None,
                       "continuation": cap[2] if cap else False,
                       "box": box, "nrows": len(rows) - 1, "ncols": len(cols) - 1,
                       "col_edges": [round(c, 1) for c in cols],
                       "cells": cells})

# stitch continuations: same designator, consecutive pages, same column geometry
groups = defaultdict(list)
for t in tables:
    groups[t["designator"]].append(t)
stitched = []
for des, ts in groups.items():
    ts.sort(key=lambda t: (t["page"], t["region"]))
    run = []
    for t in ts:
        if run and t["page"] - run[-1]["page"] <= 1 and t["ncols"] == run[-1]["ncols"]:
            run.append(t)
        else:
            if run:
                stitched.append(run)
            run = [t]
    if run:
        stitched.append(run)

with gzip.open("out/tables.jsonl.gz", "wt", encoding="utf-8") as fh:
    fh.write(json.dumps({"_meta": True, "regions": len(tables),
                         "stitched": len(stitched)}) + "\n")
    for run in stitched:
        fh.write(json.dumps({
            "designator": run[0]["designator"],
            "pages": [t["page"] for t in run],
            "ncols": run[0]["ncols"],
            "nrows": sum(t["nrows"] for t in run),
            "parts": run,
        }, ensure_ascii=False) + "\n")

cells = sum(len(t["cells"]) for t in tables)
spans = sum(1 for t in tables for c in t["cells"] if c["rowspan"] > 1 or c["colspan"] > 1)
print(f"table regions rebuilt : {len(tables)}")
print(f"logical tables        : {len(stitched)}")
print(f"cells                 : {cells}  (merged spans {spans})")
print(f"text lines placed     : {assigned_total}   unassigned {unassigned_total}")
print(f"-> out/tables.jsonl.gz  {time.time()-t0:.0f}s")
