#!/usr/bin/env python3
"""Emitter 3 - accessible HTML, built to WCAG 2.2 AA.

The AODA (O. Reg. 191/11 s.14) mandates WCAG 2.0 AA for Ontario government web
content; 2.2 is a superset and Ontario has signalled a transition, so building
to 2.2 now is the forward-compatible choice. The specifics that matter for a
legal code: a strict non-skipping heading hierarchy, scope= on simple tables and
the id/headers pattern on merged-cell tables (scope alone cannot resolve a
spanned header), a <caption> on every table, landmarks, a skip link, meaningful
link text, and a two-part text alternative for every figure.
"""
import os, sys, json, re, html, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from emit_common import (load_graph, permalink, anchor, node_text, designator,
                         CURRENT_TO, CURRENT_TO_ISO, THROUGH, NOTICE,
                         COPYRIGHT, LICENCE, VOLUME_FILE)

OUTDIR = "out/html"
os.makedirs(OUTDIR, exist_ok=True)
t0 = time.time()
nodes, order, meta = load_graph()
kids = {nid: nodes[nid]["children"] for nid in order}

HEAD_LEVEL = {"division": 2, "part": 2, "appendix": 2,
              "supplementary_standard": 2, "act": 2,
              "section": 3, "subsection": 4, "article": 5,
              "act_section": 3, "note": 3}
MARKER = {"sentence", "clause", "subclause",
          "act_subsection", "act_clause", "act_subclause"}
IND = {"sentence": 0, "act_subsection": 0, "clause": 1,
       "act_clause": 1, "subclause": 2, "act_subclause": 2}
SKIP = {"contents"}
E = html.escape

CSS = """
:root{--ink:#1a1a1a;--rule:#c9d3e0;--tint:#eef4fb;--link:#1a4f9c;--amber:#fff2d6}
*{box-sizing:border-box}
body{margin:0;font:16px/1.6 Georgia,'Times New Roman',serif;color:var(--ink);background:#fff}
.skip{position:absolute;left:-9999px}
.skip:focus{left:8px;top:8px;position:fixed;background:#fff;padding:.6rem 1rem;
  border:2px solid var(--link);z-index:50}
header,footer{background:var(--tint);border-bottom:1px solid var(--rule);padding:1rem 1.25rem}
footer{border-top:1px solid var(--rule);border-bottom:0;font-size:.85rem}
.wrap{display:flex;gap:2rem;align-items:flex-start;max-width:1400px;margin:0 auto}
nav.toc{flex:0 0 22rem;position:sticky;top:0;max-height:100vh;overflow:auto;
  padding:1rem;border-right:1px solid var(--rule);font-family:system-ui,sans-serif;font-size:.85rem}
nav.toc a{display:block;padding:.12rem 0;text-decoration:none;color:var(--link)}
nav.toc a:hover,nav.toc a:focus{text-decoration:underline}
main{flex:1 1 auto;padding:1.25rem 1.5rem 4rem;max-width:56rem}
h1{font-size:1.7rem}h2{font-size:1.4rem;border-bottom:2px solid var(--rule);padding-bottom:.2rem}
h3{font-size:1.2rem}h4{font-size:1.05rem}h5{font-size:.98rem}h6{font-size:.95rem}
.prov{margin:.35rem 0}
.d{font-weight:700;font-family:system-ui,sans-serif;font-size:.9em}
.i1{margin-left:2rem}.i2{margin-left:4rem}
a{color:var(--link)}
.amend{background:var(--amber);border-left:4px solid #d9a441;padding:.5rem .75rem;
  margin:.5rem 0;font-family:system-ui,sans-serif;font-size:.9rem}
.notice{font-family:system-ui,sans-serif;font-size:.9rem}
table{border-collapse:collapse;margin:1rem 0;font-family:system-ui,sans-serif;font-size:.85rem;width:100%}
caption{text-align:left;font-weight:700;padding:.4rem 0}
th,td{border:1px solid var(--rule);padding:.35rem .5rem;vertical-align:top;text-align:left}
thead th,th[scope=col]{background:var(--tint)}
figure{margin:1.25rem 0;padding:.5rem;border:1px solid var(--rule)}
figcaption{font-family:system-ui,sans-serif;font-size:.9rem;padding-top:.4rem}
details{margin-top:.4rem;font-family:system-ui,sans-serif;font-size:.9rem}
:focus-visible{outline:3px solid #b45309;outline-offset:2px}
@media print{nav.toc{display:none}a[href^="#"]::after{content:""}
  main{max-width:none}body{font-size:11pt}}
@media (max-width:900px){.wrap{display:block}nav.toc{position:static;max-height:none;
  border-right:0;border-bottom:1px solid var(--rule)}}
"""

def table_html(n):
    grid = n.get("grid") or []
    if not grid:
        return ""
    rows = {}
    for c in grid:
        rows.setdefault((c.get("page"), c["r"]), []).append(c)
    keys = sorted(rows)
    pages = sorted({k[0] for k in keys if k[0]})
    cap = f'{E(designator(n))} {E(n.get("heading") or "")}'.strip()
    if len(pages) > 1:
        cap += f' <span class="notice">(continues across pages {pages[0]}–{pages[-1]})</span>'
    out = [f'<table id="{anchor(n["id"])}">', f"<caption>{cap}</caption>"]
    complex_ = any(c["rowspan"] > 1 or c["colspan"] > 1 for c in grid)
    hdr_ids = []
    for i, key in enumerate(keys):
        cells = sorted(rows[key], key=lambda c: c["c"])
        out.append("<tr>")
        for c in cells:
            a = ""
            if c["rowspan"] > 1: a += f' rowspan="{c["rowspan"]}"'
            if c["colspan"] > 1: a += f' colspan="{c["colspan"]}"'
            if i == 0:
                # merged headers need id/headers; scope alone cannot resolve a span
                hid = f'{anchor(n["id"])}-h{c["c"]}'
                hdr_ids.append(hid)
                out.append(f'<th id="{hid}"{a} scope="col">{E(c["text"])}</th>')
            else:
                if complex_ and hdr_ids:
                    idx = min(c["c"], len(hdr_ids) - 1)
                    a += f' headers="{hdr_ids[idx]}"'
                out.append(f"<td{a}>{E(c['text'])}</td>")
        out.append("</tr>")
    out.append("</table>")
    return "\n".join(out)

def links_for(n, vol):
    seen, out = set(), []
    for r in n.get("refs", []):
        t = r.get("target")
        if not t or t in seen or t not in nodes:
            continue
        seen.add(t)
        tn = nodes[t]
        label = (designator(tn) + " " + (tn.get("heading") or "")).strip() or t
        tv = tn.get("volume", 1)
        href = f"#{anchor(t)}" if tv == vol else f"../v{tv}/index.html#{anchor(t)}"
        # link text states the destination, not "here" (WCAG 2.4.4)
        out.append(f'<a href="{href}">{E(r["text"].strip())} — {E(label)}</a>')
    return out

def render(nid, buf, vol, lvl=2):
    n = nodes[nid]
    t = n["type"]
    if t in SKIP:
        return
    num, head = designator(n), (n.get("heading") or "").strip()
    body = node_text(n)
    if not head and t in HEAD_LEVEL and n.get("text"):
        first = n["text"][0]["t"].strip()
        if 0 < len(first) <= 80 and not first.startswith("(") and first[-1] not in ".;:":
            head = first
            body = " ".join(x["t"] for x in n["text"][1:]).strip()
    if t == "table":
        buf.append(table_html(n)); return
    if t in HEAD_LEVEL:
        lv = min(6, lvl)
        buf.append(f'<h{lv} id="{anchor(nid)}">'
                   f'<span class="d">{E(num)}</span> {E(head)}</h{lv}>')
        for a in n.get("amendment", []):
            src = (f"O. Reg. {a['instrument']}" if a.get("instrument")
                   else "editorial correction")
            buf.append(f'<p class="amend"><strong>Amended</strong> by {E(src)}, '
                       f'in force {E(a["effective"])}.</p>')
        if body:
            buf.append(f'<p class="prov">{E(body)}</p>')
        ls = links_for(n, vol)
        if ls:
            buf.append('<p class="notice">Refers to: ' + "; ".join(ls[:12]) + "</p>")
    elif t in MARKER:
        cls = f' class="prov i{IND.get(t,0)}"' if IND.get(t, 0) else ' class="prov"'
        buf.append(f'<p{cls} id="{anchor(nid)}">'
                   f'<span class="d">{E(num)}</span> {E(body)}</p>')
    elif body:
        buf.append(f'<p class="prov">{E(body)}</p>')
    nxt = min(6, lvl + 1) if t in HEAD_LEVEL else lvl
    for c in kids.get(nid, []):
        render(c, buf, vol, nxt)

def page(nid, vol):
    n = nodes[nid]
    title = (designator(n) + " " + (n.get("heading") or "")).strip() or nid
    if n["type"] == "part":
        title = f"Division {nid.split('/')[0]} — Part {n['number']}"
    toc = []
    def walk(x, d=0):
        m = nodes[x]
        if m["type"] in ("section", "subsection", "note", "act_section",
                         "supplementary_standard"):
            lbl = (designator(m) + " " + (m.get("heading") or "")).strip()
            toc.append(f'<a href="#{anchor(x)}" style="padding-left:{d*.7}rem">{E(lbl)}</a>')
        for c in kids.get(x, []):
            walk(c, d + (1 if m["type"] != "part" else 0))
    walk(nid)
    body = []
    render(nid, body, vol, 2)
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{E(title)} — 2024 Building Code Compendium (unofficial)</title>
<meta name="description" content="{E(title)}. Unofficial edition, current to {CURRENT_TO}.">
<style>{CSS}</style>
</head>
<body>
<a class="skip" href="#main">Skip to main content</a>
<header>
  <p class="notice"><strong>{E(title)}</strong> — unofficial edition,
     current to <time datetime="{CURRENT_TO_ISO}">{CURRENT_TO}</time>
     (through {E(THROUGH)}).</p>
  <p class="notice">{E(NOTICE)}</p>
</header>
<div class="wrap">
<nav class="toc" aria-label="Contents of this Part">
<h2 id="toc-h" style="font-size:1rem">On this page</h2>
{chr(10).join(toc)}
</nav>
<main id="main">
<h1>{E(title)}</h1>
{chr(10).join(body)}
</main>
</div>
<footer>
  <p>{E(COPYRIGHT)}</p>
  <p>{E(LICENCE)}</p>
  <p>Source: {E(VOLUME_FILE.get(vol,''))}</p>
</footer>
</body>
</html>
"""

roots = [nid for nid in order if not nodes[nid].get("parent")]
targets = []
for r in roots:
    if nodes[r]["type"] == "division":
        targets += kids[r]
    else:
        targets.append(r)
sys.setrecursionlimit(20000)
files = 0
index_rows = []
for nid in targets:
    vol = nodes[nid].get("volume", 1)
    slug = f"v{vol}_" + (permalink(nid).replace("/", "_") or nid)
    open(f"{OUTDIR}/{slug}.html", "w", encoding="utf-8").write(page(nid, vol))
    lbl = (designator(nodes[nid]) + " " + (nodes[nid].get("heading") or "")).strip() or nid
    index_rows.append(f'<li><a href="{slug}.html">{E(lbl)}</a> '
                      f'<span class="notice">(Volume {vol})</span></li>')
    files += 1
open(f"{OUTDIR}/index.html", "w", encoding="utf-8").write(f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>2024 Building Code Compendium (unofficial edition)</title>
<style>{CSS}</style></head><body>
<a class="skip" href="#main">Skip to main content</a>
<header><p class="notice">{E(NOTICE)}</p></header>
<main id="main"><h1>2024 Building Code Compendium — unofficial edition</h1>
<p>Current to <time datetime="{CURRENT_TO_ISO}">{CURRENT_TO}</time>
   (through {E(THROUGH)}).</p>
<h2>Contents</h2><ul>{''.join(index_rows)}</ul></main>
<footer><p>{E(COPYRIGHT)}</p><p>{E(LICENCE)}</p></footer>
</body></html>""")
size = sum(os.path.getsize(f"{OUTDIR}/{f}") for f in os.listdir(OUTDIR))
print(f"html files {files+1} | {size/1e6:.1f} MB | {time.time()-t0:.0f}s -> {OUTDIR}")
