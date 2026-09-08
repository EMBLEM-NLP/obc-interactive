#!/usr/bin/env python3
"""Check 19 - the delivered package.

Unpacks the zip into a scratch directory and verifies it against its own
manifest: every file present, every checksum matching, the required deliverables
there, the PDFs openable and correctly protected, and the SQLite queryable.
A package that lists what it contains but was never opened is not verified.
"""
import sys, os, os, zipfile, hashlib, tempfile, sqlite3, shutil
import pymupdf

ZIP = os.environ.get("OBC_ZIP", "../../obc-interactive.zip")
REQUIRED = [
    "obc-interactive/README.md",
    "obc-interactive/MANIFEST.sha256",
    "obc-interactive/pdf/301880_built_from_model_protected.pdf",
    "obc-interactive/pdf/301881_built_from_model_protected.pdf",
    "obc-interactive/pdf/301880_built_from_model.pdf",
    "obc-interactive/pdf/301881_built_from_model.pdf",
    "obc-interactive/emitters/obc.sqlite",
    "obc-interactive/emitters/markdown.tar.gz",
    "obc-interactive/emitters/html.tar.gz",
    "obc-interactive/model/docgraph-merged.jsonl.gz",
    "obc-interactive/gates/GATES-volume1.md",
    "obc-interactive/gates/GATES-volume2.md",
    "obc-interactive/gates/GATES-emitters.md",
    "obc-interactive/pipeline/run.sh",
]
fails = []
if not os.path.exists(ZIP):
    print("RESULT: FAIL package missing"); sys.exit(1)
z = zipfile.ZipFile(ZIP)
bad = z.testzip()
if bad: fails.append(f"corrupt member {bad}")
names = set(z.namelist())
missing = [r for r in REQUIRED if r not in names]
print(f"members            : {len(names)}")
print(f"required present   : {len(REQUIRED)-len(missing)}/{len(REQUIRED)} {missing}")
if missing: fails.append(f"missing: {missing}")

tmp = tempfile.mkdtemp()
z.extractall(tmp)
root = os.path.join(tmp, "obc-interactive")
man = {}
for line in open(os.path.join(root, "MANIFEST.sha256")):
    if line.startswith("#") or not line.strip():
        continue                      # the manifest carries a column header
    h, sz, rel = line.split(None, 2)
    man[rel.strip()] = (h, int(sz))
mismatch = []
for rel, (h, sz) in man.items():
    p = os.path.join(root, rel)
    if not os.path.exists(p):
        mismatch.append((rel, "absent")); continue
    if rel == "MANIFEST.sha256":
        continue
    got = hashlib.sha256(open(p, "rb").read()).hexdigest()
    if got != h: mismatch.append((rel, "checksum"))
print(f"manifest entries   : {len(man)}, mismatched {len(mismatch)} {mismatch[:3]}")
if mismatch: fails.append(f"{len(mismatch)} manifest mismatches")

for f, pages in (("301880_built_from_model_protected.pdf", 1260),
                 ("301881_built_from_model_protected.pdf", 1001)):
    d = pymupdf.open(os.path.join(root, "pdf", f))
    perm = d.permissions
    ok = (d.page_count == pages and d.needs_pass == 0
          and perm & pymupdf.PDF_PERM_PRINT and not (perm & pymupdf.PDF_PERM_MODIFY))
    links = sum(len(p.get_links()) for p in d)
    print(f"   {f}: {d.page_count} pages, {links} links, opens free={d.needs_pass==0}")
    if not ok: fails.append(f"{f} wrong page count or permissions")
    if links < 4000: fails.append(f"{f} has too few links")

db = sqlite3.connect(os.path.join(root, "emitters", "obc.sqlite"))
n = db.execute("SELECT count(*) FROM node").fetchone()[0]
hits = db.execute("SELECT count(*) FROM node_fts WHERE node_fts MATCH 'fire'").fetchone()[0]
meta = dict(db.execute("SELECT key,value FROM meta").fetchall())
print(f"   obc.sqlite: {n} nodes, FTS 'fire' {hits} hits, current_to {meta.get('current_to')}")
if n != 27421: fails.append("sqlite node count wrong")
if not hits: fails.append("sqlite FTS returned nothing")
if "free of charge" not in (meta.get("licence") or ""): fails.append("licence missing from sqlite")

# normalise whitespace: the licence sentence wraps across a line, and matching
# the raw text tests the line width rather than whether the term is stated.
# Tenth time a check in this suite has failed on its own formatting assumption.
import re as _re
readme = _re.sub(r"\s+", " ", open(os.path.join(root, "README.md"), encoding="utf-8").read())
for phrase in ("Unofficial", "free of charge", "King's Printer", "HANDOFF REQUIRED", "E4"):
    if phrase not in readme: fails.append(f"README missing '{phrase}'")
print(f"   README states the abandoned gate: {'E4' in readme and 'HANDOFF' in readme}")
shutil.rmtree(tmp)
print(f"   zip {os.path.getsize(ZIP)/1e6:.0f} MB")
print("RESULT:", "PASS" if not fails else f"FAIL {fails}")
sys.exit(0 if not fails else 1)
