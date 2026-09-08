#!/usr/bin/env python3
"""Check 22 (H3) - documentation may not drift from the artifacts.

An external audit found two figures in the README that were typed by hand from
an earlier build report; one of them (4,138 bookmarks) came from a build that
had a defect. The recognised fix is docs-as-tests: generate the numbers from the
artifacts and fail when the committed documentation disagrees with a fresh
regeneration.

STAGED - NOT IN FORCE
---------------------
This file belongs at `harden/checks/check22_docs.py`, which is protected
(`check41_machinery.py` PROTECTED, `.claude/settings.json`), so an executor may
not install it. A human promotes it. Staged flat at `proposed/E/check22_docs.py`.

Why it changed (track E9, 2026-09-08)
-------------------------------------
`README.md` was split in two. The measured, package-time figures - 27,421 nodes,
3,928 bookmarks, 35,932 internal links - moved to `PACKAGE.md`, which is now
what `harden/gen_readme.py` writes into. `README.md` became the source-checkout
front page and carries only figures measured from `data-manifest.json`.

The in-force version of this check reads `README.md` for both jobs. After the
split that is wrong in two directions at once, and both are false results:

  * the figures H3 exists to police are no longer in the file H3 opens, so H3
    would pass over `PACKAGE.md` without reading it - green for the wrong
    reason;
  * the two figures the new `README.md` does carry, 338,348,579 and 29, come
    from `data-manifest.json`, which is not in `FACTS.json`, so H3 would report
    `README states figures nothing measured` - a false red.

So the figure test is applied to each document against the source that measures
it, and the required-statement test stays on `README.md`, which is where a
reader lands and where `check19_package.py` (G16d) also looks.

What did NOT change, deliberately
---------------------------------
The regeneration-identity test, the `\\b\\d[\\d,]{2,}\\b` pattern and its
three-digit floor, and the required-statement list are untouched. Lowering the
floor is a real defect (`AUDIT-rev12.md` finding 1: the ledger counts that drifted
are one and two digits and sit under it) and it is a separate change with its own
blast radius; making it here would mean shipping two untested changes to the
documentation gate at once. Proposed, not applied.

**Not exercised.** `harden/gen_readme.py` opens `emitters/obc.sqlite` and the two
built PDFs. All 29 files in `data-manifest.json` are absent from a git checkout,
so this check cannot be run where it was written - `subprocess.run(..., check=True)`
raises `CalledProcessError` before the first assertion. It is reviewed, not
verified, and the first run with data is its first run.
"""
import sys, os, subprocess, json, tempfile, shutil, re
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from lib.canon import text, contains
_PKG = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))

PKG = os.environ.get("OBC_PKG", _PKG)
GEN = os.environ.get("OBC_GEN", os.path.join(_PKG, "harden/gen_readme.py"))
fails = []

# read BOTH documents before regenerating: gen_readme.py rewrites PACKAGE.md
package_before = open(f"{PKG}/PACKAGE.md", encoding="utf-8").read()
readme_before = open(f"{PKG}/README.md", encoding="utf-8").read()
facts_before = json.load(open(f"{PKG}/FACTS.json"))
subprocess.run([sys.executable, GEN, PKG], capture_output=True, check=True)
facts_after = json.load(open(f"{PKG}/FACTS.json"))
if facts_before != facts_after:
    diff = {k: (facts_before.get(k), facts_after.get(k))
            for k in set(facts_before) | set(facts_after)
            if facts_before.get(k) != facts_after.get(k)}
    fails.append(f"FACTS.json drifted: {list(diff)[:4]}")
print(f"FACTS.json regenerates identically: {facts_before == facts_after}")

# ---------------------------------------------------------------------------
# every number a document states must appear in the source that measures it
# ---------------------------------------------------------------------------
def _digits(obj):
    return set(re.findall(r"\d+", json.dumps(obj)))

def norm(n):
    return n.replace(",", "")

measured_facts = _digits(facts_after)
measured_manifest = _digits(json.load(open(f"{PKG}/data-manifest.json")))

# years, publication numbers, standard numbers and algorithm names are prose,
# not measurements
PROSE = {"2024", "2025", "8493", "301880", "301881", "163", "256", "512",
         "20170501121", "191", "2261", "1992",
         # README.md quotes harden/checks/check40_dataintegrity.py's docstring
         # on the Git-LFS-pointer hazard: a "~130-byte" stub, and a ratio over
         # zero denominators that "reports 100%". Both are prose about a failure
         # mode, not measurements of this build.
         "130", "100"}

def figures(doc, body, measured, where):
    nums = set(re.findall(r"\b\d[\d,]{2,}\b", body))
    unbacked = sorted(n for n in nums
                      if norm(n) not in measured and len(norm(n)) > 2
                      and norm(n) not in PROSE)
    print(f"{doc} figures not present in {where}: {len(unbacked)} {unbacked[:6]}")
    if unbacked:
        fails.append(f"{doc} states figures nothing measured: {unbacked[:5]}")

# PACKAGE.md is generated from the artifacts; FACTS.json is the same measurement
figures("PACKAGE.md", package_before, measured_facts, "the measured facts")
# README.md describes the source checkout; its figures come from the data
# manifest. Package figures are allowed too - both sources are measured - but a
# figure in neither is typed, which is what R9 forbids.
figures("README.md", readme_before, measured_manifest | measured_facts,
        "data-manifest.json or the measured facts")

# ---------------------------------------------------------------------------
# the claims that must always be present, compared canonically
# ---------------------------------------------------------------------------
# These stay on README.md. verify/emitters/checks/check19_package.py (G16d)
# asserts the same set plus "E4" against README.md, so the two gates must agree
# on which file carries them; if this list ever moves to PACKAGE.md, that check
# moves with it or G16d goes red on its own.
REQUIRED = ("Unofficial", "free of charge", "King's Printer",
            "HANDOFF REQUIRED", "current to")
for phrase in REQUIRED:
    if not contains(readme_before, phrase, casefold=True):
        fails.append(f"README lost the required statement: {phrase!r}")
print("required statements present:",
      sum(1 for p in REQUIRED if contains(readme_before, p, casefold=True)),
      f"of {len(REQUIRED)}")
print("RESULT:", "PASS" if not fails else f"FAIL {fails}")
sys.exit(0 if not fails else 1)
