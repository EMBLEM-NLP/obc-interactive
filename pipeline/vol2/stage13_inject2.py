#!/usr/bin/env python3
"""Stage 13 - build both volumes from the merged model.

Same rules as the Volume 1 injector: clear the source's own GoTo and Launch
annotations first so nothing is inherited, keep URI links, resolve overlaps
longest-first. Cross-volume citations become remote GoTo actions.
"""
import gzip, json, os, os, sys, time
from collections import defaultdict
import pymupdf

# Reproducible Builds: the /Info timestamps are the dominant source of
# nondeterminism in a PDF. Take them from SOURCE_DATE_EPOCH so two builds of the
# same inputs are byte-identical.
import time as _t
_epoch = int(os.environ.get("SOURCE_DATE_EPOCH", "1737072000"))
_stamp = "D:" + _t.strftime("%Y%m%d%H%M%S", _t.gmtime(_epoch)) + "Z"

SRC = {1: "/mnt/user-data/uploads/301880.pdf", 2: "/mnt/user-data/uploads/301881.pdf"}
OUT = {1: "out/301880_built.pdf", 2: "out/301881_built.pdf"}
TINT = (0.87, 0.925, 1.0); BLUE = (0.10, 0.33, 0.72); AMBER = (1.0, 0.93, 0.75)
GREEN = (0.83, 0.94, 0.85)

nodes, meta = {}, None
for line in gzip.open("out/docgraph-merged.jsonl.gz", "rt"):
    r = json.loads(line)
    if r.get("_meta"):
        meta = r
    else:
        nodes[r["id"]] = r

for vol in (2,):
    links = json.load(open(f"out/pdf-links-v{vol}.json"))
    doc = pymupdf.open(SRC[vol])
    removed = 0
    for i in range(doc.page_count):
        page = doc[i]
        for l in list(page.get_links()):
            if l["kind"] in (pymupdf.LINK_GOTO, pymupdf.LINK_LAUNCH, pymupdf.LINK_GOTOR):
                page.delete_link(l); removed += 1
    by_page = defaultdict(list)
    for l in links:
        by_page[l["page"]].append(l)
    added = skipped = remote = 0
    for pg, ls in by_page.items():
        page = doc[pg - 1]
        placed = [l["from"] for l in page.get_links()]
        ls.sort(key=lambda l: -(l["rect"][2] - l["rect"][0]))
        for l in ls:
            R = pymupdf.Rect(l["rect"])
            if any((R & p).get_area() > 0.5 * R.get_area() for p in placed):
                skipped += 1; continue
            if l.get("remote"):
                page.insert_link({"kind": pymupdf.LINK_GOTOR, "file": l["remote"],
                                  "page": l["to_page"] - 1,
                                  "to": pymupdf.Point(33, l["to_y"]),
                                  "from": R + (-0.5, -0.5, 0.5, 0.5)})
                remote += 1
            else:
                page.insert_link({"kind": pymupdf.LINK_GOTO, "page": l["to_page"] - 1,
                                  "to": pymupdf.Point(33, l["to_y"]),
                                  "from": R + (-0.5, -0.5, 0.5, 0.5)})
            placed.append(R); added += 1
            if l["why"] == "toc":
                page.draw_rect(R + (-2, -0.8, 2, 0.8), color=None, fill=TINT, overlay=False)
            elif l["why"] == "amendment":
                page.draw_rect(R + (-1, -1, 1, 1), color=None, fill=AMBER, overlay=False)
            elif l.get("remote"):
                page.draw_rect(R + (-0.5, -0.5, 0.5, 0.5), color=None, fill=GREEN, overlay=False)
            elif l["why"] != "term":
                page.draw_line((R.x0, R.y1 + 0.55), (R.x1, R.y1 + 0.55),
                               color=BLUE, width=0.5, overlay=True)
    # outline from the model
    DEPTH = {"division": 1, "part": 2, "act": 1, "front_matter": 1, "index": 1,
             "appendix": 1, "supplementary_standard": 1, "contents": 3,
             "section": 3, "subsection": 4, "article": 5, "note": 2,
             "act_section": 2, "table": 5}
    toc = []
    for nid, n in nodes.items():
        if n.get("volume", 1) != vol or n["type"] not in DEPTH or not n.get("provenance"):
            continue
        label = " ".join(x for x in [(n.get("number") or ""), (n.get("heading") or "")] if x).strip()
        pv = n["provenance"][0]
        toc.append([DEPTH[n["type"]], (label or n["type"])[:110], pv["page"],
                    {"kind": 1, "page": pv["page"],
                     "to": pymupdf.Point(33, max(0, pv["bbox"][1] - 6))}])
    toc.sort(key=lambda e: (e[2], e[3]["to"].y, e[0]))
    fixed, depth = [], 0
    for e in toc:
        e[0] = min(e[0], depth + 1); depth = e[0]; fixed.append(e)
    doc.set_toc(fixed)
    doc.set_metadata({**doc.metadata,
        "creationDate": _stamp, "modDate": _stamp,
        "title": "2024 Building Code Compendium - Volume 2 (unofficial)"})
    doc.xref_set_key(doc.pdf_catalog(), "PageMode", "/UseOutlines")
    doc.save(OUT[vol], garbage=1, deflate=True, use_objstms=1,
             no_new_id=True, encryption=pymupdf.PDF_ENCRYPT_NONE)
    print(f"volume {vol}: cleared {removed} | added {added} (remote {remote}) | "
          f"skipped {skipped} | bookmarks {len(fixed)} | "
          f"{os.path.getsize(OUT[vol])/1e6:.1f} MB")
