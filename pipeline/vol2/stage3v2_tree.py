#!/usr/bin/env python3
"""Stage 3 (Volume 2) - a second container model.

Volume 1's walk is built around Division/Part contents pages. Volume 2 has no
Divisions: it is Appendix A notes plus the Supplementary Standards. The
containers differ; the marker grammar underneath does not, exactly as it did
not for the Building Code Act.

Containers come from the running header, which names the standard the page
belongs to. That is the document stating its own structure, not a guess about
page type - and check12 validates it two ways against the title pages.
"""
import gzip, json, re, time
from collections import Counter

inv, geo, rol = {}, {}, {}
for line in gzip.open("out/inventory.jsonl.gz", "rt"):
    r = json.loads(line)
    if not r.get("_meta"):
        inv[r["page"]] = r
for line in gzip.open("out/geometry.jsonl.gz", "rt"):
    r = json.loads(line)
    geo[r["page"]] = r
for line in gzip.open("out/roles.jsonl.gz", "rt"):
    r = json.loads(line)
    if not r.get("_meta"):
        rol[r["page"]] = r["roles"]
NPAGES = max(inv)

NOTE = re.compile(r"^(A-\d+(?:\.\d+){0,4}\.?(?:\(\d+\))?(?:\([a-z]\))?)\s")
NUM  = re.compile(r"^(\d+(?:\.\d+){1,4}[A-Z]?)\.?(?:\s|$)")
SENT = re.compile(r"^\((\d+(?:\.\d+)?)\)")
CLA  = re.compile(r"^\(([a-z](?:\.\d+)?)\)")
SUB  = re.compile(r"^\(([ivx]+)\)")
ROMAN = ["i","ii","iii","iv","v","vi","vii","viii","ix","x","xi","xii","xiii","xiv",
         "xv","xvi","xvii","xviii","xix","xx","xxi","xxii","xxiii","xxiv","xxv"]
STD = re.compile(r"Supplementary Standard\s+(S[ABC]-\d+)")

def txt_of(l):
    return "".join(s["t"] for s in l["s"]).strip()

def ordered_lines(p):
    pg, g, rr = inv[p], geo[p], rol.get(p, {})
    items = []
    for bi, b in enumerate(pg["blocks"]):
        for li, l in enumerate(b["l"]):
            t = txt_of(l)
            if not t:
                continue
            ital = [sp["t"] for sp in l["s"] if "Italic" in sp["f"] and sp["t"].strip()]
            items.append({"b": l["b"], "t": t, "it": ital,
                          "region": g["roles"].get(f"{bi}.{li}"),
                          "role": rr.get(f"{bi}.{li}"),
                          "font": l["s"][0]["f"], "size": l["s"][0]["sz"]})
    body_x = sorted(i["b"][0] for i in items if i["region"] == "body")
    bands = []
    for x in body_x:
        if bands and x - bands[-1][1] <= 60:
            bands[-1][1] = max(bands[-1][1], x)
        else:
            bands.append([x, x])
    def band_of(i):
        for n, (lo, hi) in enumerate(bands):
            if i["b"][0] <= hi + 60:
                return n
        return len(bands)
    items.sort(key=lambda i: (band_of(i), round(i["b"][1], 1), i["b"][0]))
    return items

# ---- container spans from the running header ----
def header_key(p):
    for b in inv[p]["blocks"]:
        for l in b["l"]:
            if l["b"][1] < 45:
                t = txt_of(l)
                m = STD.search(t)
                if m:
                    return m.group(1)
                if re.search(r"\bA-\d", t):
                    return "APPA"
    return None

spans, cur = [], None
for p in range(1, NPAGES + 1):
    k = header_key(p)
    if k is None and cur:                       # a gap inside a standard
        k = cur
    if spans and spans[-1][0] == k:
        spans[-1][2] = p
    else:
        spans.append([k, p, p])
    cur = k
spans = [s for s in spans if s[0]]
merged = []
for s in spans:
    if merged and merged[-1][0] == s[0] and s[1] - merged[-1][2] <= 3:
        merged[-1][2] = s[2]
    else:
        merged.append(s)
spans = merged
print("containers:")
for k, a, b in spans:
    print(f"   {k:<8} pp {a}-{b}")

nodes, order = {}, []
def add(nid, ntype, number, heading, page, bbox, parent):
    if nid in nodes:
        return nodes[nid]
    n = {"id": nid, "type": ntype, "number": number, "heading": heading,
         "parent": parent, "children": [], "text": [],
         "provenance": ([{"page": page, "bbox": [round(v, 1) for v in bbox]}] if bbox else [])}
    nodes[nid] = n
    order.append(nid)
    if parent and parent in nodes:
        nodes[parent]["children"].append(nid)
    return n

def push(host, it, p):
    nodes[host]["text"].append({"p": p, "t": it["t"],
                                "b": [round(v, 1) for v in it["b"]],
                                **({"it": it["it"]} if it["it"] else {})})

t0 = time.time()
covered = set()
for key, lo, hi in spans:
    root = "APPA" if key == "APPA" else key
    add(root, "appendix" if key == "APPA" else "supplementary_standard",
        None if key == "APPA" else key,
        "Appendix A — Explanatory Material" if key == "APPA" else
        f"MMAH Supplementary Standard {key}", lo, [0, 60, 10, 70], None)
    cur_top = cur_sent = cur_cl = cur_sc = None
    nxt = {"s": 1, "c": 1, "sc": 1}
    cl_x = None
    for p in range(lo, hi + 1):
        covered.add(p)
        for it in ordered_lines(p):
            if it["region"] in ("header", "footer"):
                continue
            t, bb = it["t"], it["b"]
            black = "Black" in it["font"]
            if key == "APPA":
                m = NOTE.match(t)
                if m and black:
                    nid = f"APPA/{m.group(1).rstrip('.')}"
                    add(nid, "note", m.group(1).rstrip("."),
                        t[m.end():].strip(" .") or None, p, bb, root)
                    cur_top, cur_sent, cur_cl, cur_sc = nid, None, None, None
                    nxt = {"s": 1, "c": 1, "sc": 1}; cl_x = None
                    continue
            else:
                m = NUM.match(t)
                if m and black:
                    num = m.group(1)
                    depth = num.count(".") + 1
                    nid = f"{root}/{num}"
                    add(nid, {2: "section", 3: "subsection"}.get(depth, "article"),
                        num, t[m.end():].strip(" .") or None, p, bb, root)
                    cur_top, cur_sent, cur_cl, cur_sc = nid, None, None, None
                    nxt = {"s": 1, "c": 1, "sc": 1}; cl_x = None
                    continue
            if not cur_top:
                push(root, it, p); continue
            ms, mc, msc = SENT.match(t), CLA.match(t), SUB.match(t)
            if ms and it["region"] == "body":
                n2 = ms.group(1)
                if "." in n2 or int(n2) == nxt["s"]:
                    nid = f"{cur_top}/({n2})"
                    add(nid, "sentence", n2, None, p, bb, cur_top)
                    nodes[nid]["text"].append({"p": p, "t": t[ms.end():].strip(),
                                               "b": [round(v, 1) for v in bb],
                                               **({"it": it["it"]} if it["it"] else {})})
                    cur_sent, cur_cl, cur_sc = nid, None, None
                    if "." not in n2:
                        nxt["s"] = int(n2) + 1
                    nxt["c"] = nxt["sc"] = 1; cl_x = None
                    continue
            if (mc or msc) and it["region"] == "body":
                want_c = chr(96 + nxt["c"])
                want_s = ROMAN[nxt["sc"] - 1] if nxt["sc"] <= len(ROMAN) else None
                deeper = cl_x is not None and bb[0] > cl_x + 12
                as_sub = bool(msc) and msc.group(1) == want_s
                as_cl = bool(mc) and mc.group(1) == want_c
                if as_sub and cur_cl and not (as_cl and not deeper):
                    nid = f"{cur_cl}/({msc.group(1)})"
                    add(nid, "subclause", msc.group(1), None, p, bb, cur_cl)
                    nodes[nid]["text"].append({"p": p, "t": t[msc.end():].strip(),
                                               "b": [round(v, 1) for v in bb]})
                    cur_sc = nid; nxt["sc"] += 1
                    continue
                if as_cl and cur_sent:
                    nid = f"{cur_sent}/({mc.group(1)})"
                    add(nid, "clause", mc.group(1), None, p, bb, cur_sent)
                    nodes[nid]["text"].append({"p": p, "t": t[mc.end():].strip(),
                                               "b": [round(v, 1) for v in bb]})
                    cur_cl, cur_sc = nid, None
                    if cl_x is None:
                        cl_x = bb[0]
                    nxt["c"] = ord(mc.group(1)) - 96 + 1; nxt["sc"] = 1
                    continue
            push(cur_sc or cur_cl or cur_sent or cur_top, it, p)

# anything outside a container: front matter and the Forms section
add("V2FRONT", "front_matter", None, "Volume 2 front matter and Forms",
    1, [0, 60, 10, 70], None)
for p in range(1, NPAGES + 1):
    if p in covered:
        continue
    for it in ordered_lines(p):
        if it["region"] in ("header", "footer"):
            continue
        push("V2FRONT", it, p)

with gzip.open("out/docgraph.jsonl.gz", "wt", encoding="utf-8") as fh:
    fh.write(json.dumps({"_meta": True, "volume": 2, "nodes": len(nodes),
                         "containers": [{"key": k, "lo": a, "hi": b} for k, a, b in spans]}) + "\n")
    for nid in order:
        fh.write(json.dumps(nodes[nid], ensure_ascii=False) + "\n")
print("\nnodes:", dict(Counter(n["type"] for n in nodes.values()).most_common()),
      "total", len(nodes), f"{time.time()-t0:.0f}s")
