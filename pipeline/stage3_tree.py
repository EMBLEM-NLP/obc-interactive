#!/usr/bin/env python3
"""Stage 3 - tree assembly.

Walks pages in reading order and builds a node tree with stable, namespaced IDs.
Division and Part come from the title text on each contents page, never from
page footers. Column order is derived from body-line clustering so two-column
pages (the whole Building Code Act) read correctly.
"""
import gzip, json, re, sys, time
from collections import Counter, defaultdict

inv, geo, rol = {}, {}, {}
with gzip.open("out/inventory.jsonl.gz", "rt") as fh:
    for line in fh:
        r = json.loads(line)
        if not r.get("_meta"):
            inv[r["page"]] = r
with gzip.open("out/geometry.jsonl.gz", "rt") as fh:
    for line in fh:
        r = json.loads(line)
        geo[r["page"]] = r
meta = None
with gzip.open("out/roles.jsonl.gz", "rt") as fh:
    for line in fh:
        r = json.loads(line)
        if r.get("_meta"):
            meta = r
        else:
            rol[r["page"]] = r["roles"]
CONTENTS = set(meta["contents_pages"])
NPAGES = max(inv)

NUM   = re.compile(r"^(\d+(?:\.\d+){1,4}[A-Z]?)\.?(?:\s|$)")
SECT  = re.compile(r"^Section\s+(\d+(?:\.\d+){1,2})\.?(?:\s|$)")
SENT  = re.compile(r"^\((\d+(?:\.\d+)?)\)")
CLA   = re.compile(r"^\(([a-z](?:\.\d+)?)\)")
SUB   = re.compile(r"^\(([ivx]+)\)")
ROMAN = ["i","ii","iii","iv","v","vi","vii","viii","ix","x","xi","xii","xiii",
         "xiv","xv","xvi","xvii","xviii","xix","xx","xxi","xxii","xxiii",
         "xxiv","xxv","xxvi","xxvii","xxviii","xxix","xxx"]
ACTS  = re.compile(r"^(\d+(?:\.\d+){0,2})(?:\((\d+(?:\.\d+)?)\))?\s")
DIVW  = re.compile(r"^Division\s+([ABC])\b")
PARTW = re.compile(r"^Part\s+(\d+)\b")

def txt_of(l):
    return "".join(s["t"] for s in l["s"]).strip()

def ordered_lines(p):
    """lines in reading order: column band, then y, then x"""
    pg, g, rr = inv[p], geo[p], rol.get(p, {})
    items = []
    for bi, b in enumerate(pg["blocks"]):
        for li, l in enumerate(b["l"]):
            t = txt_of(l)
            if not t:
                continue
            ital = [sp["t"] for sp in l["s"] if "Italic" in sp["f"] and sp["t"].strip()]
            items.append({"key": f"{bi}.{li}", "b": l["b"], "t": t, "it": ital,
                          "region": g["roles"].get(f"{bi}.{li}"),
                          "role": rr.get(f"{bi}.{li}"),
                          "font": l["s"][0]["f"], "size": l["s"][0]["sz"],
                          "spans": l["s"]})
    body_x = sorted(i["b"][0] for i in items if i["region"] == "body")
    bands = []
    for x in body_x:
        if bands and x - bands[-1][1] <= 60:
            bands[-1][1] = max(bands[-1][1], x)
        else:
            bands.append([x, x])
    bands = [b for b in bands if b[1] - b[0] >= 0]
    def band_of(i):
        x = i["b"][0]
        for n, (lo, hi) in enumerate(bands):
            if x <= hi + 60:
                return n
        return len(bands)
    items.sort(key=lambda i: (band_of(i), round(i["b"][1], 1), i["b"][0]))
    return items

# ---- containers: one per contents block, plus the Act and the front matter ----
blocks = []
for p in sorted(CONTENTS):
    if blocks and p == blocks[-1][-1] + 1:
        blocks[-1].append(p)
    else:
        blocks.append([p])
parts = []
division = None
for i, blk in enumerate(blocks):
    end = blocks[i + 1][0] - 1 if i + 1 < len(blocks) else NPAGES
    part = None
    for it in ordered_lines(blk[0]):
        m = DIVW.match(it["t"])
        if m:
            division = m.group(1)
        m = PARTW.match(it["t"])
        if m and part is None:
            part = int(m.group(1))
    parts.append({"division": division, "part": part,
                  "contents": blk, "lo": blk[0], "hi": end})

# the Index is the trailing run of pages carrying no structural heading at all
HEADR = {"section", "subsection", "article", "act_section"}
INDEX_LO = None
p = NPAGES
while p > 1 and not any(r in HEADR for r in rol.get(p, {}).values()):
    INDEX_LO = p
    p -= 1
if INDEX_LO and NPAGES - INDEX_LO < 10:      # a couple of blank pages is not an index
    INDEX_LO = None
if INDEX_LO:
    parts[-1]["hi"] = INDEX_LO - 1

first_contents = blocks[0][0]
ACT_LO, ACT_HI = None, None
for p in range(1, first_contents):
    for it in ordered_lines(p):
        if it["role"] == "act_section":
            ACT_LO = ACT_LO or p
            ACT_HI = p

print("parts detected:")
for pt in parts:
    print(f"   Division {pt['division']} Part {pt['part']:<3} pages {pt['lo']}-{pt['hi']}"
          f"  contents {pt['contents']}")
print(f"Building Code Act body pages: {ACT_LO}-{ACT_HI}")
print(f"Index pages: {INDEX_LO}-{NPAGES}" if INDEX_LO else "Index: not found")

# ---- node tree ----
nodes = {}
order = []

def add(nid, ntype, number, heading, page, bbox, parent):
    if nid in nodes:
        return nodes[nid]
    n = {"id": nid, "type": ntype, "number": number, "heading": heading,
         "parent": parent, "children": [], "text": [], "provenance": []}
    if bbox:
        n["provenance"].append({"page": page, "bbox": [round(v, 1) for v in bbox]})
    nodes[nid] = n
    order.append(nid)
    if parent and parent in nodes:
        nodes[parent]["children"].append(nid)
    return n

t0 = time.time()
for pt in parts:
    D, P = pt["division"], pt["part"]
    if D is None or P is None:
        continue
    root = f"{D}"
    add(root, "division", D, None, pt["lo"], [0, 60, 10, 70], None)
    pid = f"{D}/{P}"
    add(pid, "part", str(P), None, pt["lo"], [0, 60, 10, 70], root)
    cur = {"section": None, "subsection": None, "article": None,
           "sentence": None, "clause": None, "subclause": None}
    clause_x = None            # indent of the current clause list
    nxt = {"sentence": 1, "clause": 1, "subclause": 1}
    cid = f"{pid}/contents"
    add(cid, "contents", None, f"Contents, Division {D} Part {P}",
        pt["contents"][0], None, pid)
    for p in pt["contents"]:
        for it in ordered_lines(p):
            if it["region"] in ("header", "footer"):
                continue
            nodes[cid]["text"].append({"p": p, "t": it["t"], "b": [round(v,1) for v in it["b"]], **({"it": it["it"]} if it["it"] else {})})
    for p in range(pt["lo"], pt["hi"] + 1):
        if p in pt["contents"]:
            continue
        for it in ordered_lines(p):
            role, t, bb = it["role"], it["t"], it["b"]
            if it["region"] in ("header", "footer"):
                continue
            if it["region"] in ("table", "figure"):
                host = (cur["article"] or cur["subsection"] or cur["section"] or pid)
                nodes[host]["text"].append({"p": p, "t": t, "region": it["region"], "b": [round(v,1) for v in bb], **({"it": it["it"]} if it["it"] else {})})
                continue
            if role == "section":
                nxt["sentence"] = nxt["clause"] = nxt["subclause"] = 1
                m = SECT.match(t) or NUM.match(t)
                if m:
                    num = m.group(1)
                    nid = f"{pid}/{num}"
                    add(nid, "section", num, t[m.end():].strip(" .") or None, p, bb, pid)
                    cur.update(section=nid, subsection=None, article=None,
                               sentence=None, clause=None, subclause=None)
                continue
            if role in ("subsection", "article"):
                m = NUM.match(t)
                if not m:
                    continue
                num = m.group(1)
                # a heading whose number does not belong to this Part is a
                # mis-detection (a table cell or a marginal reference)
                if num.split(".")[0] != str(P):
                    nodes[cur["article"] or cur["subsection"] or cur["section"] or pid]["text"].append({"p": p, "t": t, "b": [round(v,1) for v in bb]})
                    continue
                sec = ".".join(num.split(".")[:2]).rstrip("ABCDEFGH")
                parent = cur["section"] or add(f"{pid}/{sec}", "section", sec, None, p, None, pid)["id"]
                if role == "subsection":
                    nid = f"{pid}/{num}"
                    add(nid, "subsection", num, t[m.end():].strip(" .") or None, p, bb, parent)
                    cur.update(subsection=nid, article=None, sentence=None,
                               clause=None, subclause=None)
                else:
                    subn = ".".join(num.split(".")[:3]).rstrip("ABCDEFGH")
                    par = cur["subsection"] or add(f"{pid}/{subn}", "subsection", subn,
                                                   None, p, None, parent)["id"]
                    nid = f"{pid}/{num}"
                    add(nid, "article", num, t[m.end():].strip(" .") or None, p, bb, par)
                    cur.update(article=nid, sentence=None, clause=None, subclause=None)
                    nxt["sentence"] = nxt["clause"] = nxt["subclause"] = 1
                    clause_x = None
                continue
            host = (cur["subclause"] or cur["clause"] or cur["sentence"] or
                    cur["article"] or cur["subsection"] or cur["section"] or pid)
            if role == "sentence" and cur["article"]:
                m = SENT.match(t)
                num = m.group(1)
                # "(4), (5) or (7) are met." is a wrapped line, not a new sentence.
                # A real marker is the next in sequence, or a decimal insertion.
                if "." not in num and int(num) != nxt["sentence"]:
                    nodes[cur["sentence"] or cur["article"]]["text"].append({"p": p, "t": t, "b": [round(v,1) for v in bb]})
                    continue
                nid = f"{cur['article']}/({num})"
                add(nid, "sentence", num, None, p, bb, cur["article"])
                nodes[nid]["text"].append({"p": p, "t": t[m.end():].strip(), "b": [round(v,1) for v in bb], **({"it": it["it"]} if it["it"] else {})})
                cur.update(sentence=nid, clause=None, subclause=None)
                clause_x = None
                if "." not in num:
                    nxt["sentence"] = int(num) + 1
                nxt["clause"] = nxt["subclause"] = 1
                continue
            # "(i)" is both a clause letter and a roman subclause. Indent decides:
            # subclauses sit ~30pt deeper than the clause list they belong to.
            if role in ("clause", "subclause"):
                mc, ms = CLA.match(t), SUB.match(t)
                # "(i)" is both clause letter i and roman subclause i. It is a
                # clause only when it is the letter the clause list expects next.
                want_c = chr(96 + nxt["clause"])
                want_s = ROMAN[nxt["subclause"] - 1] if nxt["subclause"] <= len(ROMAN) else None
                deeper = clause_x is not None and bb[0] > clause_x + 12
                as_clause = bool(mc) and (mc.group(1) == want_c or
                                          ("." in mc.group(1) and not deeper))
                as_sub = bool(ms) and ms.group(1) == want_s
                if as_sub and cur["clause"] and not (as_clause and not deeper):
                    nid = f"{cur['clause']}/({ms.group(1)})"
                    add(nid, "subclause", ms.group(1), None, p, bb, cur["clause"])
                    nodes[nid]["text"].append({"p": p, "t": t[ms.end():].strip(), "b": [round(v,1) for v in bb], **({"it": it["it"]} if it["it"] else {})})
                    cur.update(subclause=nid)
                    nxt["subclause"] += 1
                    continue
                if as_clause and cur["sentence"]:
                    nid = f"{cur['sentence']}/({mc.group(1)})"
                    add(nid, "clause", mc.group(1), None, p, bb, cur["sentence"])
                    nodes[nid]["text"].append({"p": p, "t": t[mc.end():].strip(), "b": [round(v,1) for v in bb], **({"it": it["it"]} if it["it"] else {})})
                    cur.update(clause=nid, subclause=None)
                    if clause_x is None:
                        clause_x = bb[0]
                    if "." not in mc.group(1):
                        nxt["clause"] = ord(mc.group(1)) - 96 + 1
                    nxt["subclause"] = 1
                    continue
            nodes[host]["text"].append({"p": p, "t": t, "b": [round(v,1) for v in bb], **({"it": it["it"]} if it["it"] else {})})

# ---- the Building Code Act, parsed the same way as a Division ----
# Sections were held as flat text until Phase 6. The Act uses the same marker
# grammar as the Code - (1) subsections, (a) clauses, (i) subclauses - so the
# sequence rules from the Division walk apply unchanged. Arial-Black lines in
# the Act are marginal notes: they title the subsection that follows.
if ACT_LO:
    add("ACT", "act", None, "Building Code Act, 1992", ACT_LO, [0, 60, 10, 70], None)
    cur_s = cur_sub = cur_cl = None
    pending = None
    anx = {"sub": 1, "cl": 1, "sc": 1}
    cl_x = None

    def act_txt(host, it, p):
        nodes[host]["text"].append({"p": p, "t": it["t"],
                                    "b": [round(v, 1) for v in it["b"]],
                                    **({"it": it["it"]} if it["it"] else {})})

    for p in range(ACT_LO, ACT_HI + 1):
        for it in ordered_lines(p):
            if it["region"] in ("header", "footer"):
                continue
            t, bb = it["t"], it["b"]
            if it["role"] == "act_section":
                m = ACTS.match(t)
                if m:
                    nid = f"ACT/{m.group(1)}"
                    add(nid, "act_section", m.group(1), pending, p, bb, "ACT")
                    cur_s, cur_sub, cur_cl = nid, None, None
                    pending, cl_x = None, None
                    anx = {"sub": 1, "cl": 1, "sc": 1}
                    rest = t[m.end():].strip()
                    if m.group(2):                       # "1.1(1) It is the role…"
                        sid = f"{nid}/({m.group(2)})"
                        add(sid, "act_subsection", m.group(2), None, p, bb, nid)
                        nodes[sid]["text"].append({"p": p, "t": rest,
                                                   "b": [round(v, 1) for v in bb],
                                                   **({"it": it["it"]} if it["it"] else {})})
                        cur_sub = sid
                        if "." not in m.group(2):
                            anx["sub"] = int(m.group(2)) + 1
                    else:
                        nodes[nid]["text"].append({"p": p, "t": rest or t,
                                                   "b": [round(v, 1) for v in bb],
                                                   **({"it": it["it"]} if it["it"] else {})})
                    continue
            if it["role"] == "label" and cur_s:
                pending = t                              # marginal note
                continue
            if not cur_s:
                act_txt("ACT", it, p)
                continue
            ms, mc, msc = SENT.match(t), CLA.match(t), SUB.match(t)
            if ms:
                num = ms.group(1)
                if "." in num or int(num) == anx["sub"]:
                    sid = f"{cur_s}/({num})"
                    add(sid, "act_subsection", num, pending, p, bb, cur_s)
                    nodes[sid]["text"].append({"p": p, "t": t[ms.end():].strip(),
                                               "b": [round(v, 1) for v in bb],
                                               **({"it": it["it"]} if it["it"] else {})})
                    cur_sub, cur_cl, pending, cl_x = sid, None, None, None
                    if "." not in num:
                        anx["sub"] = int(num) + 1
                    anx["cl"] = anx["sc"] = 1
                    continue
            if mc or msc:
                want_c = chr(96 + anx["cl"])
                want_s = ROMAN[anx["sc"] - 1] if anx["sc"] <= len(ROMAN) else None
                deeper = cl_x is not None and bb[0] > cl_x + 12
                as_sub = bool(msc) and msc.group(1) == want_s
                as_cl = bool(mc) and mc.group(1) == want_c
                if as_sub and cur_cl and not (as_cl and not deeper):
                    nid2 = f"{cur_cl}/({msc.group(1)})"
                    add(nid2, "act_subclause", msc.group(1), None, p, bb, cur_cl)
                    nodes[nid2]["text"].append({"p": p, "t": t[msc.end():].strip(),
                                                "b": [round(v, 1) for v in bb]})
                    anx["sc"] += 1
                    continue
                if as_cl and cur_sub:
                    nid2 = f"{cur_sub}/({mc.group(1)})"
                    add(nid2, "act_clause", mc.group(1), None, p, bb, cur_sub)
                    nodes[nid2]["text"].append({"p": p, "t": t[mc.end():].strip(),
                                                "b": [round(v, 1) for v in bb]})
                    cur_cl = nid2
                    if cl_x is None:
                        cl_x = bb[0]
                    anx["cl"] = ord(mc.group(1)) - 96 + 1
                    anx["sc"] = 1
                    continue
            act_txt(cur_cl or cur_sub or cur_s, it, p)

# front matter, the Act and the Index take the same italic capture as the
# Division path. They did not, so every defined term in the Preface and the
# whole Act was invisible to stage 7.
# front matter and the Index are containers too - nothing may be orphaned
add("FRONT", "front_matter", None, "Front matter and Preface", 1, [0, 60, 10, 70], None)
for p in range(1, (ACT_LO or first_contents)):
    for it in ordered_lines(p):
        if it["region"] in ("header", "footer"):
            continue
        nodes["FRONT"]["text"].append({"p": p, "t": it["t"], "b": [round(v,1) for v in it["b"]], **({"it": it["it"]} if it["it"] else {})})
if INDEX_LO:
    # The Index is not prose: it is term / subterm / continuation, set at three
    # indents per column. Parsed as entries it becomes queryable; left flat it is
    # 7,088 lines of text with 10,500 citations and no structure to hang them on.
    add("INDEX", "index", None, "Index", INDEX_LO, [0, 60, 10, 70], None)
    n_entry = 0
    cur_main = cur_sub = None
    for p in range(INDEX_LO, NPAGES + 1):
        items = [it for it in ordered_lines(p)
                 if it["region"] not in ("header", "footer") and it["t"]]
        if not items:
            continue
        xs = sorted({round(i["b"][0], 1) for i in items})
        cols = [xs[0]]
        for x in xs[1:]:
            if x - cols[-1] > 100:
                cols.append(x)
        for it in items:
            base = max([c for c in cols if c <= it["b"][0] + 2] or [cols[0]])
            lvl = min(2, max(0, round((it["b"][0] - base) / 10.8)))
            if lvl == 0:
                n_entry += 1
                cur_main = f"INDEX/e{n_entry}"
                add(cur_main, "index_entry", None, it["t"].split(",")[0][:80],
                    p, it["b"], "INDEX")
                cur_sub = None
                host = cur_main
            elif lvl == 1 and cur_main:
                n_entry += 1
                cur_sub = f"{cur_main}/s{n_entry}"
                add(cur_sub, "index_subentry", None, it["t"].split(",")[0][:80],
                    p, it["b"], cur_main)
                host = cur_sub
            else:
                host = cur_sub or cur_main or "INDEX"
            nodes[host]["text"].append({"p": p, "t": it["t"],
                                        "b": [round(v, 1) for v in it["b"]],
                                        **({"it": it["it"]} if it["it"] else {})})

with gzip.open("out/docgraph.jsonl.gz", "wt", encoding="utf-8") as fh:
    fh.write(json.dumps({"_meta": True, "nodes": len(nodes),
                         "parts": [{k: v for k, v in p.items() if k != "contents"}
                                   for p in parts]}) + "\n")
    for nid in order:
        fh.write(json.dumps(nodes[nid], ensure_ascii=False) + "\n")

c = Counter(n["type"] for n in nodes.values())
print("\nnodes:", dict(c.most_common()), "total", len(nodes), f"{time.time()-t0:.0f}s")
