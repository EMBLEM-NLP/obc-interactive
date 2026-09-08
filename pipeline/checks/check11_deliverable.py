#!/usr/bin/env python3
"""Check 11 - the shipped artifact itself.

Everything else measures the model or the unencrypted build. This opens the file
that is actually delivered and confirms it is usable and correctly protected.
"""
import sys, os, pymupdf
from collections import Counter
# Paths resolve from the package root with env-var overrides, so this check
# runs from the shipped bag. Before 2026-09-07 it hardcoded build-session
# paths and could not be re-run by anyone who received the artifact.
_PKG = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))

P = os.environ.get("OBC_PROTECTED", os.path.join(_PKG, "pdf/301880_built_from_model_protected.pdf"))
U = os.environ.get("OBC_BUILT_V1", os.path.join(_PKG, "pdf/301880_built_from_model.pdf"))
fails = []
if not os.path.exists(P): fails.append("protected deliverable missing")
if not os.path.exists(U): fails.append("unencrypted master missing")
if fails:
    print("RESULT: FAIL", fails); sys.exit(1)
d = pymupdf.open(P)
k = Counter()
for p in d:
    for l in p.get_links():
        k[l["kind"]] += 1
perm = d.permissions
checks = {
    "1260 pages": d.page_count == 1260,
    "opens without a password": d.needs_pass == 0,
    "printing allowed": bool(perm & pymupdf.PDF_PERM_PRINT),
    "copying allowed": bool(perm & pymupdf.PDF_PERM_COPY),
    "content changes disallowed": not (perm & pymupdf.PDF_PERM_MODIFY),
    "no dead Launch links": k[3] == 0,
    "internal links >= 30000": k[1] >= 30000,
    "web links >= 437": k[2] >= 437,
    "bookmarks >= 3500": len(d.get_toc()) >= 3500,
    "page labels present": d[985].get_label() == "Div B Part 9, 276",
    "text still extractable": "Plain and Reinforced Masonry" in d[542].get_text(),
}
for name, ok in checks.items():
    print(f"   {'ok ' if ok else 'FAIL'}  {name}")
    if not ok: fails.append(name)
print(f"   size {os.path.getsize(P)/1e6:.1f} MB | GoTo {k[1]} URI {k[2]} Launch {k[3]}")
print("RESULT:", "PASS" if not fails else f"FAIL {fails}")
sys.exit(0 if not fails else 1)
