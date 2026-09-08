#!/usr/bin/env python3
"""Stage 8b - rebuild the interactive PDF from the model.

Reads the PRISTINE source and pdf-links.json. The PDF is a build artifact: a
grammar fix in stage 7 propagates here on the next run, with no patching.
"""
import json, os, sys, time
from collections import defaultdict
import pymupdf

# Reproducible Builds: the /Info timestamps are the dominant source of
# nondeterminism in a PDF. Take them from SOURCE_DATE_EPOCH so two builds of the
# same inputs are byte-identical.
import time as _t
_epoch = int(os.environ.get("SOURCE_DATE_EPOCH", "1737072000"))
_stamp = "D:" + _t.strftime("%Y%m%d%H%M%S", _t.gmtime(_epoch)) + "Z"

SRC = sys.argv[1] if len(sys.argv) > 1 else "/mnt/user-data/uploads/301880.pdf"
OUT = sys.argv[2] if len(sys.argv) > 2 else "out/301880_built.pdf"
TINT = (0.87, 0.925, 1.0)
BLUE = (0.10, 0.33, 0.72)

links = json.load(open("out/pdf-links.json"))
doc = pymupdf.open(SRC)
by_page = defaultdict(list)
for l in links:
    by_page[l["page"]].append(l)

t0 = time.time()
added = skipped = removed = 0
# The source's own GoTo links carry its errors (18 wrong TOC targets, 67 off-by-N
# body links) and its 819 dead Launch links point at an internal network share.
# A build FROM the model must clear them, or it inherits every one.
for i in range(doc.page_count):
    page = doc[i]
    for l in list(page.get_links()):
        if l["kind"] in (pymupdf.LINK_GOTO, pymupdf.LINK_LAUNCH, pymupdf.LINK_GOTOR):
            page.delete_link(l)
            removed += 1
# URI links anchored on statute names cannot be derived from visible text, so the
# source's web/mail annotations are kept; the model adds the ones it can see.
for pg, ls in by_page.items():
    page = doc[pg - 1]
    placed = [l["from"] for l in page.get_links()]
    # longest rectangles first so a specific citation wins over a broad one
    ls.sort(key=lambda l: -(l["rect"][2] - l["rect"][0]))
    for l in ls:
        R = pymupdf.Rect(l["rect"])
        if l["why"] != "uri" and any((R & p).get_area() > 0.5 * R.get_area() for p in placed):
            skipped += 1
            continue
        if l["why"] == "uri":
            page.insert_link({"kind": pymupdf.LINK_URI, "uri": l["uri"],
                              "from": R + (-0.5, -0.5, 0.5, 0.5)})
            placed.append(R)
            added += 1
            continue
        if l.get("remote"):
            page.insert_link({"kind": pymupdf.LINK_GOTOR, "file": l["remote"],
                              "page": l["to_page"] - 1,
                              "to": pymupdf.Point(33, l["to_y"]),
                              "from": R + (-0.5, -0.5, 0.5, 0.5)})
            page.draw_rect(R + (-0.5, -0.5, 0.5, 0.5), color=None,
                           fill=(0.83, 0.94, 0.85), overlay=False)
            placed.append(R); added += 1
            continue
        page.insert_link({"kind": pymupdf.LINK_GOTO, "page": l["to_page"] - 1,
                          "to": pymupdf.Point(33, l["to_y"]),
                          "from": R + (-0.5, -0.5, 0.5, 0.5)})
        placed.append(R)
        added += 1
        if l["why"] == "toc":
            page.draw_rect(R + (-2, -0.8, 2, 0.8), color=None, fill=TINT, overlay=False)
        elif l["why"] == "amendment":
            page.draw_rect(R + (-1, -1, 1, 1), color=None, fill=(1.0, 0.93, 0.75),
                           overlay=False)
        elif l["why"] not in ("term",) and pg < 1197:
            page.draw_line((R.x0, R.y1 + 0.55), (R.x1, R.y1 + 0.55),
                           color=BLUE, width=0.5, overlay=True)

# ---- outline and page labels, both generated from the model ----
import gzip
nodes, meta = {}, None
for line in gzip.open("out/docgraph.jsonl.gz", "rt"):
    r = json.loads(line)
    if r.get("_meta"):
        meta = r
    else:
        nodes[r["id"]] = r
DEPTH = {"division": 1, "part": 2, "act": 1, "front_matter": 1, "index": 1,
         "contents": 3, "section": 3, "subsection": 4, "article": 5,
         "act_section": 2, "table": 5}
toc = []
for nid, n in nodes.items():
    if n.get("volume", 1) != 1 or n["type"] not in DEPTH or not n.get("provenance"):
        continue
    label = " ".join(x for x in [(n.get("number") or ""), (n.get("heading") or "")] if x).strip()
    if not label:
        label = n["type"].replace("_", " ").title()
    pv = n["provenance"][0]
    toc.append([DEPTH[n["type"]], label[:110], pv["page"],
                {"kind": 1, "page": pv["page"], "to": pymupdf.Point(33, max(0, pv["bbox"][1] - 6))}])
toc.sort(key=lambda e: (e[2], e[3]["to"].y, e[0]))
fixed, depth = [], 0
for e in toc:
    e[0] = min(e[0], depth + 1)
    depth = e[0]
    fixed.append(e)
doc.set_toc(fixed)

# printed page labels: the footer states them, so read them as content
lab_runs, cur = [], None
sec_re = __import__("re").compile(r"(Division [ABC])\s*[–-]\s*(Part\s*\d+)")
for i in range(doc.page_count):
    foot = doc[i].get_text("dict")
    sec = num = None
    for b in foot["blocks"]:
        if b["type"] != 0:
            continue
        for l in b["lines"]:
            y = l["bbox"][1]
            if not (y > 700 or y < 45):
                continue
            t = "".join(x["text"] for x in l["spans"]).strip()
            m = sec_re.search(t)
            if m:
                sec = f"Div {m.group(1).split()[1]} {m.group(2).replace(' ','').replace('Part','Part ')}, "
            mi = __import__("re").match(r"^I\s*-\s*(\d+)$", t)      # Index: "I - 14"
            mb = __import__("re").search(r"Page\s+(\d+)\s*•\s*BCA|BCA\s*•\s*Page\s+(\d+)", t)
            mr = __import__("re").fullmatch(r"[ivxl]{1,7}", t)        # Preface roman
            if mi:
                sec, num = "Index I - ", int(mi.group(1))
            elif mb:
                sec, num = "BCA Page ", int(mb.group(1) or mb.group(2))
            elif mr and num is None:
                sec, num = "", None
            if num is None and t.isdigit():
                num = int(t)
    key = (sec, num)
    if cur and sec == cur[0] and num is not None and cur[1] is not None and num == cur[1] + 1:
        lab_runs[-1]["_n"] = num
        cur = (sec, num)
        continue
    lab_runs.append({"startpage": i, "style": "D", "prefix": sec or "", 
                     "firstpagenum": num or 1, "_n": num})
    cur = (sec, num)
for r in lab_runs:
    r.pop("_n", None)
try:
    doc.set_page_labels(lab_runs)
except Exception as e:
    print("page labels failed:", e)

doc.set_metadata({**doc.metadata,
    "creationDate": _stamp, "modDate": _stamp,
    "title": "2024 Building Code Compendium — Volume 1 (O. Reg. 163/24)",
    "subject": "Ontario Building Code, Divisions A, B and C, Building Code Act 1992"})
doc.xref_set_key(doc.pdf_catalog(), "PageMode", "/UseOutlines")
doc.save(OUT, garbage=1, deflate=True, use_objstms=1, no_new_id=True,
         encryption=pymupdf.PDF_ENCRYPT_NONE)
import os
print(f"source links cleared {removed} | links added {added} | overlapping skipped {skipped}")
print(f"-> {OUT}  {os.path.getsize(OUT)/1e6:.1f} MB  {time.time()-t0:.0f}s")
