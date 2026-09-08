#!/usr/bin/env python3
"""Check 2 - the feasibility gate.

Two-way reconciliation between what the printed contents pages DECLARE and what
the structure detector FOUND, without using page footers to decide anything.
Each contents page owns the page range up to the next contents page; declared
numbers and detected headings are compared inside that range only.

Both directions must be clean. A declared heading that was not detected is a
detector defect. A detected heading that was never declared is either a
detector false positive or a genuine gap in the printed contents.
"""
import sys, os
import gzip, json, re
from collections import defaultdict

inv, roles = {}, {}
with gzip.open("out/inventory.jsonl.gz", "rt") as fh:
    for line in fh:
        r = json.loads(line)
        if not r.get("_meta"):
            inv[r["page"]] = r
meta = None
with gzip.open("out/roles.jsonl.gz", "rt") as fh:
    for line in fh:
        r = json.loads(line)
        if r.get("_meta"):
            meta = r
        else:
            roles[r["page"]] = r["roles"]
contents = meta["contents_pages"]

NUM = re.compile(r"^(\d+(?:\.\d+){1,4})\.?(?:\s|$)")
# trailing period optional: the source omits it in a handful of places
# ("Section 1.1 General", "9.1  General", "Section 5.5  Vapour Diffusion")
HEADROLES = {"section", "subsection", "article"}

def line_text(l):
    return "".join(s["t"] for s in l["s"]).strip()

# group contiguous contents pages into one contents block
blocks = []
for p in contents:
    if blocks and p == blocks[-1][-1] + 1:
        blocks[-1].append(p)
    else:
        blocks.append([p])

ranges = []
for i, blk in enumerate(blocks):
    end = blocks[i + 1][0] - 1 if i + 1 < len(blocks) else max(inv)
    ranges.append((blk, blk[0], end))

tot_dec = tot_det = tot_deep = 0
missing_all, extra_all = [], []
print(f"{'contents':<12}{'pages':<13}{'declared':>9}{'detected':>9}{'deeper':>8}{'missing':>8}{'extra':>7}")
for blk, lo, hi in ranges:
    declared = set()
    for p in blk:
        for b in inv[p]["blocks"]:
            for l in b["l"]:
                m = NUM.match(line_text(l))
                if m:
                    declared.add(m.group(1))
    detected = set()
    for p in range(lo, hi + 1):
        if p in blk:
            continue
        rr = roles.get(p, {})
        for bi, b in enumerate(inv[p]["blocks"]):
            for li, l in enumerate(b["l"]):
                if rr.get(f"{bi}.{li}") in HEADROLES:
                    t = line_text(l)
                    m = NUM.match(t) or re.match(r"^Section\s+(\d+(?:\.\d+){1,2})\.?(?:\s|$)", t)
                    if m:
                        detected.add(m.group(1))
    # compare like with like: the printed contents list Sections and Subsections,
    # never Articles, so only compare at depths the contents page actually declares
    depths = {d.count(".") for d in declared}
    detected_cmp = {d for d in detected if d.count(".") in depths}
    deeper = len(detected) - len(detected_cmp)
    miss = sorted(declared - detected_cmp)
    extra = sorted(detected_cmp - declared)
    tot_dec += len(declared); tot_det += len(detected_cmp); tot_deep += deeper
    missing_all += [(blk[0], m) for m in miss]
    extra_all += [(blk[0], e) for e in extra]
    print(f"p{blk[0]:<11}{f'{lo}-{hi}':<13}{len(declared):>9}{len(detected_cmp):>9}"
          f"{deeper:>8}{len(miss):>8}{len(extra):>7}")

print(f"\ntotal declared {tot_dec} | detected at the same depths {tot_det}"
      f" | detected deeper than the contents lists {tot_deep} (expected: Articles)")
print(f"declared but NOT detected : {len(missing_all)}")
for b, m in missing_all[:20]:
    print(f"    contents p{b}: {m}")
print(f"detected but NOT declared : {len(extra_all)}")
for b, e in extra_all[:20]:
    print(f"    contents p{b}: {e}")
print("RESULT:", "PASS" if not missing_all else "FAIL")
sys.exit(0 if (not missing_all) else 1)
