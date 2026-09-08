#!/usr/bin/env python3
"""Stage 2 - structural roles from font signature + line shape.

The signature map below was derived by profiling the corpus (stage2_profile.py),
not assumed. Roles are emitted per line; the tree is built in stage 3.
"""
import gzip, json, re, sys
from collections import Counter

inv, geo = {}, {}
with gzip.open("out/inventory.jsonl.gz", "rt") as fh:
    for line in fh:
        r = json.loads(line)
        if not r.get("_meta"):
            inv[r["page"]] = r
with gzip.open("out/geometry.jsonl.gz", "rt") as fh:
    for line in fh:
        r = json.loads(line)
        geo[r["page"]] = r

NUM      = re.compile(r"^(\d+(?:\.\d+){0,4}[A-Z]?)\.")
# the Code inserts articles with a letter suffix: 7.6.2.5A., 9.10.14A.
SECTION  = re.compile(r"^Section\s+(\d+(?:\.\d+){1,2})\.?(?:\s|$)(?!of\b)")
# the trailing period is optional: the source omits it in "Section 1.1 General"
# and "Section 5.5  Vapour Diffusion"
ACTSTART = re.compile(r"^(\d+(?:\.\d+){0,2})(?:\((\d+(?:\.\d+)?)\))?\s{1,}(?=[A-Z“(RN])")
SENT     = re.compile(r"^\((\d+(?:\.\d+)?)\)")
CLAUSE   = re.compile(r"^\(([a-z](?:\.\d+)?)\)")
SUBCL    = re.compile(r"^\(([ivx]+)\)")
LEADER   = re.compile(r"\.{4,}")

def role_for(font, size, x, txt):
    black = "Black" in font
    bold  = "Bold" in font
    m = NUM.match(txt)
    depth = m.group(1).count(".") + 1 if m else 0
    ms = SECTION.match(txt)
    if ms and (black or bold) and not re.match(r"^Section\s+\S+\s+of\b", txt):
        return "section"      # "Section 4.1 of the Act" is a citation, not a heading
    if black and depth == 3:
        return "subsection"
    if black and depth == 4:
        return "article"
    if black and depth == 2:
        return "section"
    if black and not m:
        return "label"                      # Act marginal note / part title / heading text
    if bold and "Times" in font and ACTSTART.match(txt) and x < 400:
        return "act_section"
    if SENT.match(txt):
        return "sentence"
    if CLAUSE.match(txt):
        return "clause"
    if SUBCL.match(txt):
        return "subclause"
    return "text"

out = {}
stats = Counter()
contents_pages = set()
for p, r in inv.items():
    g = geo[p]
    leaders = narrow = 0
    roles = {}
    for bi, b in enumerate(r["blocks"]):
        for li, l in enumerate(b["l"]):
            key = f"{bi}.{li}"
            region = g["roles"].get(key)
            txt = "".join(s["t"] for s in l["s"]).strip()
            if LEADER.search(txt):
                leaders += 1
            if l["s"][0]["f"].startswith("ArialNarrow") and l["s"][0]["sz"] <= 9.5:
                narrow += 1
            if region != "body" or not txt:
                roles[key] = region
                stats[region] += 1
                continue
            s0 = l["s"][0]
            rl = role_for(s0["f"], s0["sz"], l["b"][0], txt)
            roles[key] = rl
            stats[rl] += 1
    # a contents page pairs dot leaders with the contents font; the Referenced
    # Documents table also uses ArialNarrow but has no leaders at all
    if leaders >= 2 and narrow >= 10:
        contents_pages.add(p)
    out[p] = roles

with gzip.open("out/roles.jsonl.gz", "wt", encoding="utf-8") as fh:
    fh.write(json.dumps({"_meta": True, "contents_pages": sorted(contents_pages)}) + "\n")
    for p in sorted(out):
        fh.write(json.dumps({"page": p, "roles": out[p]}) + "\n")

print("line roles:", dict(stats.most_common()))
print("contents pages detected (dot-leader density):", len(contents_pages),
      sorted(contents_pages)[:26])
