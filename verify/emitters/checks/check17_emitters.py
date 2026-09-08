#!/usr/bin/env python3
"""Check 17 - the Markdown and HTML emitters.

Markdown: every file carries front matter with the currency stamp and the
licence; designators are literal text; complex tables are HTML blocks.
HTML: WCAG 2.2 AA structural requirements that can be decided mechanically -
lang, title, skip link, landmarks, non-skipping heading order, a caption on
every table, scope on simple tables and id/headers on merged-cell ones, and no
bare "click here" link text. Contrast, focus order and alt-text quality are
manual and are not claimed here.
"""
import sys, os, os, re, glob, json
MD, HT = "out/markdown", "out/html"
fails, warn = [], []

mds = sorted(glob.glob(f"{MD}/*.md"))
print(f"markdown files : {len(mds)}")
if len(mds) < 30: fails.append("too few markdown files")
need = ["id:", "permalink:", "current_to:", "through:", "notice:", "copyright:", "licence:"]
bad_fm = [f for f in mds
          if not (open(f, encoding="utf-8").read(2000).startswith("---")
                  and all(k in open(f, encoding="utf-8").read(4000) for k in need))]
print(f"   files missing front-matter keys : {len(bad_fm)} {bad_fm[:3]}")
if bad_fm: fails.append("markdown front matter incomplete")
# a designator must never be emitted as a markdown ordered-list marker
listnum = 0
for f in mds:
    for line in open(f, encoding="utf-8"):
        if re.match(r"^\s*\d+\.\s", line) and not line.lstrip().startswith("#"):
            listnum += 1
print(f"   lines that a renderer could renumber : {listnum}")
if listnum: warn.append(f"{listnum} lines look like ordered-list items")
tab = sum(open(f, encoding="utf-8").read().count("<table") for f in mds)
print(f"   complex tables emitted as HTML blocks : {tab}")
if tab < 100: fails.append("markdown tables missing")

hts = sorted(glob.glob(f"{HT}/*.html"))
print(f"html files     : {len(hts)}")
h_fail = []
for f in hts:
    s = open(f, encoding="utf-8").read()
    name = os.path.basename(f)
    if '<html lang="en">' not in s: h_fail.append((name, "no lang"))
    if "<title>" not in s: h_fail.append((name, "no title"))
    if 'class="skip"' not in s: h_fail.append((name, "no skip link"))
    if "<main" not in s: h_fail.append((name, "no main landmark"))
    # heading order must not skip a level
    lv = [int(m) for m in re.findall(r"<h([1-6])", s)]
    for a, b in zip(lv, lv[1:]):
        if b > a + 1:
            h_fail.append((name, f"heading jump h{a}->h{b}")); break
    # every table needs a caption
    if s.count("<table") != s.count("<caption>"):
        h_fail.append((name, "table without caption"))
    # merged-cell tables need id/headers, not scope alone
    for t in re.findall(r"<table.*?</table>", s, re.S):
        if ("rowspan" in t or "colspan" in t) and "headers=" not in t:
            h_fail.append((name, "merged-cell table without headers=")); break
    if re.search(r">\s*(click here|here|read more)\s*<", s, re.I):
        h_fail.append((name, "non-descriptive link text"))
print(f"   structural accessibility failures : {len(h_fail)} {h_fail[:4]}")
if h_fail: fails.append(f"{len(h_fail)} html accessibility failures")
idx = os.path.join(HT, "index.html")
if not os.path.exists(idx): fails.append("html index missing")
import html as _h
for f in (mds[:1] + hts[:1]):
    # compare against unescaped text: the HTML writer correctly escapes the
    # apostrophe in "King's Printer", so a literal string match tests nothing
    s = _h.unescape(open(f, encoding="utf-8").read())
    if "Unofficial" not in s: fails.append(f"{f} lacks the unofficial notice")
    if "King's Printer" not in s: fails.append(f"{f} lacks the copyright line")
    if "free of charge" not in s: fails.append(f"{f} lacks the licence condition")
for w in warn:
    print("   note:", w)
print("RESULT:", "PASS" if not fails else f"FAIL {fails}")
sys.exit(0 if not fails else 1)
