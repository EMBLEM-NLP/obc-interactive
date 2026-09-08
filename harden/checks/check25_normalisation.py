#!/usr/bin/env python3
"""Check 25 (H7) - assertions compare canonical forms.

Two parts. First, the canonicaliser must actually neutralise every
representation difference that broke a check in this project - these are
regression fixtures drawn from the real failures. Second, an audit of the shipped
check scripts for raw substring tests against text that a writer may have
escaped or wrapped: the pattern that produced four of the eleven defects.
"""
import sys, os, re, glob
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from lib.canon import contains, text, designator, squash
# Paths resolve from the package root with env-var overrides, so this check
# runs from the shipped bag. Before 2026-09-07 it hardcoded build-session
# paths and could not be re-run by anyone who received the artifact.
_PKG = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))

# every one of these is a real failure this project shipped and then had to fix
FIXTURES = [
    ("HTML entity escaping",      "<p>&copy; King&#x27;s Printer for Ontario, 2024</p>", "King's Printer"),
    ("line wrapping",             "available to the public free of\ncharge. Any use", "free of charge"),
    ("smart quotes",              "\u201cbuilding\u201d means a structure", '"building" means'),
    ("non-breaking space",        "Division\u00a0B \u2014 Part\u00a09", "Division B - Part 9"),
    ("unicode form (NFD)",        "Que\u0301bec fenestration", "Qu\u00e9bec fenestration"),
    ("comment header in manifest","# sha256  bytes  path", "sha256"),
    ("ligature",                  "the \ufb01rst \ufb02oor assembly", "the first floor"),
]
fails = []
print("canonicaliser regression fixtures (each one a defect this project shipped):")
for name, hay, needle in FIXTURES:
    raw = needle in hay
    can = contains(hay, needle)
    print(f"   {'ok ' if can else 'FAIL'}  {name:<28} raw={str(raw):<5} canonical={can}")
    if not can:
        fails.append(f"canonicaliser misses {name}")
    # the fixture is only meaningful if the raw test would actually have failed
    if raw and name != "comment header in manifest":
        fails.append(f"{name} is not a real fixture - the raw test already passes")

# designator equivalence, the other class
for a, b in (("9.10.16.1.", "9.10.16.1"), ("11.5.1.1.-F", "11.5.1.1-F"),
             ("SB-3", "sb3"), ("A-3.1.2.", "a-3.1.2")):
    if designator(a) != designator(b):
        fails.append(f"designator {a} != {b}")
print(f"   designator equivalence: {'ok' if not any('designator' in f for f in fails) else 'FAIL'}")

# audit the shipped checks for the pattern that caused the defects
ROOTS = [os.environ.get("OBC_CHECKS_V1", os.path.join(_PKG, "pipeline/checks")), os.environ.get("OBC_CHECKS_V2", os.path.join(_PKG, "pipeline/vol2/checks")),
         os.environ.get("OBC_CHECKS_EM", os.path.join(_PKG, "pipeline/emitters/checks")), os.path.dirname(os.path.abspath(__file__))]
RAW = re.compile(r'"[^"]{6,}"\s+in\s+\w*(?:read\(\)|text|readme|s|body|txt)\b')
suspect = []
for r in ROOTS:
    for f in glob.glob(os.path.join(r, "*.py")):
        src = open(f, encoding="utf-8").read()
        if "canon" in src or "unescape" in src or "NFKC" in src or "NFC" in src:
            continue
        for i, line in enumerate(src.splitlines(), 1):
            if RAW.search(line) and "canon" not in line:
                suspect.append(f"{os.path.basename(f)}:{i}")
print(f"raw substring assertions without normalisation: {len(suspect)} {suspect[:6]}")
if len(suspect) > 3:
    fails.append(f"{len(suspect)} unnormalised substring assertions remain")
print("RESULT:", "PASS" if not fails else f"FAIL {fails}")
sys.exit(0 if not fails else 1)
