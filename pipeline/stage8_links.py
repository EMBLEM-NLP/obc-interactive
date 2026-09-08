#!/usr/bin/env python3
"""Stage 8a - emit pdf-links.json from the model.

Every link in the output PDF is derived from a resolved reference in the graph:
source rectangle from the line bbox recorded in stage 3, destination from the
target node's own provenance. Nothing is pattern-matched off the page here.
"""
import gzip, json, re, sys, time
import pymupdf

SRC = sys.argv[1] if len(sys.argv) > 1 else "/mnt/user-data/uploads/301880.pdf"
doc = pymupdf.open(SRC)
nodes, _meta = {}, {}
for line in gzip.open("out/docgraph.jsonl.gz", "rt"):
    r = json.loads(line)
    if r.get("_meta"):
        _meta = r
    else:
        nodes[r["id"]] = r
tab_runs = {}
for line in gzip.open("out/tables.jsonl.gz", "rt"):
    r = json.loads(line)
    if not r.get("_meta"):
        tab_runs.setdefault(r["designator"], []).append(r)

REMOTE_FILE = "301881_built_from_model.pdf"

def dest(nid):
    n = nodes.get(nid)
    if not n or not n.get("provenance"):
        return None
    pv = n["provenance"][0]
    return pv["page"], max(40.0, min(760.0, pv["bbox"][1] - 6))

def is_remote(nid):
    return nodes.get(nid, {}).get("volume", 1) == 2

def rect_for(page_no, line_bbox, text):
    """exact rectangle of `text` inside the line, via a clipped search"""
    if not line_bbox:
        return None
    clip = pymupdf.Rect(line_bbox) + (-2, -2, 2, 2)
    probe = re.sub(r"\s+", " ", text).strip()
    for cand in (probe, probe.rstrip(".,;:"), probe.split()[0] if probe.split() else probe):
        try:
            hits = doc[page_no - 1].search_for(cand, clip=clip)
        except Exception:
            hits = []
        if hits:
            r = hits[0]
            for h in hits[1:]:
                r |= h
            return [round(v, 2) for v in r]
    return None

t0 = time.time()
links = []
stat = {"ref": 0, "term": 0, "toc": 0, "no_rect": 0, "no_dest": 0}

# 1. citations and defined terms
for nid, n in nodes.items():
    if n.get("volume", 1) != 1:
        continue
    for r in n.get("refs", []):
        if not r.get("target"):
            continue
        d = dest(r["target"])
        if not d:
            stat["no_dest"] += 1
            continue
        if r["chunk"] == "*":
            if r.get("line") is None:
                stat["no_rect"] += 1
                continue
            tl = n["text"][r["line"]]
            rect = rect_for(tl["p"], tl.get("b"), r["text"])
            pg = tl["p"]
        else:                                    # a table cell
            gi = int(r["chunk"][1:])
            cell = n["grid"][gi]
            part = next((p for run in tab_runs.get(n["number"], [])
                         for p in run["parts"] if p["page"] == cell["page"]), None)
            box = next((c["box"] for c in part["cells"]
                        if c["r"] == cell["r"] and c["c"] == cell["c"]), None) if part else None
            rect = rect_for(cell["page"], box, r["text"])
            pg = cell["page"]
        if not rect:
            stat["no_rect"] += 1
            continue
        rec = {"page": pg, "rect": rect, "target": r["target"],
               "to_page": d[0], "to_y": d[1], "why": r["kind"], "src": nid}
        if is_remote(r["target"]):
            rec["remote"] = REMOTE_FILE
            stat["remote"] = stat.get("remote", 0) + 1
        links.append(rec)
        stat["ref"] += 1
    for tm in n.get("terms", []):
        d = (tm.get("to_page"), tm.get("to_y")) if tm.get("to_page") else dest(tm["target"])
        if not d or not d[0]:
            continue
        tl = n["text"][tm["chunk"]]
        rect = rect_for(tl["p"], tl.get("b"), tm["term"])
        if not rect:
            stat["no_rect"] += 1
            continue
        links.append({"page": tl["p"], "rect": rect, "target": tm["target"],
                      "to_page": d[0], "to_y": d[1], "why": "term", "src": nid})
        stat["term"] += 1

# printed page labels, read from the footers as content. A contents entry states
# which printed page it points at; that assertion outranks where the detector
# happened to find the heading.
import gzip as _gz
_sec = re.compile(r"(Division [ABC])\s*[–-]\s*(Part\s*\d+)")
printed = {}
for line in _gz.open("out/inventory.jsonl.gz", "rt"):
    r = json.loads(line)
    if r.get("_meta"):
        continue
    sec = num = None
    for b in r["blocks"]:
        for l in b["l"]:
            y = l["b"][1]
            if not (y > 700 or y < 45):
                continue
            tx = "".join(x["t"] for x in l["s"]).strip()
            m = _sec.search(tx)
            if m:
                sec = f"{m.group(1)} - {m.group(2)}".replace("  ", " ")
            if num is None and tx.isdigit():
                num = int(tx)
    if sec and num is not None:
        printed.setdefault((sec, num), r["page"])

# 2. the Building Code Act's own contents pages (they live in the FRONT node)
ACTNUM = re.compile(r"^(\d+(?:\.\d+){0,2})(?:\s|$)")
act_ids = {n["number"]: nid for nid, n in nodes.items() if n["type"] == "act_section"}
act_pages = {n["provenance"][0]["page"] for nid, n in nodes.items()
             if n["type"] == "act_section" and n["provenance"]}
act_lo = min(act_pages) if act_pages else 10 ** 9
front = nodes.get("FRONT")
if front:
    for tl in front["text"]:
        if tl["p"] >= act_lo or not tl.get("b"):
            continue
        m = ACTNUM.match(tl["t"].strip())
        if not m or m.group(1) not in act_ids:
            continue
        d = dest(act_ids[m.group(1)])
        if not d:
            continue
        b = tl["b"]
        links.append({"page": tl["p"], "rect": [b[0] - 2, b[1] - 1, b[2] + 240, b[3] + 1],
                      "target": act_ids[m.group(1)], "to_page": d[0], "to_y": d[1],
                      "why": "toc", "src": "FRONT"})
        stat["toc"] += 1

# 3. web and mail addresses, emitted from the model so the mangled ones are repaired
URL = re.compile(r"(https?://[^\s)\]]+|www\.[^\s)\]]+|[\w.\-]+@[\w.\-]+\.[a-z]{2,})")
uri_links = []
for nid, n in nodes.items():
    for tl in n["text"]:
        if not tl.get("b"):
            continue
        for m in URL.finditer(tl["t"]):
            raw = m.group(1).rstrip(".,;:)\u201d\"'")
            uri = raw if raw.startswith("http") else (
                "mailto:" + raw if "@" in raw else "https://" + raw)
            rect = rect_for(tl["p"], tl["b"], raw)
            if not rect:
                continue
            uri_links.append({"page": tl["p"], "rect": rect, "uri": uri,
                              "why": "uri", "src": nid})
stat["uri"] = len(uri_links)
links += uri_links

# 4. amendment markers -> the legend, so a bare "r2" in the margin is reachable
marks = _meta.get("amendment_marks", [])
leg = _meta.get("amendment_legend", {})
for mk in marks:
    lp = (leg.get(mk["marker"]) or {}).get("legend_page")
    if not lp:
        continue
    b = mk["bbox"]
    links.append({"page": mk["page"],
                  "rect": [b[0] - 1.5, b[1] - 1, b[2] + 1.5, b[3] + 1],
                  "target": "FRONT", "to_page": lp, "to_y": 60.0,
                  "why": "amendment", "src": mk["node"]})
    stat["amendment"] = stat.get("amendment", 0) + 1

# 5. tables of contents - the contents nodes hold the entries verbatim
NUMLINE = re.compile(r"^(\d+(?:\.\d+){1,4}[A-Z]?)\.?(?:\s|$)")
by_num = {}
for nid, n in nodes.items():
    if n["type"] in ("section", "subsection", "article") and n["number"]:
        by_num[(nid.split("/")[0], n["number"])] = nid
for nid, n in nodes.items():
    if n["type"] != "contents":
        continue
    D = nid.split("/")[0]
    # a contents entry is a ROW: number, title with dot leaders, page-number cell.
    # Linking only the number line leaves the page-number cell dead, which is the
    # cell a reader actually aims at.
    rows = {}
    for tl in n["text"]:
        if not tl.get("b"):
            continue
        rows.setdefault((tl["p"], round(tl["b"][1], 1)), []).append(tl)
    # column starts, taken from where numbered entries actually begin. A fixed
    # gutter width fails here: on a two-column contents page the gap between the
    # left column's page-number cell and the right column's entry is ~22pt, the
    # same as the gap between an entry's number and its title.
    colstarts = {}
    for tl in n["text"]:
        if tl.get("b") and NUMLINE.match(tl["t"]):
            colstarts.setdefault(tl["p"], []).append(tl["b"][0])
    for pg in colstarts:
        xs = sorted(colstarts[pg]); cs = [xs[0]]
        for x in xs[1:]:
            if x - cs[-1] > 100:
                cs.append(x)
        colstarts[pg] = cs
    last = []          # [(page, x0, x1, y1, target, dest)] for wrapped titles
    for (pg, y) in sorted(rows):
        row = rows[(pg, y)]
        row.sort(key=lambda t: t["b"][0])
        cs = colstarts.get(pg) or [row[0]["b"][0]]
        buckets = {}
        for t in row:
            c = max([x for x in cs if x <= t["b"][0] + 6] or [cs[0]])
            buckets.setdefault(c, []).append(t)
        segs = [buckets[k] for k in sorted(buckets)]
        for span in segs:
            m = NUMLINE.match(span[0]["t"])
            sx0 = min(t["b"][0] for t in span)
            sx1 = max(t["b"][2] for t in span)
            if not m:
                # a wrapped title line: the page number sits on the continuation,
                # so it belongs to the entry above whose column it overlaps
                cands = [e for e in last if e[0] == pg
                         and e[1] - 8 <= sx1 and sx0 <= e[2] + 8
                         and 0 <= span[0]["b"][1] - e[3] < 14]
                prev = max(cands, key=lambda e: e[3]) if cands else None
                if prev:
                    rect = [span[0]["b"][0] - 2.5, min(t["b"][1] for t in span) - 0.8,
                            max(t["b"][2] for t in span) + 2.5,
                            max(t["b"][3] for t in span) + 0.8]
                    dd = prev[5]
                    cell = next((t["t"] for t in reversed(span) if t["t"].isdigit()), None)
                    sec_of = next((k[0] for k in printed if printed[k] == pg), None)
                    if cell and sec_of and (sec_of, int(cell)) in printed:
                        dd = (printed[(sec_of, int(cell))], 60.0)
                    links.append({"page": pg, "rect": rect, "target": prev[4],
                                  "to_page": dd[0], "to_y": dd[1],
                                  "why": "toc", "src": nid})
                    stat["toc"] += 1
                    last.append((pg, prev[1], prev[2],
                                 max(t["b"][3] for t in span), prev[4], prev[5]))
                continue
            tgt = by_num.get((D, m.group(1)))
            if not tgt:
                continue
            d = dest(tgt)
            if not d:
                continue
            rect = [span[0]["b"][0] - 2.5, min(t["b"][1] for t in span) - 0.8,
                    max(t["b"][2] for t in span) + 2.5, max(t["b"][3] for t in span) + 0.8]
            cell = next((t["t"] for t in reversed(span) if t["t"].isdigit()), None)
            sec_of = next((k[0] for k in printed if printed[k] == pg), None)
            if cell and sec_of and (sec_of, int(cell)) in printed:
                d = (printed[(sec_of, int(cell))], 60.0)
            links.append({"page": pg, "rect": rect, "target": tgt,
                          "to_page": d[0], "to_y": d[1], "why": "toc", "src": nid})
            stat["toc"] += 1
            last.append((pg, sx0, sx1, max(t["b"][3] for t in span), tgt, d))

# the master table of contents (Volume 1) is prose, not numbers
MASTER = {"preface": "FRONT", "building code act": "ACT", "index": "INDEX",
          "building code": "A"}
div_now = None
for tl in (nodes.get("FRONT") or {"text": []})["text"]:
    if not tl.get("b"):
        continue
    t = tl["t"].strip()
    tgt = None
    md = re.match(r"^Division\s+([ABC])\b", t)
    mp = re.match(r"^Part\s+(\d+)\b", t)
    if md:
        div_now = md.group(1)
        tgt = md.group(1) if md.group(1) in nodes else None
    elif mp and div_now and f"{div_now}/{mp.group(1)}" in nodes:
        tgt = f"{div_now}/{mp.group(1)}"
    elif t.lower().rstrip(".") in MASTER and MASTER[t.lower().rstrip(".")] in nodes:
        tgt = MASTER[t.lower().rstrip(".")]
    if not tgt:
        continue
    d = dest(tgt)
    if not d:
        continue
    b = list(tl["b"])
    row = [x for x in nodes["FRONT"]["text"]
           if x.get("b") and x["p"] == tl["p"] and abs(x["b"][1] - b[1]) < 3
           and x["b"][0] >= b[0] - 1]
    if row:
        b = [min(x["b"][0] for x in row), min(x["b"][1] for x in row),
             max(x["b"][2] for x in row), max(x["b"][3] for x in row)]
    links.append({"page": tl["p"], "rect": [b[0] - 2, b[1] - 1, b[2] + 2, b[3] + 1],
                  "target": tgt, "to_page": d[0], "to_y": d[1],
                  "why": "toc", "src": "FRONT"})
    stat["toc"] += 1

json.dump(links, open("out/pdf-links.json", "w"))
print(f"links emitted : {len(links)}   {stat}")
print(f"pages touched : {len({l['page'] for l in links})}   {time.time()-t0:.0f}s")
