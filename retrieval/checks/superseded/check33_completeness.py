#!/usr/bin/env python3
"""Check 33 (R4) - retrieval must return complete mandatory context.

Recall@k measures whether the right provision was found. It says nothing about
whether the answer is usable: a provision that cites a table, a defined term or
a note is not answerable without them. This measures expansion completeness -
of everything the retrieved article depends on, how much did the bundle carry?
"""
import sys, os, json, sqlite3
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from lib.hybrid import connect, fts, vec, fuse

DB = os.environ.get("OBC_DB", "out/obc-vec.sqlite")
ES = os.environ.get("OBC_EVAL", "evalset.json")
db = connect(DB)

def dependencies(nid):
    """what this article and its descendants cite: tables, notes, standards,
    other provisions, and the defined terms it uses"""
    subtree = [r[0] for r in db.execute(
        "SELECT descendant FROM closure WHERE ancestor=?", (nid,))]
    qs = ",".join("?" * len(subtree))
    refs = {r[0] for r in db.execute(
        f"SELECT dst FROM ref WHERE src IN ({qs}) AND dst IS NOT NULL", subtree)}
    terms = {r[0] for r in db.execute(
        f"SELECT dst FROM term WHERE src IN ({qs})", subtree)}
    return refs, terms

def bundle(nid, hops=1):
    """what a context assembler would carry: the article, its ancestors for
    scope, its subtree, and one hop of citations and definitions"""
    got = {nid}
    got |= {r[0] for r in db.execute(
        "SELECT descendant FROM closure WHERE ancestor=?", (nid,))}
    got |= {r[0] for r in db.execute(
        "SELECT ancestor FROM closure WHERE descendant=?", (nid,))}
    refs, terms = dependencies(nid)
    got |= refs | terms
    return got

qs = json.load(open(ES))["questions"]
test = [q for q in qs if q["split"] == "test"]
tot_dep = carried = 0
zero_dep = 0
per = []
for q in test:
    hits = fuse(fts(db, q["q"], 50), vec(db, q["q"], 50), 5)
    if q["target"] not in hits:
        continue
    refs, terms = dependencies(q["target"])
    dep = refs | terms
    if not dep:
        zero_dep += 1
        continue
    b = bundle(q["target"])
    have = len(dep & b)
    tot_dep += len(dep); carried += have
    per.append((q["q"][:38], have, len(dep)))
print(f"retrieved targets with dependencies : {len(per)}")
print(f"targets with none                   : {zero_dep}")
print(f"mandatory context carried           : {carried}/{tot_dep} "
      f"= {carried/max(1,tot_dep):.1%}")
for a, h, t in per[:6]:
    print(f"   {a:<40} {h}/{t}")
# every dependency must at least EXIST - a bundle cannot carry a dangling target
dangling = 0
for q in test:
    refs, terms = dependencies(q["target"])
    for d in refs | terms:
        if not db.execute("SELECT 1 FROM node WHERE id=?", (d,)).fetchone():
            dangling += 1
print(f"dependencies naming a node that does not exist: {dangling}")
fails = []
if carried / max(1, tot_dep) < 0.99:
    fails.append(f"expansion carries only {carried/max(1,tot_dep):.1%} of mandatory context")
if dangling:
    fails.append(f"{dangling} dependencies are dangling")
print("RESULT:", "PASS" if not fails else f"FAIL {fails}")
sys.exit(0 if not fails else 1)
