#!/usr/bin/env python3
"""Control for the negative assertions in the build gate.

Gate G7 asserts an absence: zero dead Launch links, zero disagreeing overlaps,
zero pages worse than the previous build. An absence check that is simply broken
also reports zero. This runs the same detectors against a KNOWN POSITIVE
fixture - the pristine source, which carries 819 dead Launch links and 18 wrong
TOC targets - and fails if they are not found.
"""
import sys, os, json, re
import pymupdf
from collections import Counter

SRC = os.environ.get("OBC_SRC_V1", "301880.pdf")
LAB = "out/labels.json"
d = pymupdf.open(SRC)
k = Counter()
for p in d:
    for l in p.get_links():
        k[l["kind"]] += 1
lab = json.load(open(LAB))
rev = {}
for a, b in lab.items():
    sec, num = b
    if sec and num is not None:
        rev.setdefault((sec, num), int(a))
TOC = [75,109,117,123,159,183,184,457,553,575,599,679,711,712,713,714,
       1035,1041,1113,1119,1153,1159]
wrong = missing = 0
for pno in TOC:
    page = d[pno - 1]; sec = lab[str(pno)][0]; links = page.get_links()
    for blk in page.get_text("dict")["blocks"]:
        if blk["type"] != 0: continue
        for ln in blk["lines"]:
            t = "".join(sp["text"] for sp in ln["spans"]).strip()
            R = pymupdf.Rect(ln["bbox"])
            if not (re.fullmatch(r"\d{1,4}", t) and R.x0 > 240 and R.y0 < 720): continue
            want = rev.get((sec, int(t)))
            if not want: continue
            hits = [L for L in links if not (R & L["from"]).is_empty
                    and (R & L["from"]).get_area() > 0.45 * R.get_area()]
            if not hits: missing += 1
            elif not any(h["kind"] == 1 and h["page"] + 1 == want for h in hits): wrong += 1
print(f"positive fixture (pristine source): Launch links {k[3]}, "
      f"wrong TOC targets {wrong}, missing {missing}")
ok = k[3] == 819 and wrong == 18 and missing == 2
print("RESULT:", "PASS" if ok else "FAIL - the detectors did not find the known defects")
sys.exit(0 if ok else 1)
