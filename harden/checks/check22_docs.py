#!/usr/bin/env python3
"""Check 22 (H3) - documentation may not drift from the artifacts.

An external audit found two figures in the README that were typed by hand from
an earlier build report; one of them (4,138 bookmarks) came from a build that
had a defect. The recognised fix is docs-as-tests: generate the numbers from the
artifacts and fail when the committed documentation disagrees with a fresh
regeneration.
"""
import sys, os, subprocess, json, tempfile, shutil, re
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from lib.canon import text, contains
_PKG = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))

PKG = os.environ.get("OBC_PKG", _PKG)
GEN = os.environ.get("OBC_GEN", os.path.join(_PKG, "harden/gen_readme.py"))
fails = []

before = open(f"{PKG}/README.md", encoding="utf-8").read()
facts_before = json.load(open(f"{PKG}/FACTS.json"))
subprocess.run([sys.executable, GEN, PKG], capture_output=True, check=True)
facts_after = json.load(open(f"{PKG}/FACTS.json"))
if facts_before != facts_after:
    diff = {k: (facts_before.get(k), facts_after.get(k))
            for k in set(facts_before) | set(facts_after)
            if facts_before.get(k) != facts_after.get(k)}
    fails.append(f"FACTS.json drifted: {list(diff)[:4]}")
print(f"FACTS.json regenerates identically: {facts_before == facts_after}")

# every number the README states must appear in the measured facts
flat = json.dumps(facts_after)
nums = set(re.findall(r"\b\d[\d,]{2,}\b", before))
measured = {str(v) for v in re.findall(r"\d+", flat)}
def norm(n): return n.replace(",", "")
unbacked = sorted(n for n in nums if norm(n) not in measured and len(norm(n)) > 2)
# page numbers and years are legitimately prose
# years, publication numbers, standard numbers and algorithm names are prose,
# not measurements
PROSE = {"2024", "2025", "8493", "301880", "301881", "163", "256", "512",
         "20170501121", "191", "2261", "1992"}
unbacked = [n for n in unbacked if norm(n) not in PROSE]
print(f"README figures not present in the measured facts: {len(unbacked)} {unbacked[:6]}")
if unbacked:
    fails.append(f"README states figures nothing measured: {unbacked[:5]}")

# the claims that must always be present, compared canonically
for phrase in ("Unofficial", "free of charge", "King's Printer",
               "HANDOFF REQUIRED", "current to"):
    if not contains(before, phrase, casefold=True):
        fails.append(f"README lost the required statement: {phrase!r}")
print("required statements present:",
      sum(1 for p in ("Unofficial", "free of charge", "King's Printer",
                      "HANDOFF REQUIRED", "current to")
          if contains(before, p, casefold=True)), "of 5")
print("RESULT:", "PASS" if not fails else f"FAIL {fails}")
sys.exit(0 if not fails else 1)
