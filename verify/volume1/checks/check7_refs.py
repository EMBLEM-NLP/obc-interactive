#!/usr/bin/env python3
"""Check 7 - reference resolution: the Phase 4 gate.

Every citation carries a reason code. Only 'parse-failure' is a defect;
external volumes and clauses absent from this edition are facts about the
source, not bugs. The gate fails if anything is unclassified.
"""
import sys, os
import gzip, json, random, re
from collections import Counter

nodes = {}
for line in gzip.open("out/docgraph.jsonl.gz", "rt"):
    r = json.loads(line)
    if not r.get("_meta"):
        nodes[r["id"]] = r

EXTERNAL = ("Volume 2",)
SOURCE = ("not-in-this-edition", "not-in-Table-1.3.1.2", "figure asset",
          "compliance-alternative row")
cat = Counter()
resolved = total = 0
for n in nodes.values():
    for r in n.get("refs", []):
        total += 1
        if r["target"]:
            resolved += 1
            cat["resolved"] += 1
        elif any(e in (r["why"] or "") for e in EXTERNAL):
            cat["external (Volume 2)"] += 1
        elif r["why"] in SOURCE:
            cat[f"source: {r['why']}"] += 1
        else:
            cat[f"PARSE FAILURE: {r['why']}"] += 1
terms = sum(len(n.get("terms", [])) for n in nodes.values())
print(f"citations           : {total}")
print(f"resolved to a node  : {resolved}  ({100*resolved/total:.1f}%)")
for k, v in cat.most_common():
    print(f"   {v:>6}  {k}")
print(f"defined-term links  : {terms}")

# spot check: does the target actually carry the cited number?
random.seed(3)
pool = [(n, r) for n in nodes.values() for r in n.get("refs", [])
        if r["target"] and r["kind"] in ("code_ref", "cap_ref", "act_ref")]
bad = 0
for n, r in random.sample(pool, 200):
    t = nodes[r["target"]]
    num = re.sub(r"[.\-\s]", "", (t.get("number") or "")).upper()
    cited = re.sub(r"[.\-\s]", "", r["text"]).upper()
    if num and num not in cited and not cited.startswith(num[:4]):
        anc = re.sub(r"[.\-\s]", "", (nodes.get(t["parent"], {}).get("number") or "")).upper()
        if not (anc and anc in cited):
            bad += 1
print(f"spot check (200)    : target number consistent with the citation in {200-bad}/200")
fail = sum(v for k, v in cat.items() if k.startswith("PARSE FAILURE"))
print("RESULT:", "PASS" if fail == 0 and bad <= 4 else "REVIEW")
sys.exit(0 if (fail == 0 and bad <= 4) else 1)
