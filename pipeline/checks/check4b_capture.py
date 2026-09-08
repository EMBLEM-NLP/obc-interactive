#!/usr/bin/env python3
"""Check 4b - text capture, measured per page.

Replaces check4_capture.py, whose metric could not fail.

What was wrong
--------------
check4 compared two corpus-wide Counters of *characters*: every character in
every node's text against every character on every body/table/figure line.
The tree carries 4,697,394 characters against 2,742,659 on the page - a 71%
surplus from index entries, the Act, notes and headings, none of which are in
body roles. So the tree has more of every letter than the page needs, and the
multiset difference stays near zero no matter what is removed.

Measured: blanking 100% of sentence text (7,667 sentences, ~1.39M characters)
left "orphaned" at 0.140%, under the 0.5% floor. PASS. The check's own comment
records it being tuned at the 1% level; it is insensitive at the 100% level.

What this does instead
----------------------
Per page: the text that nodes place on page p (every text run whose `p` is p)
against the body/table/figure lines inventory records on page p. A line is
captured if its normalised text is a substring of the page's captured text.
Orphaned characters are summed over lines that are not. This is what "capture"
means, and it cannot be satisfied by surplus text on some other page.

Floor unchanged at 0.5%, because the real defect rate on the untouched build is
what the floor was originally set against; the metric changing is the point.
"""
import sys, gzip, json, re, unicodedata
from collections import Counter, defaultdict

nodes = {}
for line in gzip.open("out/docgraph.jsonl.gz", "rt"):
    r = json.loads(line)
    if not r.get("_meta"):
        nodes[r["id"]] = r
inv, geo = {}, {}
for line in gzip.open("out/inventory.jsonl.gz", "rt"):
    r = json.loads(line)
    if not r.get("_meta"):
        inv[r["page"]] = r
for line in gzip.open("out/geometry.jsonl.gz", "rt"):
    r = json.loads(line)
    geo[r["page"]] = r

# Alphanumerics only. Substring matching is exact where the old multiset
# never cared: reconstructing "A-4.2.6.1.(1)" + "." + "Shallow Foundations"
# yields a period the page does not print, and every Appendix A note heading
# reads as orphaned. Stripping punctuation from BOTH sides makes the match
# lenient only in the direction that removes false positives; a line that
# is genuinely absent still has no alphanumeric substring to find.
norm = lambda s: re.sub(r"[^0-9A-Za-z]+", "", unicodedata.normalize("NFKC", s))

# what the tree places on each page, by page of the text run - not by node
tree_by_page = defaultdict(list)
MARKER = {"sentence", "clause", "subclause",
          "act_subsection", "act_clause", "act_subclause"}
for n in nodes.values():
    num = n.get("number") or ""
    lead = (f"({num})" if n["type"] in MARKER else num + ".") + (n.get("heading") or "")
    # A heading is captured in n["heading"], not in a text run, and a
    # subsection or section node may have no text runs of its own at all -
    # its children carry the sentences. Place the heading on the node's
    # provenance page, which is where the inventory will look for it. The
    # first version of this check credited headings only via text runs and
    # reported 456 pages of "orphaned" headings that were fully captured.
    prov = n.get("provenance") or []
    if isinstance(prov, dict):
        prov = [prov]
    # provenance is a list of {page, bbox}; the heading sits on the first
    pages = [x.get("page") for x in prov if isinstance(x, dict) and x.get("page") is not None]
    if lead.strip(".") and pages:
        tree_by_page[pages[0]].append(norm(lead))
    for t in n.get("text", []) or []:
        tree_by_page[t["p"]].append(norm(t["t"]))
tree_text = {p: "".join(v) for p, v in tree_by_page.items()}

body_chars = 0
orphan_chars = 0
orphan_lines = Counter()
for p, r in inv.items():
    captured = tree_text.get(p, "")
    for bi, b in enumerate(r["blocks"]):
        for li, l in enumerate(b["l"]):
            if geo[p]["roles"].get(f"{bi}.{li}") not in ("body", "table", "figure"):
                continue
            t = norm("".join(s["t"] for s in l["s"]))
            if len(t) < 4:
                continue
            body_chars += len(t)
            # tolerate hyphenation and line-wrap splits: accept if either half
            # of the line is present, since a line can straddle two runs
            half = len(t) // 2
            if not (t in captured or t[:half] in captured or t[half:] in captured):
                orphan_chars += len(t)
                orphan_lines[p] += 1

pct = 100 * orphan_chars / max(1, body_chars)
print(f"content chars on page  : {body_chars}")
print(f"pages with orphans     : {len(orphan_lines)}")
print(f"orphaned               : {orphan_chars}  ({pct:.3f}%)")
worst = orphan_lines.most_common(3)
if worst:
    print(f"worst pages            : {worst}")
print("RESULT:", "PASS" if pct < 0.5 else "REVIEW")
sys.exit(0 if pct < 0.5 else 1)
