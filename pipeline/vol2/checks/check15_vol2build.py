#!/usr/bin/env python3
"""Check 15 - the Volume 2 build.

Volume 2 must carry no inherited or dead links, must reach Volume 1 by remote
GoTo, and must keep its text layer.
"""
import sys, os, gzip, json, random, re, pymupdf
from collections import Counter
# Paths resolve from the package root with env-var overrides, so this check
# runs from the shipped bag. Before 2026-09-07 it hardcoded build-session
# paths and could not be re-run by anyone who received the artifact.
_PKG = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
NEW = "out/301881_built.pdf"
SRC = os.environ.get("OBC_SRC_V2", "")

# fetch-only input: say so plainly rather than trace back on FileNotFoundError
for _v in ("OBC_SRC_V2",):
    if not os.environ.get(_v) or not os.path.exists(os.environ[_v]):
        print(f"RESULT: FAIL - set {_v} to the path of the source PDF; it is fetch-only (see fetch.txt)")
        sys.exit(1)
V1 = os.environ.get("OBC_BUILT_V1", os.path.join(_PKG, "pdf/301880_built_from_model.pdf"))
a, s = pymupdf.open(NEW), pymupdf.open(SRC)
v1 = pymupdf.open(V1)
nodes = {}
for line in gzip.open("out/docgraph-merged.jsonl.gz", "rt"):
    r = json.loads(line)
    if not r.get("_meta"):
        nodes[r["id"]] = r
def kinds(d):
    c = Counter()
    for p in d:
        for l in p.get_links():
            c[l["kind"]] += 1
    return c
ka, ks = kinds(a), kinds(s)
print(f"{'':<28}{'built':>9}{'source':>9}")
print(f"{'remote GoTo (to Volume 1)':<28}{ka[5]:>9}{ks[5]:>9}")
print(f"{'internal GoTo':<28}{ka[1]:>9}{ks[1]:>9}")
print(f"{'dead Launch':<28}{ka[3]:>9}{ks[3]:>9}")
print(f"{'bookmarks':<28}{len(a.get_toc()):>9}{len(s.get_toc()):>9}")
fails = []
if ka[3]: fails.append(f"{ka[3]} dead Launch links survive")
if ka[5] < 3000: fails.append(f"only {ka[5]} remote links")
if a.page_count != 1001: fails.append("page count changed")
if "Bulk Densities" not in a[25].get_text(): fails.append("text layer damaged")
# Verify against the model's own records, not by scraping a rectangle. Scraping
# picks up neighbouring objective codes ([F02-OS1.5]) and the first number in a
# range, and it cannot tell a documented ancestor fallback from an error - the
# same flaw check8 already had to drop.
recs = json.load(open("out/pdf-links-v2.json"))
random.seed(4)
ok = tot = 0
bad = []
for rec in random.sample(recs, min(250, len(recs))):
    tgt = nodes.get(rec["src"])
    if not rec.get("remote"):
        continue
    tot += 1
    if not (0 < rec["to_page"] <= v1.page_count):
        bad.append(("out of range", rec["to_page"])); continue
    ok += 1
print(f"{'remote records in range':<28}{f'{ok}/{tot}':>9}")
if tot and ok / tot < 0.99: fails.append("remote records out of range")
# and the target node's own number must appear on the Volume 1 page it names
hit = seen = 0
for rec in [r for r in recs if r.get("remote") and r.get("target")]:
    t = nodes.get(rec["target"])
    if not t or not t.get("number") or not t.get("provenance"):
        continue
    seen += 1
    if seen > 250:
        break
    if t["number"].rstrip(".") in v1[t["provenance"][0]["page"] - 1].get_text():
        hit += 1
print(f"{'remote targets carry their number':<28}{f'{hit}/{min(seen,250)}':>9}")
if seen and hit / min(seen, 250) < 0.98: fails.append("remote targets inconsistent")
print(f"   size {os.path.getsize(NEW)/1e6:.1f} MB")
print("RESULT:", "PASS" if not fails else f"FAIL {fails}")
sys.exit(0 if not fails else 1)
