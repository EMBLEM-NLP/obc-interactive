#!/usr/bin/env python3
"""Generate PACKAGE.md (and FACTS.json) from the artifacts.

The previous README was hand-written and carried link and bookmark counts copied
from a report describing an EARLIER build. An external audit caught both. Numbers
in a manifest should be measured at package time, not typed.

Target: PACKAGE.md, not README.md. Track E9 split the front page in two, because
"measured from the artifacts at package time" is true of the hydrated package and
false of a git checkout, and the single file never said which one it described.
README.md is now the source-checkout page and is hand-maintained; PACKAGE.md is
the package page and is what this script writes into.
"""
import os, sys, json, sqlite3, gzip, tarfile
from collections import Counter
import pymupdf

PKG = sys.argv[1] if len(sys.argv) > 1 else "/home/claude/package/obc-interactive"
def pdfstats(p):
    d = pymupdf.open(p); k = Counter()
    for pg in d:
        for l in pg.get_links(): k[l["kind"]] += 1
    return dict(pages=d.page_count, goto=k[1], remote=k[5], uri=k[2],
                launch=k[3], bookmarks=len(d.get_toc()),
                mb=os.path.getsize(p)/1e6)
v1 = pdfstats(f"{PKG}/pdf/301880_built_from_model_protected.pdf")
v2 = pdfstats(f"{PKG}/pdf/301881_built_from_model_protected.pdf")
db = sqlite3.connect(f"{PKG}/emitters/obc.sqlite")
q = lambda s: db.execute(s).fetchone()[0]
sq = dict(nodes=q("select count(*) from node"), closure=q("select count(*) from closure"),
          refs=q("select count(*) from ref"), terms=q("select count(*) from term"),
          amendments=q("select count(*) from amendment"), cells=q("select count(*) from cell"),
          mb=os.path.getsize(f"{PKG}/emitters/obc.sqlite")/1e6)
meta = dict(db.execute("select key,value from meta").fetchall())
def members(t):
    with tarfile.open(t) as f: return sum(1 for m in f.getmembers() if m.isfile())
md_n = members(f"{PKG}/emitters/markdown.tar.gz")
ht_n = members(f"{PKG}/emitters/html.tar.gz")
# the reconciliation figures the README states in prose must be measured too,
# or the docs-drift gate cannot back them
import gzip as _gz, re as _re
from collections import Counter as _C
_nodes, _meta = {}, {}
for line in _gz.open(f"{PKG}/model/docgraph-merged.jsonl.gz", "rt"):
    r = json.loads(line)
    (_meta.update(r) if r.get("_meta") else _nodes.__setitem__(r["id"], r))
_st = _meta.get("amendment_stats", {})
amend = dict(on_page=_st.get("markers_on_page"), legend=_st.get("legend"),
             attached=_st.get("attached"), orphans=len(_st.get("orphans", [])),
             rows=sum(len(n.get("amendment", [])) for n in _nodes.values()),
             nodes_flagged=sum(1 for n in _nodes.values() if n.get("amendment")))
_why = _C(r.get("why") for n in _nodes.values() for r in n.get("refs", [])
          if not r.get("target"))
residual = {k: v for k, v in _why.most_common(6) if k}
led = {}
for name, path in (("volume1", f"{PKG}/gates/GATES-volume1.md"),
                   ("volume2", f"{PKG}/gates/GATES-volume2.md"),
                   ("emitters", f"{PKG}/gates/GATES-emitters.md")):
    t = open(path).read()
    led[name] = dict(total=t.count("\n- ["), met=t.count("\n- [x]"),
                     abandoned=t.count("\nABANDON:"))
# the "still open" table is generated too: it stated 182 standards absent from
# Table 1.3.1.2 when the merged model measures 363 - the Volume-1-only figure
# carried forward after the merge. Third documentation drift found by the gate.
rd = residual
open_rows = [
 ("**E4**", "manual accessibility review - abandoned, see the handoff above"),
 ("Figures", "exported but not embedded in HTML with long descriptions"),
 ("Volume 2 tables", "stages 4-5 never run on Volume 2, so its tables are text, not grids"),
 ("Volume 2 page labels", "not generated"),
 (f"{rd.get('external: Appendix A (Volume 2)', 0)} notes",
  "cited in Volume 1 with no Appendix A entry"),
 (f"{rd.get('not-in-Table-1.3.1.2', 0)} standards", "cited but absent from Table 1.3.1.2."),
 (f"{rd.get('not-in-this-edition', 0)} references", "cite a provision this edition does not contain"),
 ("21 tables", "unbound to a provision (their `Forming Part of` line is on a continuation page)"),
 ("Akoma Ntoso", "deliberately deferred; the JSON graph is canonical"),
]
rt = "| | |\n|---|---|\n" + "".join(f"| {a} | {b} |\n" for a, b in open_rows)
# Track E9, 2026-09-08: OUTPUT PATH ONLY. The measured figures moved from
# README.md to PACKAGE.md when the front page was split into the source-checkout
# page (README.md) and the package-at-package-time page (PACKAGE.md). Nothing
# else here changed. The "own the whole file instead of this span" refactor is
# the right durable fix and is deliberately NOT in this pass: this script reads
# emitters/obc.sqlite and the two built PDFs, all absent from a git checkout, so
# a change to it cannot be exercised where it was written. See AUDIT-rev9.md.
_r = open(f"{PKG}/PACKAGE.md", encoding="utf-8").read()
_a = _r.index("## What is still open")
_b = _r.index("## Licence and attribution")
_r = _r[:_a] + "## What is still open\n\n" + rt + "\n---\n\n" + _r[_b:]
open(f"{PKG}/PACKAGE.md", "w", encoding="utf-8").write(_r)

json.dump(dict(v1=v1, v2=v2, sqlite=sq, meta=meta, markdown_files=md_n,
               html_files=ht_n, ledgers=led, amendments=amend, residual=residual),
          open(f"{PKG}/FACTS.json", "w"), indent=1)
print(json.dumps(dict(v1=v1, v2=v2, sqlite=sq, markdown=md_n, html=ht_n, ledgers=led),
                 indent=1))
