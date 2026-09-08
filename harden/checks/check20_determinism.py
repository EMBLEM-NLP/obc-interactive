#!/usr/bin/env python3
"""Check 20 (H1) - the build is deterministic.

Reproducible Builds practice: same inputs, byte-identical outputs. The dominant
source of nondeterminism is timestamps, addressed with SOURCE_DATE_EPOCH; the
others are hash seeding and iteration order. Verified by building twice and
comparing digests, which is the only assertion that cannot be faked.

Scope: the derived emitters, which are cheap to rebuild. PDF determinism is
asserted separately by normalising the /Info timestamps, because PyMuPDF stamps
the current time by default.
"""
import sys, os, subprocess, hashlib, shutil, tempfile, sqlite3
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import pymupdf
# Paths resolve from the package root with env-var overrides, so this check
# runs from the shipped bag. Before 2026-09-07 it hardcoded build-session
# paths and could not be re-run by anyone who received the artifact.
_PKG = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))

EMIT = os.environ.get("OBC_EMIT", os.path.join(_PKG, "pipeline/emitters"))
fails = []
env = dict(os.environ, PYTHONHASHSEED="0", SOURCE_DATE_EPOCH="1737072000", TZ="UTC")

def sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()

def build_markdown(dest):
    subprocess.run([sys.executable, "stage16_markdown.py"], cwd=EMIT, env=env,
                   capture_output=True, check=True)
    shutil.copytree(f"{EMIT}/out/markdown", dest, dirs_exist_ok=True)

tmp = tempfile.mkdtemp()
a, b = os.path.join(tmp, "a"), os.path.join(tmp, "b")
build_markdown(a)
build_markdown(b)
da = {f: sha(os.path.join(a, f)) for f in sorted(os.listdir(a))}
dbs = {f: sha(os.path.join(b, f)) for f in sorted(os.listdir(b))}
diff = [f for f in da if da[f] != dbs.get(f)]
print(f"markdown: {len(da)} files rebuilt twice, {len(diff)} differ {diff[:3]}")
if diff: fails.append(f"markdown build is not deterministic: {diff[:3]}")

# the database: same inputs must give the same content digest
def db_digest(p):
    con = sqlite3.connect(p)
    h = hashlib.sha256()
    for tbl in ("node", "ref", "term", "amendment", "closure", "cell"):
        for row in con.execute(f"select * from {tbl} order by rowid"):
            h.update(repr(row).encode())
    return h.hexdigest()
# Build first. As written, this read whatever out/obc.sqlite happened to exist
# from an earlier session and compared it to one fresh build - which crashes
# from a clean bag and, worse, would pass if the stale file came from the
# same code. Two fresh builds is what "deterministic" means.
os.makedirs(f"{EMIT}/out", exist_ok=True)
subprocess.run([sys.executable, "stage15_sqlite.py"], cwd=EMIT, env=env,
               capture_output=True, check=True)
d1 = db_digest(f"{EMIT}/out/obc.sqlite")
subprocess.run([sys.executable, "stage15_sqlite.py"], cwd=EMIT, env=env,
               capture_output=True, check=True)
d2 = db_digest(f"{EMIT}/out/obc.sqlite")
print(f"sqlite content digest: {'stable' if d1 == d2 else 'CHANGED'} ({d1[:12]})")
if d1 != d2: fails.append("sqlite content is not deterministic")
# The content digest above excludes the `meta` table - which is exactly where
# nondeterminism was found (stage15 wrote time.strftime into meta.generated,
# so a rebuild differed from the shipped file by one date string while this
# check passed). Compare the whole file, which is what "byte-identical" means.
f1 = sha(f"{EMIT}/out/obc.sqlite")
subprocess.run([sys.executable, "stage15_sqlite.py"], cwd=EMIT, env=env,
               capture_output=True, check=True)
f2 = sha(f"{EMIT}/out/obc.sqlite")
print(f"sqlite whole-file sha256: {'byte-identical' if f1 == f2 else 'DIFFERS'} ({f1[:12]})")
if f1 != f2: fails.append("sqlite file is not byte-identical across rebuilds")

# Embeddings. stage19_embed had never been run against the shipped vectors until
# 2026-09-08; when it was, it reproduced vectors_sha256 exactly on a different
# machine and a CPU-only torch build. That is a real determinism property and it
# belongs in this gate rather than in an audit note. Skipped when the embedding
# stack is absent, so the gate does not go red for a missing optional dependency.
try:
    import sentence_transformers  # noqa: F401
    _have_st = True
except ImportError:
    _have_st = False
# Re-embedding 2,749 articles takes ~4.5 minutes. This gate is run by the
# gate-complete Stop hook on every session end, so making it unconditional
# turned a ~30 s gate into a ~5 min one and blew the hook budget - the exact
# hook-timeout hazard this project was warned about. Opt in explicitly:
#   OBC_CHECK_EMBED=1  (nightly job, or before shipping a re-embed in Track B)
_deep = os.environ.get("OBC_CHECK_EMBED") == "1"
if _deep and _have_st and os.path.exists(f"{_PKG}/emitters/obc-vec.sqlite"):
    import sqlite3, tempfile as _tf
    shipped = dict(sqlite3.connect(f"{_PKG}/emitters/obc-vec.sqlite")
                   .execute("select key,value from embed_meta")).get("vectors_sha256")
    out = os.path.join(_tf.mkdtemp(), "vec.sqlite")
    r = subprocess.run([sys.executable, f"{_PKG}/retrieval/stage19_embed.py",
                        "--db", f"{_PKG}/emitters/obc.sqlite", "--out", out],
                       capture_output=True, text=True, env=env)
    rebuilt = (dict(sqlite3.connect(out).execute("select key,value from embed_meta")).get("vectors_sha256")
               if r.returncode == 0 and os.path.exists(out) else None)
    same = shipped == rebuilt
    print(f"embeddings vectors_sha256: {'reproducible' if same else 'DIFFERS'} ({(shipped or '')[:12]})")
    if not same:
        fails.append("embeddings are not reproducible from obc.sqlite")
    shutil.rmtree(os.path.dirname(out), ignore_errors=True)
elif not _deep:
    print("embeddings vectors_sha256: not checked (set OBC_CHECK_EMBED=1; ~4.5 min)")
else:
    print("embeddings vectors_sha256: skipped (sentence-transformers not installed)")

# PDFs: two builds of the same inputs must be byte-identical. Two fixes were
# needed - SOURCE_DATE_EPOCH for the /Info timestamps, and no_new_id=True to stop
# MuPDF writing a fresh random /ID on every save.
import time as _t
want = "D:" + _t.strftime("%Y%m%d%H%M%S", _t.gmtime(int(env["SOURCE_DATE_EPOCH"]))) + "Z"
for name, p in (("v1", os.environ.get("OBC_BUILT_V1", os.path.join(_PKG, "pdf/301880_built_from_model.pdf"))),
                ("v2", os.environ.get("OBC_BUILT_V2", os.path.join(_PKG, "pdf/301881_built_from_model.pdf")))):
    m = pymupdf.open(p).metadata
    ok = m.get("creationDate") == want and m.get("modDate") == want
    print(f"pdf {name} timestamps: {m.get('creationDate')} "
          f"-> {'from SOURCE_DATE_EPOCH' if ok else 'NOT NORMALISED (want ' + want + ')'}")
    if not ok:
        fails.append(f"{name} timestamp is not derived from SOURCE_DATE_EPOCH")
    idb = open(p, "rb").read()
    n_id = idb.count(b"/ID[")
    if n_id and b"/ID[<" not in idb:
        fails.append(f"{name} has no stable /ID")

shutil.rmtree(tmp, ignore_errors=True)
print("RESULT:", "PASS" if not fails else f"FAIL {fails}")
sys.exit(0 if not fails else 1)
