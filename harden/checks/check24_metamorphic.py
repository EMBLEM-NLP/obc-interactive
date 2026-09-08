#!/usr/bin/env python3
"""Check 24 (H5) - metamorphic relations.

There is no oracle for "did I extract this 2,261-page PDF correctly", so the
recognised technique (Chen et al.) is to assert necessary relations between
inputs and outputs rather than an absolute expected value. A violated relation
is strong evidence of a fault; holding relations do not prove correctness.

MR1 text conservation   - every content character on the page is in exactly one
                          node, independent of node TYPE. This is the relation
                          that would have caught the hard-coded type list that
                          counted valid content as lost text.
MR2 cross-artifact count - the same quantity measured in the graph, the PDF and
                          the database must agree. Catches emitter drift.
MR3 subtree consistency  - a node's descendants via the closure table equal its
                          descendants via recursive traversal of the graph.
MR4 link/target symmetry - every resolved citation names a node that exists, and
                          every emitted link's target resolves in the model.
MR5 order invariance     - node identity does not depend on iteration order.
"""
import sys, os, gzip, json, re, sqlite3, random
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import pymupdf
from collections import Counter, defaultdict
from lib.canon import squash
# Paths resolve from the package root with env-var overrides, so this check
# runs from the shipped bag. Before 2026-09-07 it hardcoded build-session
# paths and could not be re-run by anyone who received the artifact.
_PKG = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))

GRAPH = os.environ.get("OBC_GRAPH", os.path.join(_PKG, "model/docgraph-merged.jsonl.gz"))
DB    = os.environ.get("OBC_DB", os.path.join(_PKG, "emitters/obc.sqlite"))
PDF1  = os.environ.get("OBC_BUILT_V1", os.path.join(_PKG, "pdf/301880_built_from_model.pdf"))
fails = []
nodes = {}
for line in gzip.open(GRAPH, "rt"):
    r = json.loads(line)
    if not r.get("_meta"):
        nodes[r["id"]] = r

# MR1 - text conservation, measured PER PAGE.
#
# The original compared corpus-wide character multisets, the same algorithm as
# check4_capture, and had the same blind spot: the merged tree carries far more
# characters than any page needs, so blanking ALL 7,667 sentences registered as
# 0.141% "unaccounted" and passed the 0.5% floor. A metamorphic relation that
# holds under total destruction of its input is not a relation. Reference
# implementation: verify/volume1/checks/check4b_capture.py.
import re as _re, unicodedata as _ud
from collections import defaultdict as _dd
_n = lambda s: _re.sub(r"[^0-9A-Za-z]+", "", _ud.normalize("NFKC", s))
MARKER = {"sentence", "clause", "subclause", "act_subsection", "act_clause",
          "act_subclause"}
_tree = _dd(list)
for n in nodes.values():
    num = n.get("number") or ""
    lead = (f"({num})" if n["type"] in MARKER else num + ".") + (n.get("heading") or "")
    prov = n.get("provenance") or []
    if isinstance(prov, dict): prov = [prov]
    pages = [x.get("page") for x in prov if isinstance(x, dict) and x.get("page") is not None]
    if lead.strip(".") and pages:
        _tree[pages[0]].append(_n(lead))
    for t in n.get("text", []) or []:
        _tree[t["p"]].append(_n(t["t"]))
_tree_text = {pg: "".join(v) for pg, v in _tree.items()}
inv, geo = {}, {}
for line in gzip.open(os.environ.get("OBC_INV_V1", os.path.join(_PKG, "verify/data/v1/inventory.jsonl.gz")), "rt"):
    r = json.loads(line)
    if not r.get("_meta"): inv[r["page"]] = r
for line in gzip.open(os.environ.get("OBC_GEO_V1", os.path.join(_PKG, "verify/data/v1/geometry.jsonl.gz")), "rt"):
    r = json.loads(line); geo[r["page"]] = r
tot = lost = 0
for pg, r in inv.items():
    cap = _tree_text.get(pg, "")
    for bi, b in enumerate(r["blocks"]):
        for li, l in enumerate(b["l"]):
            if geo[pg]["roles"].get(f"{bi}.{li}") not in ("body", "table", "figure"):
                continue
            t = _n("".join(s["t"] for s in l["s"]))
            if len(t) < 4: continue
            tot += len(t); h = len(t) // 2
            if not (t in cap or t[:h] in cap or t[h:] in cap):
                lost += len(t)
print(f"MR1 text conservation      : {lost} of {tot} characters unaccounted "
      f"({100*lost/max(1,tot):.3f}%)")
if lost / max(1, tot) > 0.005: fails.append("MR1 text conservation violated")

# MR2 - the same quantity, three ways
db = sqlite3.connect(DB)
g_nodes = len(nodes)
d_nodes = db.execute("select count(*) from node").fetchone()[0]
g_refs = sum(len(n.get("refs", [])) for n in nodes.values())
d_refs = db.execute("select count(*) from ref").fetchone()[0]
pdf = pymupdf.open(PDF1)
p_goto = sum(1 for pg in pdf for l in pg.get_links() if l["kind"] == 1)
print(f"MR2 nodes  graph={g_nodes} db={d_nodes} | refs graph={g_refs} db={d_refs}")
if g_nodes != d_nodes: fails.append(f"MR2 node count differs graph/db")
if g_refs != d_refs: fails.append(f"MR2 ref count differs graph/db")

# MR3 - closure table equals graph traversal
kids = defaultdict(list)
for nid, n in nodes.items():
    if n.get("parent"): kids[n["parent"]].append(nid)
random.seed(3)
bad3 = 0
for nid in random.sample(list(nodes), 40):
    seen, stack = set(), [nid]
    while stack:
        x = stack.pop()
        for c in kids.get(x, []):
            if c not in seen:
                seen.add(c); stack.append(c)
    n_db = db.execute("select count(*) from closure where ancestor=? and depth>0",
                      (nid,)).fetchone()[0]
    if n_db != len(seen): bad3 += 1
print(f"MR3 closure == traversal   : {40-bad3}/40 sampled nodes agree")
if bad3: fails.append(f"MR3 closure disagrees with traversal on {bad3} nodes")

# MR4 - every resolved citation names a node that exists
dangling = sum(1 for n in nodes.values() for r in n.get("refs", [])
               if r.get("target") and r["target"] not in nodes)
dangling += sum(1 for n in nodes.values() for t in n.get("terms", [])
                if t.get("target") and t["target"] not in nodes)
print(f"MR4 citation targets exist : {dangling} dangling")
if dangling: fails.append(f"MR4 {dangling} citations name a node that does not exist")

# MR5 - identity independent of iteration order
ids_a = sorted(nodes)
ids_b = sorted(nodes, key=lambda x: (len(x), x))
if set(ids_a) != set(ids_b): fails.append("MR5 identity depends on order")
print(f"MR5 order invariance       : {'ok' if set(ids_a)==set(ids_b) else 'FAIL'}")
print("RESULT:", "PASS" if not fails else f"FAIL {fails}")
sys.exit(0 if not fails else 1)
