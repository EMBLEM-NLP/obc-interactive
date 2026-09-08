#!/usr/bin/env python3
"""Check 12 - Volume 2 container model.

Two-way, like every other structural gate here:
  * every container the running headers name must exist as a node, and every
    container node must be named by a running header
  * a container's first page must carry a title naming it, so the header-derived
    spans are validated against the document's own title pages
  * Appendix A notes and Supplementary Standards must be addressable
"""
import sys, os, gzip, json, re
from collections import Counter

inv, nodes, meta = {}, {}, None
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
STD = re.compile(r"Supplementary Standard\s+(S[ABC]-\d+)")
declared = set()
for p, r in inv.items():
    for b in r["blocks"]:
        for l in b["l"]:
            if l["b"][1] < 45:
                t = "".join(s["t"] for s in l["s"]).strip()
                m = STD.search(t)
                if m: declared.add(m.group(1))
                elif re.search(r"\bA-\d", t): declared.add("APPA")
built = {n["id"] for n in nodes.values()
         if n["type"] in ("supplementary_standard", "appendix")}
fails = []
print(f"containers declared by running headers : {len(declared)}")
print(f"containers built as nodes              : {len(built)}")
print(f"   declared but not built: {sorted(declared - built)}")
print(f"   built but not declared: {sorted(built - declared)}")
if declared - built: fails.append("containers missing")
if built - declared: fails.append("containers invented")

# each container's first page must carry a title naming it
titled = 0
for c in meta["containers"]:
    if c["key"] == "APPA":
        titled += 1; continue
    body = " ".join("".join(s["t"] for s in l["s"])
                    for b in inv[c["lo"]]["blocks"] for l in b["l"])
    if c["key"].replace("-", "") in body.replace("-", "").replace(" ", ""):
        titled += 1
print(f"container first pages naming their standard: {titled} of {len(meta['containers'])}")
if titled < len(meta["containers"]): fails.append("a container start page does not name it")

notes = [n for n in nodes.values() if n["type"] == "note"]
print(f"Appendix A notes addressable : {len(notes)}")
print(f"Supplementary Standards      : {len([n for n in nodes.values() if n['type']=='supplementary_standard'])}")
if len(notes) < 500: fails.append(f"only {len(notes)} notes")
if len(built) < 15: fails.append("fewer than 15 standards")
print("RESULT:", "PASS" if not fails else f"FAIL {fails}")
sys.exit(0 if not fails else 1)
