#!/usr/bin/env python3
"""Stage 5 - bind tables into the document graph.

Each table becomes a node with a real cell grid, attached to the provision named
in its "Forming Part of ..." line. That binding is the document's own statement
of where the table belongs, so it is used rather than inferred from position.
"""
import gzip, json, re, time
from collections import Counter

nodes, order = {}, []
meta = None
for line in gzip.open("out/docgraph.jsonl.gz", "rt"):
    r = json.loads(line)
    if r.get("_meta"):
        meta = r
    else:
        nodes[r["id"]] = r
        order.append(r["id"])
runs = [json.loads(l) for l in gzip.open("out/tables.jsonl.gz", "rt")][1:]
inv = {}
for line in gzip.open("out/inventory.jsonl.gz", "rt"):
    r = json.loads(line)
    if not r.get("_meta"):
        inv[r["page"]] = r

FORM = re.compile(r"Forming Part of\s+(?:Sentence|Article|Subsection|Section|Clause)?s?\s*"
                  r"([0-9]+(?:\.[0-9]+){1,4}[A-Z]?)\.?(?:\((\d+)\))?")
# page -> part id, from the tree's own provenance
page_part = {}
for nid, n in nodes.items():
    if n["type"] in ("article", "subsection", "section") and n["provenance"]:
        page_part.setdefault(n["provenance"][0]["page"], nid.rsplit("/", 1)[0])
parts = sorted({(p["lo"], p["hi"], f'{p["division"]}/{p["part"]}')
                for p in meta["parts"] if p["division"] and p["part"]})

def part_of(page):
    for lo, hi, pid in parts:
        if lo <= page <= hi:
            return pid
    return None

t0 = time.time()
bound = unbound = 0
stat = Counter()
for run in runs:
    des = run["designator"]
    p0 = run["pages"][0]
    pid = part_of(p0)
    if not des or not pid:
        stat["no part context"] += 1
        continue
    # the caption block states where the table belongs
    target = None
    for b in inv[p0]["blocks"]:
        for l in b["l"]:
            t = "".join(s["t"] for s in l["s"]).strip()
            m = FORM.search(t)
            if m:
                num = m.group(1)
                cand = f"{pid}/{num}"
                if cand in nodes:
                    target = cand + (f"/({m.group(2)})" if m.group(2) and
                                     f"{cand}/({m.group(2)})" in nodes else "")
                else:
                    for other in parts:
                        c2 = f"{other[2]}/{num}"
                        if c2 in nodes:
                            target = c2
                            break
                break
        if target:
            break
    nid = f"{pid}/table/{des}"
    grid = []
    for part in run["parts"]:
        for c in part["cells"]:
            grid.append({"page": part["page"], "r": c["r"], "c": c["c"],
                         "rowspan": c["rowspan"], "colspan": c["colspan"],
                         "text": " ".join(x["t"] for x in c["lines"]).strip()})
    parent = target or pid
    n = {"id": nid, "type": "table", "number": des, "heading": None,
         "parent": parent, "children": [], "text": [],
         "forming_part_of": target, "pages": run["pages"],
         "ncols": run["ncols"], "nrows": run["nrows"], "grid": grid,
         "provenance": [{"page": p, "bbox": pt["box"]}
                        for p, pt in zip(run["pages"], run["parts"])]}
    if nid in nodes:                       # a designator reused by a sub-table
        nid = f"{nid}#{len([k for k in nodes if k.startswith(nid)])}"
        n["id"] = nid
    nodes[nid] = n
    order.append(nid)
    if parent in nodes:
        nodes[parent]["children"].append(nid)
    bound += bool(target)
    unbound += (not target)

with gzip.open("out/docgraph.jsonl.gz", "wt", encoding="utf-8") as fh:
    fh.write(json.dumps({**meta, "nodes": len(nodes)}) + "\n")
    for nid in order:
        fh.write(json.dumps(nodes[nid], ensure_ascii=False) + "\n")

print(f"tables added        : {bound + unbound}")
print(f"  bound to the provision named in 'Forming Part of' : {bound}")
print(f"  attached to their Part (no binding found)         : {unbound}")
print(f"nodes now: {len(nodes)}   {time.time()-t0:.0f}s")
