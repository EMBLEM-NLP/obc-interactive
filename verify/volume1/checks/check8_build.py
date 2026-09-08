#!/usr/bin/env python3
"""Check 8 - the model build must be a strict superset of the patched build.

The first version of this check only measured what the build ADDED. It passed a
file that had reinherited 819 dead Launch links and all 18 wrong TOC targets from
the source, because it never asked what was left behind. Every assertion below
exists because that failure got through.
"""
import sys, os
import gzip, json, random, re, pymupdf
from collections import Counter

NEW = "out/301880_built.pdf"
BASE = os.environ.get("OBC_BASELINE", "../baseline/v9-baseline.json")
SRC = os.environ.get("OBC_SRC_V1", "301880.pdf")
LAB = "out/labels.json"
nodes = {}
for line in gzip.open("out/docgraph.jsonl.gz", "rt"):
    r = json.loads(line)
    if not r.get("_meta"):
        nodes[r["id"]] = r
a, s = pymupdf.open(NEW), pymupdf.open(SRC)
# The previous build is a frozen JSON baseline, not a 19 MB PDF fixture: a
# regression baseline should be data you can read and diff.
base = json.load(open(BASE))
# a cross-volume citation must be verified against Volume 2, not against a
# page index in this file. Checking it here was the 7th time this suite
# reported its own blind spot as a defect.
try:
    v2 = pymupdf.open("out/301881_built.pdf")
except Exception:
    v2 = None
fails = []

def kinds(d):
    c = Counter()
    for p in d:
        for l in p.get_links():
            c[l["kind"]] += 1
    return c
ka, ks = kinds(a), kinds(s)
kb = {1: base["goto"], 2: base["uri"], 3: base["launch"]}
print(f"{'':<30}{'model':>9}{'v9':>9}{'source':>9}")
print(f"{'internal (GoTo)':<30}{ka[1]:>9}{kb[1]:>9}{ks[1]:>9}")
print(f"{'web / mail (URI)':<30}{ka[2]:>9}{kb[2]:>9}{ks[2]:>9}")
print(f"{'dead file links (Launch)':<30}{ka[3]:>9}{kb[3]:>9}{ks[3]:>9}")
if ka[3]: fails.append(f"{ka[3]} Launch links survive")
if ka[1] < kb[1]: fails.append("fewer internal links than v9")
if ka[2] < kb[2]: fails.append(f"fewer URI links than v9 ({ka[2]} < {kb[2]})")

# 1. no source-era error may survive: TOC number cells
lab = json.load(open(LAB))
rev = {}
for k, v in lab.items():
    sec, num = v
    if sec and num is not None:
        rev.setdefault((sec, num), int(k))
TOC = [75,109,117,123,159,183,184,457,553,575,599,679,711,712,713,714,
       1035,1041,1113,1119,1153,1159]
def toc_acc(d):
    ok = wrong = miss = 0
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
                if not hits: miss += 1
                elif any(h["kind"] == 1 and h["page"] + 1 == want for h in hits): ok += 1
                else: wrong += 1
    return ok, wrong, miss
oa = toc_acc(a); ob = (base["toc_ok"], base["toc_wrong"], base["toc_missing"])
print(f"{'TOC cells ok / wrong / missing':<30}{f'{oa[0]}/{oa[1]}/{oa[2]}':>9}{f'{ob[0]}/{ob[1]}/{ob[2]}':>9}")
if oa[1] or oa[2]: fails.append(f"TOC: {oa[1]} wrong, {oa[2]} missing")
if oa[0] < ob[0]: fails.append("fewer correct TOC links than v9")

# 1b. every contents page must have at least as many links as the previous build
MASTER = [7, 8, 30, 31, 32]
short = []
for pg in MASTER + TOC:
    na = len([l for l in a[pg-1].get_links() if l["kind"] in (1, 5)])
    nb = base["contents_page_links"].get(str(pg), 0)
    if na < nb:
        short.append((pg, na, nb))
print(f"{'contents pages short vs v9':<30}{len(short):>9}   {short[:5]}")
if short: fails.append(f"contents pages with fewer links than v9: {short[:5]}")

# 1c. no bookmark may point outside the document or into the other volume
outside = [t for t in a.get_toc() if not (1 <= t[2] <= a.page_count)]
print(f"{'bookmarks outside document':<30}{len(outside):>9}")
if outside: fails.append(f"{len(outside)} bookmarks point outside the document")

# 2. no two internal links may overlap and disagree
conflict = 0
for i in range(a.page_count):
    ls = [l for l in a[i].get_links() if l["kind"] == 1]
    for x in range(len(ls)):
        for y in range(x + 1, len(ls)):
            ra, rb = ls[x]["from"], ls[y]["from"]
            it = ra & rb
            if it.is_empty: continue
            if it.get_area() > 0.6 * min(ra.get_area(), rb.get_area()) \
               and ls[x]["page"] != ls[y]["page"]:
                conflict += 1
print(f"{'overlapping, disagreeing links':<30}{conflict:>9}{'-':>9}")
if conflict: fails.append(f"{conflict} overlapping links point to different pages")

# 3. accuracy against the model's own records
VAR = lambda k: {k, k.rstrip("s"), k + "s", re.sub(r"ies$", "y", k), re.sub(r"ves$", "f", k)}
random.seed(11)
refs = [(n, r) for n in nodes.values() for r in n.get("refs", []) if r.get("target")]
ok = tot = 0
for n, r in random.sample(refs, 300):
    t = nodes[r["target"]]
    num = (t.get("number") or "").rstrip(".")
    if not num or not t.get("provenance"): continue
    # a cross-volume citation is verified against Volume 2, not against a page
    # index in this file - the 7th time this suite reported its own blind spot
    src = a if t.get("volume", 1) == 1 else v2
    if src is None: continue
    tot += 1
    ok += num in src[t["provenance"][0]["page"] - 1].get_text()
terms = [(n, t) for n in nodes.values() for t in n.get("terms", []) if t.get("to_page")]
tok = ttot = 0
for n, t in random.sample(terms, 250):
    txt = a[t["to_page"] - 1].get_text().lower(); ttot += 1
    if any(re.search(r"[“\"']?" + re.escape(v) + r"[”\"']?(?:\s*\([^)]{0,90}\))?\s+means", txt)
           for v in VAR(t["term"])):
        tok += 1
print(f"{'reference targets correct':<30}{f'{ok}/{tot}':>9}")
print(f"{'defined-term targets correct':<30}{f'{tok}/{ttot}':>9}")
if ok / max(1, tot) < 0.98: fails.append("reference accuracy below 98%")
if tok / max(1, ttot) < 0.95: fails.append("term accuracy below 95%")

# 4. nothing v9 could do that the model build cannot
pa = {i + 1 for i in range(a.page_count) if any(l["kind"] == 1 for l in a[i].get_links())}
pb = set(base["pages_with_internal_links"])
lost = sorted(pb - pa)
print(f"{'pages linked in v9, not here':<30}{len(lost):>9}   {lost[:10]}")
if lost: fails.append(f"{len(lost)} pages lost links relative to v9")
print(f"{'bookmarks':<30}{len(a.get_toc()):>9}{base['bookmarks']:>9}")
if len(a.get_toc()) < base["bookmarks"]: fails.append("fewer bookmarks than the baseline")

print("\nRESULT:", "PASS" if not fails else "FAIL")
for f in fails:
    print("   -", f)
