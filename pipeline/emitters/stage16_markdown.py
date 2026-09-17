#!/usr/bin/env python3
"""Emitter 2 - Markdown, one file per Part, doubling as the RAG source.

Structural containment and table binding are separate. Tables remain physical
children of the Part in the canonical tree; a table with ``forms_part_of`` is
rendered immediately after its bound provision and skipped at its structural
Part position. Unbound tables still render at their physical location.
"""
import os, sys, json, re, time, html
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from emit_common import (load_graph, permalink, anchor, node_text, designator,
                         breadcrumb, CURRENT_TO, CURRENT_TO_ISO, THROUGH,
                         NOTICE, COPYRIGHT, LICENCE, VOLUME_FILE)

OUTDIR = "out/markdown"
os.makedirs(OUTDIR, exist_ok=True)
t0 = time.time()
nodes, order, meta = load_graph()
kids = {nid: nodes[nid]["children"] for nid in order}

# Semantic table placement. Canonical containment stays physical; this lookup is
# purely an emitter projection from the explicit forms_part_of relation.
bound_tables = {}
for tid in order:
    t = nodes[tid]
    if t.get("type") != "table" or not t.get("forms_part_of"):
        continue
    targets = t["forms_part_of"] if isinstance(t["forms_part_of"], list) else [t["forms_part_of"]]
    for target in targets:
        if target in nodes:
            bound_tables.setdefault(target, []).append(tid)
bound_ids = {tid for tids in bound_tables.values() for tid in tids}

HEAD_LEVEL = {"division": 1, "part": 1, "appendix": 1,
              "supplementary_standard": 1, "act": 1,
              "section": 2, "subsection": 3, "article": 4,
              "act_section": 2, "note": 2}
MARKER = {"sentence", "clause", "subclause",
          "act_subsection", "act_clause", "act_subclause"}
INDENT = {"sentence": 0, "act_subsection": 0,
          "clause": 1, "act_clause": 1, "subclause": 2, "act_subclause": 2}


def ref_links(n):
    seen, out = set(), []
    for r in n.get("refs", []):
        t = r.get("target")
        if not t or t in seen or t not in nodes:
            continue
        seen.add(t)
        tv = nodes[t].get("volume", 1)
        nv = n.get("volume", 1)
        target = f"{permalink(t)}" if tv == nv else f"../v{tv}/{permalink(t)}"
        out.append(f"[{r['text'].strip()}](#{anchor(t)})" if tv == nv
                   else f"[{r['text'].strip()}]({target})")
    return out


def table_html(n):
    grid = n.get("grid") or []
    if not grid:
        return ""
    pages = sorted({c["page"] for c in grid})
    rows = {}
    for c in grid:
        rows.setdefault((c["page"], c["r"]), []).append(c)
    out = [f'<table id="{anchor(n["id"])}">',
           f'  <caption>{html.escape(designator(n))} '
           f'{html.escape(n.get("heading") or "")}'
           f'{" (continues across pages " + ", ".join(map(str,pages)) + ")" if len(pages)>1 else ""}'
           f'</caption>']
    first = True
    for key in sorted(rows):
        cells = sorted(rows[key], key=lambda c: c["c"])
        out.append("  <tr>")
        for c in cells:
            tag = "th" if first else "td"
            attrs = ""
            if c["rowspan"] > 1: attrs += f' rowspan="{c["rowspan"]}"'
            if c["colspan"] > 1: attrs += f' colspan="{c["colspan"]}"'
            if first: attrs += ' scope="col"'
            out.append(f"    <{tag}{attrs}>{html.escape(c['text'])}</{tag}>")
        out.append("  </tr>")
        first = False
    out.append("</table>")
    return "\n".join(out)


def emit_bound_tables(nid, buf):
    for tid in bound_tables.get(nid, []):
        buf.append("")
        buf.append(table_html(nodes[tid]))
        buf.append("")


SKIP = {"contents"}

def render(nid, buf, depth=0):
    n = nodes[nid]
    t, num = n["type"], designator(n)
    if t in SKIP:
        return
    head = (n.get("heading") or "").strip()
    body = node_text(n)
    if not head and t in HEAD_LEVEL and n.get("text"):
        first = n["text"][0]["t"].strip()
        if 0 < len(first) <= 80 and not re.match(r"^\(", first) and first[-1] not in ".;:":
            head = first
            body = " ".join(x["t"] for x in n["text"][1:]).strip()
    if t == "table":
        # Bound tables are rendered at their semantic target, not again as a
        # physical child of the Part. Unbound tables retain structural output.
        if nid not in bound_ids:
            buf.append("")
            buf.append(table_html(n))
            buf.append("")
        return
    if t in HEAD_LEVEL:
        lvl = min(6, HEAD_LEVEL[t] + 1)
        buf.append("")
        buf.append(f'{"#"*lvl} {num} {head}'.rstrip()
                   + f' <a id="{anchor(nid)}"></a>')
        amd = n.get("amendment") or []
        if amd:
            for a in amd:
                buf.append(f"> **Amended** — {a['kind']}"
                           + (f" (O. Reg. {a['instrument']})" if a.get("instrument") else "")
                           + f", in force {a['effective']}.")
        if body:
            buf.append("")
            buf.append(body)
    elif t in MARKER:
        pad = "    " * INDENT.get(t, 0)
        buf.append(f'{pad}{num} {body}'.rstrip())
    elif body:
        buf.append("")
        buf.append(body)
    links = ref_links(n)
    if links and t in HEAD_LEVEL:
        buf.append("")
        buf.append("*Refers to:* " + "; ".join(links[:12]))

    # The printed binding is semantic placement. Emit it after the bound
    # provision's own text/citation line and before descendant provisions.
    emit_bound_tables(nid, buf)
    for c in kids.get(nid, []):
        render(c, buf, depth + 1)

roots = [nid for nid in order if not nodes[nid].get("parent")]
targets = []
for r in roots:
    n = nodes[r]
    if n["type"] in ("division",):
        targets += [c for c in kids[r]]
    else:
        targets.append(r)

files = 0
sys.setrecursionlimit(20000)
for nid in targets:
    n = nodes[nid]
    vol = n.get("volume", 1)
    slug = permalink(nid).replace("/", "_") or nid
    path = f"{OUTDIR}/v{vol}_{slug}.md"
    title = (designator(n) + " " + (n.get("heading") or "")).strip() or nid
    if n["type"] == "part":
        title = f"Division {nid.split('/')[0]} — Part {n['number']}"
    fm = {
        "id": nid, "permalink": permalink(nid), "volume": vol,
        "type": n["type"], "title": title,
        "current_to": CURRENT_TO_ISO, "through": THROUGH,
        "source": VOLUME_FILE.get(vol),
        "notice": NOTICE, "copyright": COPYRIGHT, "licence": LICENCE,
    }
    buf = ["---"]
    for k, v in fm.items():
        buf.append(f"{k}: " + json.dumps(v, ensure_ascii=False))
    buf.append("---")
    buf.append("")
    buf.append(f"# {title}")
    buf.append("")
    buf.append(f"> {NOTICE}")
    render(nid, buf)
    buf.append("")
    buf.append("---")
    buf.append("")
    buf.append(COPYRIGHT)
    buf.append("")
    buf.append(LICENCE)
    open(path, "w", encoding="utf-8").write("\n".join(buf) + "\n")
    files += 1

size = sum(os.path.getsize(f"{OUTDIR}/{f}") for f in os.listdir(OUTDIR))
print(f"markdown files {files} | bound tables {len(bound_ids)} | {size/1e6:.1f} MB | {time.time()-t0:.0f}s -> {OUTDIR}")
