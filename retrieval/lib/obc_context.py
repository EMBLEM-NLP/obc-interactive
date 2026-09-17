#!/usr/bin/env python3
"""
obc_context.py - mandatory-context bundle assembler for the OBC document model.

The docgraph answers "what is connected to what". This answers the question the
graph exists for: "given a provision, what is the complete set of text an LLM
must see before it can reason about it correctly?"

A building-code provision is meaningless alone. 9.32.3.8.(1) is unintelligible
without: its heading, its ancestors (which scope it to Part 9 housing), the
defined terms it uses in italics, the articles it cites, the Appendix A note
attached to it, the tables that declare they form part of it, and any amendment
that changed it. This walks all of those edges and emits one citation-grounded
Markdown block, budgeted to fit a context window.

Reads emitters/obc.sqlite. No network, no embeddings, no external services.
"""

import argparse
import json
import os
import re
import sqlite3
import sys
import urllib.parse
from collections import OrderedDict

from text_projection import (
    FLAT_BODY_CHARS,
    bound_table_ids,
    owns_table as projection_owns_table,
)

DB = "obc.sqlite"

LEAF = ("sentence", "clause", "subclause",
        "act_subsection", "act_clause", "act_subclause")

REF_LABEL = OrderedDict([
    ("code_ref", "cites"),
    ("note",     "explanatory note"),
    ("std",      "referenced standard"),
    ("cap_ref",  "table/figure caption"),
    ("act_ref",  "Building Code Act"),
    ("supp",     "supplementary standard"),
])

HUB_DEPS = 50

MODALITY = [
    ("prohibition", re.compile(r"\bshall not\b|\bshall in no case\b|\bis not permitted\b", re.I)),
    ("obligation",  re.compile(r"\bshall\b|\bmust\b|\bis required to\b|\bshall be\b", re.I)),
    ("permission",  re.compile(r"\bis permitted\b|\bare permitted\b|\bmay be\b|\bmay\b", re.I)),
    ("exemption",   re.compile(r"\bneed not\b|\bis not required\b|\bexcept\b", re.I)),
]


def modality_of(text):
    for name, rx in MODALITY:
        if rx.search(text or ""):
            return name
    return "statement"


def connect(path=DB, readonly=True):
    """Open the graph. READ-ONLY by default."""
    if not readonly:
        c = sqlite3.connect(path)
        c.row_factory = sqlite3.Row
        return c
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"{path} does not exist. The derived data is not kept in git; "
            f"run: bash ci/fetch_data.sh")
    c = sqlite3.connect(f"file:{urllib.parse.quote(path)}?mode=ro", uri=True)
    c.row_factory = sqlite3.Row
    return c


# --------------------------------------------------------------------------
# resolution
# --------------------------------------------------------------------------

def resolve(c, anchor, limit=8):
    """Accept a node id, a designator like '9.32.3.8', or free text."""
    r = c.execute("SELECT * FROM node WHERE id = ?", (anchor,)).fetchone()
    if r:
        return [r]

    norm = anchor.strip().rstrip(".") + "."
    rows = c.execute(
        "SELECT * FROM node WHERE designator = ? ORDER BY volume, page", (norm,)
    ).fetchall()
    if rows:
        return rows

    q = '"' + anchor.replace('"', '""') + '"'
    try:
        rows = c.execute(
            """SELECT n.* FROM node_fts f JOIN node n ON n.rowid = f.rowid
               WHERE node_fts MATCH ?
               ORDER BY (CASE WHEN n.type IN
                          ('index_entry','index_subentry','contents') THEN 1
                         ELSE 0 END),
                        bm25(node_fts) LIMIT ?""",
            (q, limit),
        ).fetchall()
    except sqlite3.OperationalError:
        rows = []
    if rows:
        return rows

    return c.execute(
        """SELECT n.* FROM node_tri t JOIN node n ON n.id = t.id
           WHERE node_tri MATCH ? LIMIT ?""",
        (anchor, limit),
    ).fetchall()


# Compatibility public surface. The implementation now lives in
# text_projection.py and is shared with stage19_embed.py, so the assembler and
# embedder cannot silently drift on what counts as an owned table.
def owns_table(c, node_id):
    return projection_owns_table(c, node_id)


def subtree_text(c, node_id):
    """Full text of a node and its descendants, in document order."""
    rows = c.execute(
        """SELECT n.id, n.type, n.designator, n.heading, n.body, cl.depth
           FROM closure cl JOIN node n ON n.id = cl.descendant
           WHERE cl.ancestor = ?
           ORDER BY cl.depth, n.page, n.rowid""",
        (node_id,),
    ).fetchall()
    out = []
    for r in rows:
        body = (r["body"] or "").strip()
        if not body and not r["heading"]:
            continue
        flat = False
        if (len(body) > FLAT_BODY_CHARS and r["type"] in ("article", "sentence")
                and owns_table(c, r["id"])):
            body = body[:FLAT_BODY_CHARS].rstrip() + (
                f" … [{len(r['body']) - FLAT_BODY_CHARS:,} further characters "
                f"suppressed: this is the table below, flattened into prose. "
                f"Read the grid, not this.]")
            flat = True
        out.append(dict(id=r["id"], type=r["type"], designator=r["designator"],
                        heading=r["heading"], body=body, depth=r["depth"],
                        flattened=flat,
                        modality=modality_of(body) if r["type"] in LEAF else None))
    return out


def ancestors(c, node_id):
    return c.execute(
        """SELECT n.id, n.type, n.designator, n.heading, cl.depth
           FROM closure cl JOIN node n ON n.id = cl.ancestor
           WHERE cl.descendant = ? AND cl.depth > 0
           ORDER BY cl.depth DESC""",
        (node_id,),
    ).fetchall()


def scope_ids(c, node_id):
    return [r[0] for r in c.execute(
        "SELECT descendant FROM closure WHERE ancestor = ?", (node_id,))]


# --------------------------------------------------------------------------
# edge expansion
# --------------------------------------------------------------------------

def dep_count(c, ids):
    ph = ",".join("?" * len(ids))
    r = c.execute(
        f"""SELECT COUNT(*) FROM (
              SELECT DISTINCT dst FROM ref WHERE src IN ({ph}) AND dst IS NOT NULL
              UNION SELECT DISTINCT dst FROM term WHERE src IN ({ph}))""",
        ids + ids).fetchone()
    return r[0] if r else 0


def outbound(c, ids):
    ph = ",".join("?" * len(ids))
    rows = c.execute(
        f"""SELECT DISTINCT src, dst, kind, text, reason FROM ref
            WHERE src IN ({ph}) AND dst IS NOT NULL""", ids).fetchall()
    return [r for r in rows if r["kind"] in REF_LABEL]


def unresolved(c, ids):
    ph = ",".join("?" * len(ids))
    return c.execute(
        f"""SELECT DISTINCT text, kind, reason FROM ref
            WHERE src IN ({ph}) AND dst IS NULL""", ids).fetchall()


def has_table(c, name):
    return c.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
                     (name,)).fetchone() is not None


def defined_terms(c, ids):
    ph = ",".join("?" * len(ids))
    if has_table(c, "term_resolved"):
        return c.execute(
            f"""SELECT DISTINCT t.term, t.dst FROM term_resolved t
                WHERE t.src IN ({ph}) ORDER BY t.term""", ids).fetchall()
    return c.execute(
        f"""SELECT DISTINCT t.term, t.dst FROM term t
            WHERE t.src IN ({ph}) ORDER BY t.term""", ids).fetchall()


def inbound_tables(c, ids):
    """Tables/figures bound to these provisions.

    The current model uses the explicit `forms_part_of` edge. Tree-parent lookup
    remains only as a compatibility fallback for pre-R4 release snapshots.
    """
    ph = ",".join("?" * len(ids))
    via_ref = c.execute(
        f"""SELECT DISTINCT r.src AS id, n.type, n.designator, n.heading
            FROM ref r JOIN node n ON n.id = r.src
            WHERE r.kind='forms_part_of' AND r.dst IN ({ph})
              AND n.type IN ('table','figure')
            ORDER BY n.rowid""", ids).fetchall()
    if via_ref:
        return via_ref
    return c.execute(
        f"""SELECT DISTINCT n.id, n.type, n.designator, n.heading
            FROM node n WHERE n.parent IN ({ph}) AND n.type IN ('table','figure')
            ORDER BY n.rowid""",
        ids).fetchall()


def citing_in(c, ids):
    ph = ",".join("?" * len(ids))
    return c.execute(
        f"""SELECT DISTINCT r.src, r.kind, n.type, n.designator, n.heading
            FROM ref r JOIN node n ON n.id = r.src
            WHERE r.dst IN ({ph}) AND n.type NOT IN ('table','figure')
            LIMIT 40""", ids).fetchall()


def amendments(c, ids):
    ph = ",".join("?" * len(ids))
    return c.execute(
        f"""SELECT DISTINCT node, marker, kind, instrument, effective
            FROM amendment WHERE node IN ({ph})""", ids).fetchall()


def render_table(c, table_id, max_rows=25):
    rows = c.execute(
        """SELECT page, r, c, rowspan, colspan, text FROM cell
           WHERE table_id = ? ORDER BY page, r, c""", (table_id,)).fetchall()
    if not rows:
        return "", 0
    grid = {}
    ncol = 0
    for x in rows:
        grid.setdefault(x["r"], {})[x["c"]] = (x["text"] or "").strip()
        ncol = max(ncol, x["c"] + 1)
    keys = sorted(grid)
    total = len(keys)
    out = []
    for i, rk in enumerate(keys[:max_rows]):
        cells = [grid[rk].get(ci, "") for ci in range(ncol)]
        out.append("| " + " | ".join(cells) + " |")
        if i == 0:
            out.append("|" + "---|" * ncol)
    if total > max_rows:
        out.append(f"_... {total - max_rows} further rows omitted; "
                   f"query the `cell` table for the full grid._")
    return "\n".join(out), total


# --------------------------------------------------------------------------
# bundle
# --------------------------------------------------------------------------

def build_bundle(c, node_id, hops=1, max_rows=25, budget=None):
    root = c.execute("SELECT * FROM node WHERE id = ?", (node_id,)).fetchone()
    if root is None:
        raise SystemExit(f"no such node: {node_id}")

    ids = scope_ids(c, node_id)
    own_rows = inbound_tables(c, ids)
    own_tables = [r["id"] for r in own_rows]
    b = {
        "anchor": dict(id=root["id"], designator=root["designator"],
                       heading=root["heading"], type=root["type"],
                       volume=root["volume"], page=root["page"],
                       permalink=root["permalink"]),
        "ancestors": [dict(r) for r in ancestors(c, node_id)],
        "provision": subtree_text(c, node_id),
        "terms": [], "cites": [], "notes": [], "standards": [],
        "tables": [], "cited_by": [], "amendments": [], "unresolved": [],
        "hops": hops,
    }

    seen = set(ids)
    b["dep_count"] = dep_count(c, ids)
    b["hub"] = b["dep_count"] > HUB_DEPS

    rows_cap = min(max_rows, 10) if b["hub"] else max_rows
    for tid in own_tables:
        d = c.execute("SELECT * FROM node WHERE id = ?", (tid,)).fetchone()
        if d is None:
            continue
        seen.add(tid)
        md, total = render_table(c, tid, rows_cap)
        b["tables"].append(dict(id=tid, designator=d["designator"],
                                heading=d["heading"], type=d["type"],
                                via="this provision's own table",
                                own=True, grid=md, rows=total))

    for t in defined_terms(c, ids):
        d = c.execute("SELECT * FROM node WHERE id = ?", (t["dst"],)).fetchone()
        if d is None:
            continue
        txt = " ".join(x["body"] for x in subtree_text(c, t["dst"]) if x["body"])
        b["terms"].append(dict(term=t["term"], id=t["dst"],
                               designator=d["designator"], text=txt.strip()))

    frontier, depth = ([], hops) if b["hub"] else (list(ids), 0)
    while frontier and depth < hops:
        nxt = []
        for e in outbound(c, frontier):
            if e["dst"] in seen:
                continue
            seen.add(e["dst"])
            d = c.execute("SELECT * FROM node WHERE id = ?", (e["dst"],)).fetchone()
            if d is None:
                continue
            txt = " ".join(x["body"] for x in subtree_text(c, e["dst"]) if x["body"])
            item = dict(id=e["dst"], designator=d["designator"],
                        heading=d["heading"], type=d["type"],
                        via=REF_LABEL.get(e["kind"], e["kind"]),
                        citation_text=e["text"], text=txt.strip()[:1600])
            if e["kind"] == "note":
                b["notes"].append(item)
            elif e["kind"] == "std":
                b["standards"].append(item)
            elif d["type"] in ("table", "figure"):
                b["tables"].append(item)
            else:
                b["cites"].append(item)
                nxt.append(e["dst"])
        frontier, depth = nxt, depth + 1

    # Compatibility path for a table that was not already picked up as an own
    # table (e.g. a legacy corpus or a broader descendant scope).
    for t in inbound_tables(c, ids):
        if t["id"] in seen:
            continue
        seen.add(t["id"])
        md, total = render_table(c, t["id"], max_rows)
        b["tables"].append(dict(id=t["id"], designator=t["designator"],
                                heading=t["heading"], type=t["type"],
                                via="forms part of this provision",
                                grid=md, rows=total))

    for t in b["tables"]:
        if "grid" not in t and t["type"] == "table":
            md, total = render_table(c, t["id"], max_rows)
            t["grid"], t["rows"] = md, total

    b["cited_by"] = [dict(id=r["src"], designator=r["designator"],
                          heading=r["heading"], type=r["type"]) for r in citing_in(c, ids)]
    b["amendments"] = [dict(r) for r in amendments(c, ids)]
    b["unresolved"] = [dict(r) for r in unresolved(c, ids)]

    if budget:
        trim(b, budget)
    b["approx_tokens"] = len(render(b)) // 4
    return b


def trim(b, budget):
    order = ["cited_by", "standards", "tables", "cites", "notes"]
    guard = 0
    while len(render(b)) // 4 > budget and guard < 5000:
        guard += 1
        for k in order:
            if k == "tables":
                idx = next((i for i, x in reversed(list(enumerate(b[k])))
                            if not x.get("own")), None)
                if idx is not None:
                    b[k].pop(idx)
                    break
                continue
            if b[k]:
                b[k].pop()
                break
        else:
            for t in b["tables"]:
                if t.get("own") and t.get("rows", 0) > 15 and t.get("grid"):
                    lines = t["grid"].split("\n")
                    t["grid"] = "\n".join(lines[:16]) + (
                        f"\n_... {t['rows'] - 14} further rows omitted; "
                        f"query the `cell` table for the full grid._")
                    t["rows"] = 15
                    break
            else:
                return


# --------------------------------------------------------------------------
# rendering
# --------------------------------------------------------------------------

def render(b):
    a = b["anchor"]
    L = []
    trail = " > ".join(f"{x['designator'] or x['id']} {x['heading'] or ''}".strip()
                       for x in reversed(b["ancestors"])) or "(root)"

    L.append(f"# {a['designator'] or a['id']} {a['heading'] or ''}".rstrip())
    L.append(f"`{a['id']}` - Volume {a['volume']}, p. {a['page']}")
    L.append(f"**Scope:** {trail}")
    L.append("")

    if b.get("hub"):
        L.append(f"> **Delivered by reference.** This provision has "
                 f"{b['dep_count']} dependencies — more than any context window "
                 f"holds. Its own tables are included below (row-capped); "
                 f"cited provisions are not expanded. Query them by id.")
        L.append("")

    L.append("## Provision")
    for n in b["provision"]:
        if n["depth"] == 0 and not n["body"]:
            continue
        pad = "  " * max(0, n["depth"] - 1)
        tag = f" _[{n['modality']}]_" if n["modality"] and n["modality"] != "statement" else ""
        head = f"**{n['heading']}** " if n["heading"] and n["depth"] else ""
        L.append(f"{pad}- {head}{n['body']}{tag}")
    L.append("")

    if b["terms"]:
        L.append("## Defined terms used (Division A 1.4.1.2 / the Act)")
        for t in b["terms"]:
            L.append(f"- **{t['term']}** (`{t['id']}`): {t['text'][:400]}")
        L.append("")

    if b["cites"]:
        L.append("## Provisions this cites")
        for x in b["cites"]:
            L.append(f"- **{x['designator'] or x['id']}** {x['heading'] or ''} "
                     f"({x['via']}): {x['text'][:400]}")
        L.append("")

    if b["notes"]:
        L.append("## Explanatory notes (Appendix A - explanatory, not mandatory)")
        for x in b["notes"]:
            L.append(f"- **{x['designator'] or x['id']}** {x['heading'] or ''}: {x['text'][:700]}")
        L.append("")

    if b["tables"]:
        L.append("## Tables and figures")
        for x in b["tables"]:
            L.append(f"### {x['designator'] or x['id']} {x.get('heading') or ''} ({x['via']})")
            if x.get("grid"):
                L.append(x["grid"])
            elif x.get("text"):
                L.append(x["text"][:600])
            L.append("")

    if b["standards"]:
        L.append("## Referenced standards")
        for x in b["standards"]:
            L.append(f"- {x['citation_text'] or x['designator'] or x['id']}")
        L.append("")

    if b["amendments"]:
        L.append("## Amendment history")
        for x in b["amendments"]:
            L.append(f"- `{x['node']}` {x['kind'] or ''} by {x['instrument'] or '?'}, "
                     f"effective {x['effective'] or '?'}")
        L.append("")

    if b["cited_by"]:
        L.append("## Cited by (reverse edges - other provisions that depend on this)")
        L.append(", ".join(f"{x['designator'] or x['id']}" for x in b["cited_by"]))
        L.append("")

    if b["unresolved"]:
        L.append("## Unresolved references (deliberate - not defects)")
        for x in b["unresolved"]:
            L.append(f"- \"{x['text']}\" ({x['kind']}) - {x['reason']}")
        L.append("")

    L.append("---")
    L.append("Unofficial. Current to 2025-01-16 (through O. Reg. 5/25). "
             "Not the official Building Code Compendium. "
             "© King's Printer for Ontario, 2024. Reproduced with permission.")
    return "\n".join(L)


def modality_report(c):
    rows = c.execute(
        f"""SELECT id, designator, body FROM node
            WHERE type IN {LEAF} AND body IS NOT NULL AND body != ''""").fetchall()
    counts = {}
    for r in rows:
        m = modality_of(r["body"])
        counts[m] = counts.get(m, 0) + 1
    total = sum(counts.values())
    print(f"modality over {total} text-bearing leaf nodes:")
    for k, v in sorted(counts.items(), key=lambda x: -x[1]):
        print(f"  {v:>6}  {100*v/total:5.1f}%  {k}")
    print("\nnormative (obligation+prohibition): "
          f"{counts.get('obligation',0)+counts.get('prohibition',0)}")


def main():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("anchor", nargs="?", help="node id, designator, or free text")
    p.add_argument("--db", default=DB)
    p.add_argument("--hops", type=int, default=1)
    p.add_argument("--budget", type=int, default=None,
                   help="approximate token budget; sections are dropped to fit")
    p.add_argument("--max-rows", type=int, default=25)
    p.add_argument("--json", action="store_true")
    p.add_argument("--search", help="search only, list candidates")
    p.add_argument("--limit", type=int, default=8)
    p.add_argument("--modality-report", action="store_true")
    args = p.parse_args()

    c = connect(args.db)

    if args.modality_report:
        return modality_report(c)

    if args.search:
        for r in resolve(c, args.search, args.limit):
            print(f"{r['id']:<34} {r['type']:<14} {r['designator'] or '':<12} "
                  f"{(r['heading'] or (r['body'] or '')[:60])[:60]}")
        return

    if not args.anchor:
        p.error("give an anchor, --search, or --modality-report")

    cands = resolve(c, args.anchor, args.limit)
    if not cands:
        raise SystemExit(f"nothing matched: {args.anchor!r}")
    if len(cands) > 1:
        print(f"# {len(cands)} candidates; using the first. "
              f"Others: {', '.join(x['id'] for x in cands[1:6])}\n", file=sys.stderr)

    b = build_bundle(c, cands[0]["id"], hops=args.hops,
                     max_rows=args.max_rows, budget=args.budget)
    print(json.dumps(b, ensure_ascii=False, indent=2) if args.json else render(b))


if __name__ == "__main__":
    main()
