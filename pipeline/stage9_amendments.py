#!/usr/bin/env python3
"""Stage 9 - amendment markers.

The Compendium flags every changed provision with a marker in the left margin
(r1, r2, e1, e2). Page 6 is the legend: each marker sits beside the line naming
the amending regulation or editorial correction and its in-force date. Those
markers carry the legal currency of a provision and were invisible to the model.
"""
import gzip, json, re, time
from collections import Counter

MARK = re.compile(r"^[er]\d{1,2}$")
inv, nodes, order, meta = {}, {}, [], None
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
        order.append(r["id"])

def lines(p):
    return [(l["b"], "".join(s["t"] for s in l["s"]).strip())
            for b in inv[p]["blocks"] for l in b["l"]
            if "".join(s["t"] for s in l["s"]).strip()]

# ---- 1. the legend: the page where markers sit beside dated statements ----
DATE = re.compile(r"(\d{1,2})(?:st|nd|rd|th)?\s+day of\s+(\w+)\s+(\d{4})|"
                  r"(\w+)\s+(\d{1,2})(?:st|nd|rd|th)?,\s*(\d{4})")
REG = re.compile(r"(?:Ontario Regulation|O\. Reg\.)\s+([\d/]+)")
legend = {}
for p in sorted(inv):
    ls = lines(p)
    marks = [(b, t) for b, t in ls if MARK.fullmatch(t) and b[0] < 32]
    if len(marks) < 3:
        continue
    for mb, mt in marks:
        row = [t for b, t in ls if b[0] > 32 and abs(b[1] - mb[1]) < 8]
        if not row:
            continue
        txt = " ".join(row)
        d = DATE.search(txt)
        legend[mt] = {
            "marker": mt,
            "kind": "regulation" if mt.startswith("r") else "editorial correction",
            "instrument": (REG.search(txt).group(1) if REG.search(txt) else None),
            "effective": " ".join(x for x in (d.groups() if d else []) if x) or None,
            "statement": txt[:110],
            "legend_page": p,
        }
    if legend:
        LEGEND_PAGE = p
        break
print("legend:")
for k in sorted(legend):
    v = legend[k]
    print(f"   {k}: {v['kind']:<22} {v['instrument'] or '-':<8} effective {v['effective']}")

# ---- 2. attach each marker to the provision it annotates ----
t0 = time.time()
by_page = {}
for nid, n in nodes.items():
    for t in n["text"]:
        if t.get("b"):
            by_page.setdefault(t["p"], []).append((t["b"], nid))
stat = Counter()
seen_total, orphans, marks_out = [], [], []
for p in sorted(inv):
    if p == LEGEND_PAGE:
        continue
    ls = lines(p)
    for b, t in ls:
        # the marker sits in the margin, and the Compendium flips which margin
        # on facing pages and on two-column pages - so identify it by being the
        # left-most thing on its baseline, not by an absolute x
        if not MARK.fullmatch(t):
            continue
        seen_total.append((p, t))
        if not any(bb[0] > b[2] + 1 and -30 < bb[1] - b[1] < 10 for bb, _ in ls):
            stat["no provision beside the marker"] += 1
            orphans.append((p, t))
            continue
        if t not in legend:
            stat["unknown marker"] += 1
            continue
        # normally the marker shares a baseline with what it annotates; where it
        # flags a whole block (a Part title) it sits just below the first line
        cands = [(abs(bb[1] - b[1]), bb[0], nid) for bb, nid in by_page.get(p, [])
                 if bb[0] > b[2] + 1 and -30 < bb[1] - b[1] < 10]
        if not cands:
            stat["no provision beside the marker"] += 1
            continue
        nid = min(cands)[2]
        n = nodes[nid]
        amd = n.setdefault("amendment", [])
        if not any(a["marker"] == t for a in amd):
            amd.append({k: v for k, v in legend[t].items() if k != "statement"})
        # carry it up to the enclosing provision so a search on the article finds it
        par = n.get("parent")
        while par and nodes.get(par, {}).get("type") in (
                "sentence", "clause", "subclause", "act_subsection",
                "act_clause", "act_subclause"):
            pa = nodes[par].setdefault("amendment", [])
            if not any(a["marker"] == t for a in pa):
                pa.append({k: v for k, v in legend[t].items() if k != "statement"})
            par = nodes[par].get("parent")
        marks_out.append({"page": p, "bbox": [round(v, 1) for v in b],
                          "marker": t, "node": nid})
        stat[f"attached {t}"] += 1

with gzip.open("out/docgraph.jsonl.gz", "wt", encoding="utf-8") as fh:
    fh.write(json.dumps({**meta, "amendment_legend": legend,
                         "amendment_stats": {
                             "markers_on_page": len(seen_total) + len(legend),
                             "legend": len(legend),
                             "attached": len(seen_total) - len(orphans),
                             "orphans": orphans},
                         "amendment_marks": marks_out}) + "\n")
    for nid in order:
        fh.write(json.dumps(nodes[nid], ensure_ascii=False) + "\n")
print()
for k, v in stat.most_common():
    print(f"   {v:>4}  {k}")
print("orphan markers:", orphans)
print(f"nodes carrying an amendment: "
      f"{sum(1 for n in nodes.values() if n.get('amendment'))}   {time.time()-t0:.0f}s")
