#!/usr/bin/env python3
"""Stage 12 - emit link records for BOTH volumes from the merged model.

A citation whose target sits in the other volume becomes a remote GoTo, so
"See Note A-3.1.2." in Volume 1 opens Volume 2 at that note, and an Appendix A
note citing 9.10.16.1. opens Volume 1 at the article.
"""
import gzip, json, re, sys, time
import pymupdf

SRC = {1: "/mnt/user-data/uploads/301880.pdf", 2: "/mnt/user-data/uploads/301881.pdf"}
FILE = {1: "301880_built_from_model.pdf", 2: "301881_built_from_model.pdf"}
doc = {v: pymupdf.open(p) for v, p in SRC.items()}
nodes = {}
for line in gzip.open("out/docgraph-merged.jsonl.gz", "rt"):
    r = json.loads(line)
    if not r.get("_meta"):
        nodes[r["id"]] = r

def dest(nid):
    n = nodes.get(nid)
    if not n or not n.get("provenance"):
        return None
    pv = n["provenance"][0]
    return n.get("volume", 1), pv["page"], max(40.0, min(760.0, pv["bbox"][1] - 6))

def rect_for(vol, page_no, line_bbox, text):
    if not line_bbox:
        return None
    clip = pymupdf.Rect(line_bbox) + (-2, -2, 2, 2)
    probe = re.sub(r"\s+", " ", text).strip()
    for cand in (probe, probe.rstrip(".,;:"), (probe.split() or [probe])[0]):
        try:
            hits = doc[vol][page_no - 1].search_for(cand, clip=clip)
        except Exception:
            hits = []
        if hits:
            r = hits[0]
            for h in hits[1:]:
                r |= h
            return [round(v, 2) for v in r]
    return None

t0 = time.time()
out = {1: [], 2: []}
stat = {"same": 0, "remote": 0, "no_rect": 0, "term": 0}
for nid, n in nodes.items():
    vol = n.get("volume", 1)
    for r in n.get("refs", []) + [{**t, "kind": "term", "text": t.get("term", ""),
                                   "chunk": t.get("chunk"), "target": t.get("target")}
                                  for t in n.get("terms", [])]:
        tgt = r.get("target")
        if not tgt:
            continue
        d = dest(tgt)
        if not d:
            continue
        tvol, tpage, ty = d
        if r.get("chunk") == "*" or r["kind"] == "term":
            li = r.get("line") if r.get("chunk") == "*" else r.get("chunk")
            if li is None or li >= len(n["text"]):
                stat["no_rect"] += 1
                continue
            tl = n["text"][li]
            rect = rect_for(vol, tl["p"], tl.get("b"), r["text"])
            pg = tl["p"]
        else:
            continue
        if not rect:
            stat["no_rect"] += 1
            continue
        rec = {"page": pg, "rect": rect, "why": r["kind"], "src": nid, "target": tgt}
        if tvol == vol:
            rec.update({"to_page": tpage, "to_y": ty})
            stat["same"] += 1
        else:
            rec.update({"remote": FILE[tvol], "to_page": tpage, "to_y": ty})
            stat["remote"] += 1
        if r["kind"] == "term":
            stat["term"] += 1
        out[vol].append(rec)

for v in (1, 2):
    json.dump(out[v], open(f"out/pdf-links-v{v}.json", "w"))
    print(f"volume {v}: {len(out[v])} link records")
print(stat, f"{time.time()-t0:.0f}s")
