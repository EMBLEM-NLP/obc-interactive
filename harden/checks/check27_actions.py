#!/usr/bin/env python3
"""Check 27 - no link may point at a file, asserted on the PDF action dictionary.

Replaces the weaker "PyMuPDF kind 3 == 0" assertion. The control gate showed
that kind 3 means "a URI action with a file:// scheme", while a genuine /Launch
action reports as kind 5 - the same value as a legitimate cross-volume link. So
the old assertion could not see a /Launch action or a /GoToR naming a file that
is not shipped alongside.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import pymupdf
from lib.pdfactions import dead_file_links, actions
from collections import Counter
_PKG = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))

ALLOWED = ("301880_built_from_model.pdf", "301881_built_from_model.pdf")
TARGETS = [("volume 1", os.environ.get("OBC_BUILT_V1", os.path.join(_PKG, "pdf/301880_built_from_model.pdf"))),
           ("volume 2", os.environ.get("OBC_BUILT_V2", os.path.join(_PKG, "pdf/301881_built_from_model.pdf")))]
fails = []
for name, path in TARGETS:
    d = pymupdf.open(path)
    kinds = Counter(s for _, _, s, _ in actions(d))
    bad = dead_file_links(d, ALLOWED)
    remote = [t for _, _, s, t in actions(d) if s == "GoToR"]
    names = {t.strip("()").split("/")[-1] for t in remote}
    print(f"{name}: {dict(kinds)}")
    print(f"   links pointing at a file : {len(bad)} {bad[:2]}")
    print(f"   remote targets           : {sorted(names) or 'none'}")
    if bad:
        fails.append(f"{name}: {len(bad)} links point at a file")
    if names - set(ALLOWED):
        fails.append(f"{name}: unexpected remote targets {names - set(ALLOWED)}")
print("RESULT:", "PASS" if not fails else f"FAIL {fails}")
sys.exit(0 if not fails else 1)
