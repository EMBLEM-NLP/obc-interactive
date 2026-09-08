#!/usr/bin/env python3
"""Stage 1 - geometric page classification.

Classifies every text line on every page as header, footer, table, figure or
body, and detects the column layout. Uses geometry and corpus-wide repetition
only. It never reads footer strings to decide what a page is - that assumption
is what caused the Building Code Act (46 pages) to be skipped entirely by the
earlier link passes.
"""
import gzip, json, re, sys, time
from collections import Counter, defaultdict

INV = sys.argv[1] if len(sys.argv) > 1 else "out/inventory.jsonl.gz"
OUT = sys.argv[2] if len(sys.argv) > 2 else "out/geometry.jsonl.gz"

def load(path):
    with gzip.open(path, "rt", encoding="utf-8") as fh:
        for line in fh:
            r = json.loads(line)
            if not r.get("_meta"):
                yield r

def lines_of(pg):
    for bi, b in enumerate(pg["blocks"]):
        for li, l in enumerate(b["l"]):
            yield bi, li, l, "".join(s["t"] for s in l["s"]).strip()

# ---------- pass A: learn the running header / footer bands from repetition ----------
t0 = time.time()
pages = list(load(INV))
H = pages[0]["rect"][3]
key_pages = defaultdict(set)
key_ys = defaultdict(list)
for pg in pages:
    for _, _, l, txt in lines_of(pg):
        if not txt:
            continue
        k = re.sub(r"\d+", "#", txt)
        key_pages[k].add(pg["page"])
        key_ys[k].append(l["b"][1])

N = len(pages)
running = set()
for k, pgs in key_pages.items():
    if len(pgs) < N * 0.05:
        continue
    ys = key_ys[k]
    med = sorted(ys)[len(ys) // 2]
    if med < H * 0.10 or med > H * 0.88:
        running.add(k)

top_edge = max([sorted(key_ys[k])[len(key_ys[k]) // 2] for k in running
                if sorted(key_ys[k])[len(key_ys[k]) // 2] < H * 0.10] or [0])
bot_edge = min([sorted(key_ys[k])[len(key_ys[k]) // 2] for k in running
                if sorted(key_ys[k])[len(key_ys[k]) // 2] > H * 0.88] or [H])
# the logo/letterhead image repeats on nearly every page - page furniture, not a figure
_imgsz = Counter()
for pg in pages:
    for im in pg["images"]:
        _imgsz[(im["w"], im["h"])] += 1
LOGO = _imgsz.most_common(1)[0][0] if _imgsz and _imgsz.most_common(1)[0][1] > N * 0.5 else None
print(f"repeated page-furniture image: {LOGO}")
print(f"learned running-text keys: {len(running)}   header band y<={top_edge+14:.0f}   "
      f"footer band y>={bot_edge-2:.0f}")

# ---------- pass B: per-page regions ----------
def inside(b, box, frac=0.55):
    ix0, iy0 = max(b[0], box[0]), max(b[1], box[1])
    ix1, iy1 = min(b[2], box[2]), min(b[3], box[3])
    if ix1 <= ix0 or iy1 <= iy0:
        return False
    a = (b[2] - b[0]) * (b[3] - b[1]) or 1
    return (ix1 - ix0) * (iy1 - iy0) >= frac * a

def bbox(rs):
    return [min(r[0] for r in rs), min(r[1] for r in rs),
            max(r[2] for r in rs), max(r[3] for r in rs)]

def components(rects, pad=5.0):
    """connected components of rects that touch or nearly touch"""
    n = len(rects)
    parent = list(range(n))
    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]; a = parent[a]
        return a
    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra
    grid = {}
    for i, (x0, y0, x1, y1) in enumerate(rects):
        for gx in range(int(x0 // 50), int(x1 // 50) + 1):
            for gy in range(int(y0 // 50), int(y1 // 50) + 1):
                grid.setdefault((gx, gy), []).append(i)
    for cell in grid.values():
        for a in range(len(cell)):
            for b in range(a + 1, len(cell)):
                i, j = cell[a], cell[b]
                ax0, ay0, ax1, ay1 = rects[i]; bx0, by0, bx1, by1 = rects[j]
                if ax0 - pad <= bx1 and bx0 - pad <= ax1 and ay0 - pad <= by1 and by0 - pad <= ay1:
                    union(i, j)
    groups = {}
    for i in range(n):
        groups.setdefault(find(i), []).append(rects[i])
    return list(groups.values())

def furniture(g, top, bot):
    y0, y1 = g["b"][1], g["b"][3]
    return y1 <= top + 14 or y0 >= bot - 2

def thin(r):
    """(is_thin, is_horizontal) - no length floor: dense span tables use very
    short cell rules, and requiring long segments misclassified them as figures."""
    w, h = r[2] - r[0], r[3] - r[1]
    if h <= 3 and w > h:
        return True, True
    if w <= 3 and h > w:
        return True, False
    return False, None

def classify_component(comp):
    """A table lattice shows up as rules aligned on repeated y levels (rows) and
    repeated x levels (columns). Freeform linework does not align that way."""
    ylev, xlev = set(), set()
    for r in comp:
        t, h = thin(r)
        if not t:
            continue
        if h:
            ylev.add(round((r[1] + r[3]) / 2, 0))
        else:
            xlev.add(round((r[0] + r[2]) / 2, 0))
    bb = bbox(comp)
    w, h = bb[2] - bb[0], bb[3] - bb[1]
    if len(ylev) >= 3 and len(xlev) >= 2 and w > 60 and h > 25:
        return "table", bb
    if len(comp) >= 25 and w > 80 and h > 60:
        return "figure", bb
    return None, bb

stats = Counter()
unassigned = []
with gzip.open(OUT, "wt", encoding="utf-8") as fh:
    for pg in pages:
        p = pg["page"]
        prims = [tuple(g["b"]) for g in pg["draws"] if not furniture(g, top_edge, bot_edge)]
        tables, figures = [], []
        for comp in components(prims, pad=6):
            kind, bb = classify_component(comp)
            if kind == "table":
                tables.append([round(v, 1) for v in bb])
            elif kind == "figure":
                figures.append([round(v, 1) for v in bb])
        for im in pg["images"]:                      # raster figures
            if not im["b"] or (im["w"], im["h"]) == LOGO:
                continue
            if im["b"][3] > top_edge + 14:
                figures.append(im["b"])


        assign = {}
        cols_x = []
        for bi, li, l, txt in lines_of(pg):
            b = l["b"]
            k = re.sub(r"\d+", "#", txt)
            if b[1] <= top_edge + 14 and k in running:
                r = "header"
            elif b[3] >= bot_edge - 2 and k in running:
                r = "footer"
            elif b[1] <= top_edge + 14:
                r = "header"
            elif b[3] >= bot_edge - 2:
                r = "footer"
            elif any(inside(b, t) for t in tables):
                r = "table"
            elif any(inside(b, f) for f in figures):
                r = "figure"
            else:
                r = "body"
                cols_x.append(b[0])
            assign[f"{bi}.{li}"] = r
            stats[r] += 1
            if r is None:
                unassigned.append((p, txt[:40]))
        # column detection from body-line left edges
        cols = []
        for x in sorted(cols_x):
            if cols and x - cols[-1][-1] <= 90:
                cols[-1].append(x)
            else:
                cols.append([x])
        cols = [[round(min(c), 1), round(max(c), 1), len(c)] for c in cols if len(c) >= 3]
        fh.write(json.dumps({"page": p, "roles": assign, "tables": tables,
                             "figures": figures, "columns": cols}) + "\n")

tot = sum(stats.values())
print("line roles:", dict(stats), f"total {tot}")
print("unassigned:", len(unassigned))
print(f"-> {OUT}  {time.time()-t0:.0f}s")
