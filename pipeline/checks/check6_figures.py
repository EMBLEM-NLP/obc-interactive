#!/usr/bin/env python3
"""Check 6 - classified image assets and caption coverage."""
import sys, gzip, json, re, os
from collections import Counter

inv = {}
for line in gzip.open("out/inventory.jsonl.gz", "rt"):
    r=json.loads(line)
    if not r.get("_meta"): inv[r["page"]]=r
assets=[json.loads(l) for l in gzip.open("out/figures.jsonl.gz","rt")][1:]
CAP=re.compile(r"^Figure\s+([A-Z]?-?\d+(?:\.\d+)*\.?(?:-\.?[A-Z0-9/]+)?)\s*(\(Cont)?", re.I)

def norm(v):
    if not v: return None
    v=v.strip().rstrip(".")
    v=re.sub(r"(?<=\d)-\.([A-Z0-9/]+)$", r".-\1", v, flags=re.I)
    return v

declared=set()
for p,r in inv.items():
    lines=sorted(((l["b"][1],"".join(s["t"] for s in l["s"]).strip()) for b in r["blocks"] for l in b["l"]), key=lambda x:x[0])
    lines=[x for x in lines if x[1]]
    for i,(y,t) in enumerate(lines):
        m=CAP.match(t)
        if m and ("Forming Part of" in " ".join(x[1] for x in lines[i+1:i+4]) or m.group(2)): declared.add(norm(m.group(1)))

built={norm(a.get("designator")) for a in assets if a.get("asset_role")=="formal_figure" and a.get("designator")}
missing=sorted(declared-built); extra=sorted(built-declared)
roles=Counter(a.get("asset_role") for a in assets)

def build_path(ref):
    if ref.startswith("assets/"): ref=ref[len("assets/"): ]
    return os.path.join("out","assets",ref)
broken=[ref for a in assets for ref in a.get("files",[]) if not os.path.exists(build_path(ref)) or os.path.getsize(build_path(ref))==0]
micro_with_files=[a for a in assets if a.get("asset_role")=="micro_nonfigure" and a.get("files")]
packageable_without_files=[a for a in assets if a.get("asset_role")!="micro_nonfigure" and not a.get("files")]
table_as_figure=[a for a in assets if a.get("asset_role")=="table_cell_graphic" and a.get("designator")]
bad_g=[a for a in assets if a.get("page")==501 and a.get("asset_role")=="formal_figure" and a.get("designator")!="4.1.7.6.-G"]

print(f"declared figure captions : {len(declared)}")
print(f"formal figure records    : {len(built)}")
print(f"roles                    : {dict(roles)}")
print(f"declared not exported    : {len(missing)} {missing[:8]}")
print(f"exported not declared    : {len(extra)} {extra[:8]}")
print(f"missing/zero files       : {len(broken)}")
print(f"micro records with files : {len(micro_with_files)}")
print(f"packageable no files     : {len(packageable_without_files)}")
print(f"table graphics captioned : {len(table_as_figure)}")
print(f"Figure G naming defects  : {len(bad_g)}")
fails=missing or broken or micro_with_files or packageable_without_files or table_as_figure or bad_g
print("RESULT:","PASS" if not fails else "REVIEW")
sys.exit(0 if not fails else 1)
