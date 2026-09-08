#!/usr/bin/env python3
"""Check 34 (R5) - negative control for the retrieval harness.

An eval harness that always reports a good number is worthless. This corrupts
the vector index in a copy - shuffling every embedding onto the wrong node - and
requires the harness to notice. If a scrambled index still scores like the real
one, the harness is measuring the lexical layer and nothing else.
"""
import sys, os, sqlite3, shutil, tempfile, json, random
import numpy as np, sqlite_vec
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from lib.hybrid import connect, fts, vec, fuse

DB = os.environ.get("OBC_DB", "out/obc-vec.sqlite")
ES = os.environ.get("OBC_EVAL", "evalset.json")
tmp = tempfile.mkdtemp()
bad = os.path.join(tmp, "scrambled.sqlite")
shutil.copy(DB, bad)
db = sqlite3.connect(bad)
db.enable_load_extension(True); sqlite_vec.load(db); db.enable_load_extension(False)
rows = db.execute("SELECT node_id, embedding FROM vec_article").fetchall()
ids = [r[0] for r in rows]; embs = [r[1] for r in rows]
random.seed(7); random.shuffle(embs)              # every vector on the wrong node
db.execute("DELETE FROM vec_article")
db.executemany("INSERT INTO vec_article(node_id, embedding) VALUES (?,?)",
               list(zip(ids, embs)))
db.commit(); db.close()

qs = [q for q in json.load(open(ES))["questions"] if q["split"] == "test"]
good, poor = connect(DB), connect(bad)
def score(conn, mode, k=5):
    hit = 0
    for q in qs:
        f, v = fts(conn, q["q"], 50), vec(conn, q["q"], 50)
        lst = (f if mode == "fts" else v if mode == "vec" else fuse(f, v, k))[:k]
        hit += q["target"] in lst
    return hit
gv, bv = score(good, "vec"), score(poor, "vec")
gh, bh = score(good, "hybrid"), score(poor, "hybrid")
gf = score(good, "fts")
print(f"{'':<22}{'real index':>12}{'scrambled':>12}")
print(f"{'vectors alone':<22}{gv:>12}{bv:>12}")
print(f"{'hybrid':<22}{gh:>12}{bh:>12}")
print(f"{'fts5 (unaffected)':<22}{gf:>12}{gf:>12}")
fails = []
if bv >= gv:
    fails.append(f"a scrambled index scores as well as the real one on vectors "
                 f"({bv} vs {gv}) - the harness is not measuring the vectors")
if bv > len(qs) * 0.15:
    fails.append(f"a scrambled index still scores {bv}/{len(qs)} - suspiciously high")
if bh >= gh:
    fails.append(f"hybrid is unaffected by scrambling the vectors ({bh} vs {gh}) "
                 f"- the vector layer contributes nothing to fusion")
shutil.rmtree(tmp, ignore_errors=True)
print("RESULT:", "PASS" if not fails else f"FAIL {fails}")
sys.exit(0 if not fails else 1)
