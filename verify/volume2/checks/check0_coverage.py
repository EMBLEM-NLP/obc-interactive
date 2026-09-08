#!/usr/bin/env python3
"""Check 0 - character coverage, in two parts.

A. The inventory must reproduce the extractor's own page text exactly. This is
   the hard assertion: it proves the block/line/span walk loses nothing.

B. An INDEPENDENT engine (pdftotext) must agree within a tolerance. Part B is
   the useful one - it is not circular - but two engines legitimately disagree
   on tokenisation. Volume 2 exposed this: pdftotext emits some table cells
   several times ('gypsum board' x8 on p599), so requiring exact equality
   with a second engine failed a document that had lost nothing.
"""
import sys, os, gzip, json, subprocess, re, unicodedata
from collections import Counter
import pymupdf

INV = sys.argv[1] if len(sys.argv) > 1 else "out/inventory.jsonl.gz"
SRC = sys.argv[2] if len(sys.argv) > 2 else os.environ.get("OBC_SRC_V1", "301880.pdf")
PAGE_TOL = 200          # characters, per page, between different engines
TOTAL_TOL = 0.0005      # 0.05% of all characters

def norm(s):
    s = unicodedata.normalize("NFKC", s)
    s = s.replace("\u00a0", " ").replace("\ufb01", "fi").replace("\ufb02", "fl")
    return re.sub(r"\s+", "", s)

inv = {}
with gzip.open(INV, "rt", encoding="utf-8") as fh:
    for line in fh:
        r = json.loads(line)
        if r.get("_meta"):
            continue
        inv[r["page"]] = "".join(s["t"] for b in r["blocks"]
                                 for l in b["l"] for s in l["s"])

doc = pymupdf.open(SRC)
walk_bad = []
tot_i = 0
for pg, body in inv.items():
    a, b = Counter(norm(body)), Counter(norm(doc[pg - 1].get_text()))
    tot_i += sum(a.values())
    if b - a:
        walk_bad.append((pg, sum((b - a).values())))

txt = subprocess.run(["pdftotext", "-q", SRC, "-"],
                     capture_output=True, text=True).stdout.split("\f")
eng_bad, tot_p, delta = [], 0, 0
for pg, body in inv.items():
    a = Counter(norm(body))
    b = Counter(norm(txt[pg - 1] if pg - 1 < len(txt) else ""))
    tot_p += sum(b.values())
    d = sum((b - a).values())
    if d:
        delta += d
        eng_bad.append((pg, d))

print(f"pages                         : {len(inv)}")
print(f"chars in inventory            : {tot_i}")
print(f"A. pages where the inventory differs from the extractor: {len(walk_bad)}")
for pg, n in walk_bad[:8]:
    print(f"      p{pg}: {n}")
print(f"B. independent engine (pdftotext) chars: {tot_p}")
print(f"   pages differing: {len(eng_bad)}  total {delta} chars "
      f"({100*delta/max(1,tot_p):.4f}%)")
for pg, n in sorted(eng_bad, key=lambda x: -x[1])[:8]:
    print(f"      p{pg}: {n}")
fails = []
if walk_bad:
    fails.append(f"{len(walk_bad)} pages lose text in the inventory walk")
over = [p for p, n in eng_bad if n > PAGE_TOL]
if over:
    fails.append(f"pages beyond the per-page engine tolerance: {over[:6]}")
if delta / max(1, tot_p) > TOTAL_TOL:
    fails.append(f"engine delta {100*delta/max(1,tot_p):.4f}% exceeds {100*TOTAL_TOL}%")
print("RESULT:", "PASS" if not fails else f"FAIL {fails}")
sys.exit(0 if not fails else 1)
