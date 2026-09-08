#!/usr/bin/env python3
"""Stage 2a - profile font signatures before assigning any structural role.
The role map is derived from what the document actually uses, not assumed."""
import gzip, json, re
from collections import Counter, defaultdict

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

NUM = re.compile(r"^(\d+(?:\.\d+){0,4})\.?")
sig = Counter(); samp = defaultdict(list)
for p, r in inv.items():
    g = geo[p]
    for bi, b in enumerate(r["blocks"]):
        for li, l in enumerate(b["l"]):
            if g["roles"].get(f"{bi}.{li}") != "body":
                continue
            s0 = l["s"][0]
            txt = "".join(s["t"] for s in l["s"]).strip()
            if not txt:
                continue
            m = NUM.match(txt)
            shape = ("N" * (m.group(1).count(".") + 1)) if m else (
                "(n)" if txt.startswith("(") and txt[1:2].isdigit() else
                "(a)" if txt.startswith("(") and txt[1:2].isalpha() else "text")
            k = (s0["f"], s0["sz"], shape)
            sig[k] += 1
            if len(samp[k]) < 2:
                samp[k].append((p, txt[:56]))

print(f"{'font':<28}{'sz':>5}{'shape':>7}{'count':>8}  sample")
for k, n in sig.most_common(24):
    f, sz, shape = k
    print(f"{f[:27]:<28}{sz:>5}{shape:>7}{n:>8}  p{samp[k][0][0]} {samp[k][0][1]}")
