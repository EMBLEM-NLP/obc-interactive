#!/usr/bin/env python3
"""Check 32 (R3) - does the vector layer earn its place, and does fusion keep it?

Reported on the TEST half only. The fusion policy (reserve=2) was chosen on the
DEV half, so the number the gate judges is not the number the design was tuned
against.

Two separate claims, because they can come apart and did:
  A. the vector layer reaches provisions the lexical layer cannot - measured on
     questions constructed to share no content word with the target
  B. fusion does not throw that away - hybrid must be at least as good as the
     better single layer, overall and on the hard subset
"""
import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from lib.hybrid import connect, fts, vec, fuse

DB = os.environ.get("OBC_DB", "out/obc-vec.sqlite")
ES = os.environ.get("OBC_EVAL", "evalset.json")
# the fusion contract: hybrid@n contains each layer's own top ceil(n/2)
CONTRACT = "hybrid@n >= max(fts@n, vec@ceil(n/2)) and >= fts@n on every subset"
qs = json.load(open(ES))["questions"]
db = connect(DB)
cache = {q["q"]: (fts(db, q["q"], 50), vec(db, q["q"], 50)) for q in qs}
test = [q for q in qs if q["split"] == "test"]
tpar = [q for q in test if q["kind"] == "paraphrase"]

def run(sub, mode, k):
    hit = 0
    for q in sub:
        f, v = cache[q["q"]]
        lst = (f if mode == "fts" else v if mode == "vec"
               else fuse(f, v, k))[:k]
        hit += q["target"] in lst
    return hit

print(f"TEST split: {len(test)} questions, {len(tpar)} of them lexically disjoint")
print(f"{'':<9}{'recall@5':>12}{'recall@10':>12}{'recall@20':>12}")
tbl = {}
for m in ("fts", "vec", "hybrid"):
    row = [run(test, m, k) for k in (5, 10, 20)]
    tbl[m] = row
    print(f"  {m:<7}" + "".join(f"{r}/{len(test)} = {r/len(test):>6.0%}" for r in row))
print(f"\nlexically disjoint only ({len(tpar)} questions)")
ptbl = {}
for m in ("fts", "vec", "hybrid"):
    row = [run(tpar, m, k) for k in (5, 10, 20)]
    ptbl[m] = row
    print(f"  {m:<7}" + "".join(f"{r}/{len(tpar)}      " for r in row))

fails = []
# A. the vector layer must beat lexical on the disjoint subset at some usable k
if not any(ptbl["vec"][i] > ptbl["fts"][i] for i in range(3)):
    fails.append("vectors never beat FTS5 on lexically disjoint questions - "
                 "the embedding layer is not earning its place")
# B. the fusion contract. Note what is NOT asserted: hybrid@k >= vec@k is
# unsatisfiable while also containing the lexical layer's top-k, so demanding it
# would be a gate that can never pass. The honest contract is half the budget.
half = {5: 3, 10: 5, 20: 10}
for i, k in enumerate((5, 10, 20)):
    j = {5: 0, 10: 1, 20: 2}[k]
    vec_half = run(test, "vec", half[k])
    if tbl["hybrid"][i] < max(tbl["fts"][i], vec_half):
        fails.append(f"hybrid@{k} ({tbl['hybrid'][i]}) is worse than "
                     f"max(fts@{k}={tbl['fts'][i]}, vec@{half[k]}={vec_half})")
    if ptbl["hybrid"][i] < ptbl["fts"][i]:
        fails.append(f"hybrid@{k} is worse than FTS5 alone on the disjoint subset")
    pv_half = run(tpar, "vec", half[k])
    if ptbl["hybrid"][i] < pv_half:
        fails.append(f"hybrid@{k} loses disjoint recall the vector layer had at "
                     f"half the budget ({ptbl['hybrid'][i]} < {pv_half})")
print(f"\ncontract: {CONTRACT}")
print("RESULT:", "PASS" if not fails else f"FAIL {fails}")
sys.exit(0 if not fails else 1)
