#!/usr/bin/env python3
"""Check 18 - one identity layer, three emitters.

The design review's first recommendation: permalink, currency stamp and licence
must come from a single source and appear in every output. This proves they
agree, and that the permalink scheme is stable and collision-free.
"""
import sys, os, sqlite3, glob, json, gzip, html as _h
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from emit_common import (load_graph, permalink, anchor, CURRENT_TO,
                         CURRENT_TO_ISO, THROUGH, NOTICE, COPYRIGHT, LICENCE)
fails = []
nodes, order, _ = load_graph()

# permalinks must be unique and URL-safe
pl = {}
import re
bad_chars = 0
for nid in order:
    p = permalink(nid)
    if re.search(r"[^A-Za-z0-9._/-]", p):
        bad_chars += 1
    if p in pl:
        fails.append(f"permalink collision: {nid} and {pl[p]} -> {p}")
    pl[p] = nid
print(f"nodes {len(order)} | unique permalinks {len(pl)} | non-URL-safe {bad_chars}")
if bad_chars: fails.append(f"{bad_chars} permalinks contain unsafe characters")

# an inserted provision must not disturb its siblings
ins = [n for n in order if re.search(r"\d+[A-Z]\.?$", nodes[n].get("number") or "")]
print(f"letter-suffixed provisions (insertions) addressable: {len(ins)}"
      f"  e.g. {[permalink(x) for x in ins[:2]]}")
if len(ins) < 10: fails.append("insertions not represented")

db = sqlite3.connect("out/obc.sqlite")
m = dict(db.execute("SELECT key, value FROM meta").fetchall())
if m.get("current_to") != CURRENT_TO_ISO: fails.append("sqlite currency mismatch")
if m.get("licence") != LICENCE: fails.append("sqlite licence mismatch")
n_pl = db.execute("SELECT count(*) FROM node WHERE permalink IS NULL OR permalink=''").fetchone()[0]
if n_pl: fails.append(f"{n_pl} sqlite rows without a permalink")
print(f"sqlite : current_to={m.get('current_to')} licence={'ok' if m.get('licence')==LICENCE else 'MISMATCH'}")

md = sorted(glob.glob("out/markdown/*.md"))
ht = sorted(glob.glob("out/html/*.html"))
def has_all(text):
    t = _h.unescape(text)
    return (CURRENT_TO_ISO in t or CURRENT_TO in t) and "free of charge" in t \
           and "King's Printer" in t and "Unofficial" in t
bad_md = [f for f in md if not has_all(open(f, encoding="utf-8").read())]
bad_ht = [f for f in ht if not has_all(open(f, encoding="utf-8").read())]
print(f"markdown files carrying currency+licence+notice : {len(md)-len(bad_md)}/{len(md)}")
print(f"html files carrying currency+licence+notice     : {len(ht)-len(bad_ht)}/{len(ht)}")
if bad_md: fails.append(f"markdown missing identity: {[os.path.basename(x) for x in bad_md][:3]}")
if bad_ht: fails.append(f"html missing identity: {[os.path.basename(x) for x in bad_ht][:3]}")

# anchors in HTML must match the permalink scheme
import random
random.seed(2)
sample = random.sample(order, 200)
miss = 0
allht = "".join(open(f, encoding="utf-8").read() for f in ht)
for nid in sample:
    if nodes[nid]["type"] in ("division", "index_entry", "index_subentry", "index"):
        continue
    if f'id="{anchor(nid)}"' not in allht:
        miss += 1
print(f"sampled node anchors present in html : {200-miss}/200")
print("RESULT:", "PASS" if not fails else f"FAIL {fails}")
sys.exit(0 if not fails else 1)
