#!/usr/bin/env python3
"""Check 30 (R1) - every article has a deterministic contextual embedding."""
import sys, os, sqlite3, numpy as np, subprocess, hashlib, shutil, tempfile
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import sqlite_vec
DB = os.environ.get("OBC_DB", "out/obc-vec.sqlite")
db = sqlite3.connect(DB)
db.enable_load_extension(True); sqlite_vec.load(db); db.enable_load_extension(False)
meta = dict(db.execute("select key,value from embed_meta").fetchall())
n_art = db.execute("select count(*) from node where type='article'").fetchone()[0]
n_vec = db.execute("select count(*) from vec_article").fetchone()[0]
fails = []
print(f"model            : {meta.get('model')}")
print(f"level / context  : {meta.get('level')} / {meta.get('context')}")
print(f"articles         : {n_art}")
print(f"vectors          : {n_vec}  (dim {meta.get('dim')})")
if n_vec != n_art: fails.append(f"{n_art - n_vec} articles have no vector")
missing = db.execute("""SELECT count(*) FROM node WHERE type='article'
    AND id NOT IN (SELECT node_id FROM vec_article)""").fetchone()[0]
if missing: fails.append(f"{missing} article ids absent from the index")
# vectors must be unit length, or cosine ranking is meaningless
rows = db.execute("SELECT embedding FROM vec_article LIMIT 200").fetchall()
norms = [float(np.linalg.norm(np.frombuffer(r[0], dtype=np.float32))) for r in rows]
bad = [x for x in norms if abs(x - 1.0) > 1e-3]
print(f"unit-normalised  : {len(norms)-len(bad)}/{len(norms)} sampled")
if bad: fails.append("vectors are not unit length")
# the FTS5 and trigram layers must still be present - this is an addition
for t in ("node_fts", "node_tri"):
    try:
        db.execute(f"select count(*) from {t}").fetchone()
    except Exception:
        fails.append(f"{t} was lost")
print(f"fts5 + trigram preserved: {'yes' if not fails else 'NO'}")
# determinism: re-encode a sample and compare against the stored digest
tmp = tempfile.mkdtemp()
out = os.path.join(tmp, "re.sqlite")
env = dict(os.environ, PYTHONHASHSEED="0", SOURCE_DATE_EPOCH="1737072000")
r = subprocess.run([sys.executable, "stage19_embed.py", "--out", out],
                   env=env, capture_output=True, text=True)
if r.returncode != 0:
    fails.append("re-embedding failed")
else:
    d2 = sqlite3.connect(out)
    d2.enable_load_extension(True); sqlite_vec.load(d2); d2.enable_load_extension(False)
    h2 = dict(d2.execute("select key,value from embed_meta").fetchall())["vectors_sha256"]
    same = h2 == meta.get("vectors_sha256")
    print(f"deterministic    : {same} ({meta.get('vectors_sha256','')[:16]})")
    if not same: fails.append("re-encoding produced different vectors")
shutil.rmtree(tmp, ignore_errors=True)
print("RESULT:", "PASS" if not fails else f"FAIL {fails}")
sys.exit(0 if not fails else 1)
