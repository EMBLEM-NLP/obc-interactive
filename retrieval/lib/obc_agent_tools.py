#!/usr/bin/env python3
"""
obc_agent_tools.py - the tool surface an agent can actually call.

`obc_context.py` is a library. An agent cannot import a library; it needs a
contract: named tools, typed arguments, structured results, and an honest
statement of what the tools cannot do. This file is that contract.

Design rules
------------
1. Every result carries node ids and verbatim text. An agent that cannot
   cite a node id has not answered; it has guessed.
2. `capabilities()` is a tool, not documentation. An agent asked "does Part 9
   apply to my building?" must be able to discover that the graph cannot
   answer that, rather than reasoning its way to a confident wrong answer
   from scoping prose. Stating the boundary is a feature.
3. Stack-agnostic. TOOLS is a list of JSON-schema tool definitions usable
   with Anthropic tool use, OpenAI function calling, LangChain, or MCP.
   `--mcp` serves the same functions over the Model Context Protocol.

    python3 obc_agent_tools.py --demo
    python3 obc_agent_tools.py --mcp --db obc-mod.sqlite
"""

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from obc_context import (connect, resolve, build_bundle, render,  # noqa: E402
                         scope_ids, HUB_DEPS)

def _resolve_db():
    """OBC_DB may be absolute, relative to cwd, or relative to the package root.
    Claude Code starts MCP servers with cwd at the project root, but nothing in
    the spec guarantees it; resolve against the package root as a fallback so
    .mcp.json needs no environment variable."""
    p = os.environ.get("OBC_DB", "emitters/obc-mod.sqlite")
    if os.path.isabs(p) or os.path.exists(p):
        return p
    root = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
    q = os.path.join(root, p)
    return q if os.path.exists(q) else p

DB_PATH = _resolve_db()
_db = None

ATTRIBUTION = ("Unofficial. Current to 2025-01-16 (through O. Reg. 5/25). "
               "Not the official Building Code Compendium. "
               "© King's Printer for Ontario, 2024. Reproduced with permission.")


class DataUnavailable(RuntimeError):
    """The graph is not on disk. Raised with the remedy, never bare.

    An agent that calls a tool and gets `Error executing tool obc_capabilities`
    learns only that something broke. Every other entry point in this project
    names its cause: check40 lists the missing files, run_gates.py names the
    DATA1 abort, regenerate.sh explains its refusal. The surface an agent
    actually talks to said nothing at all. Observed 2026-09-08 over MCP.
    """


DATA_REMEDY = ("The derived data is not kept in git. Run: bash ci/fetch_data.sh "
               "(needs OBC_DATA_URL, OBC_DATA_TARBALL or OBC_DATA_DIR), then "
               "restart the MCP server.")


def db():
    global _db
    if _db is None:
        try:
            _db = connect(DB_PATH)
        except FileNotFoundError as e:
            raise DataUnavailable(f"the OBC graph is not available: {e}. {DATA_REMEDY}") from e
    return _db


def _node(row):
    return dict(id=row["id"], type=row["type"], designator=row["designator"],
                heading=row["heading"], volume=row["volume"], page=row["page"])


# --------------------------------------------------------------------------
# tools
# --------------------------------------------------------------------------

def search(query: str, limit: int = 8) -> dict:
    """Find provisions by designator, id, or free text.

    Lexical + trigram only. There is no semantic index in this tool surface
    yet, so a query with no word overlap with the provision will miss.
    Index and table-of-contents nodes are demoted below provisions."""
    rows = resolve(db(), query, limit)
    return dict(query=query, results=[
        dict(_node(r), snippet=((r["heading"] or r["body"] or "")[:160]))
        for r in rows])


def get_provision(node_id: str) -> dict:
    """Verbatim text of one node and its subtree, with modality per leaf.
    Use this for exact quotation. Use get_context for reasoning."""
    b = build_bundle(db(), node_id, hops=0, budget=None)
    return dict(anchor=b["anchor"],
                scope=[a["designator"] or a["id"] for a in reversed(b["ancestors"])],
                text=[dict(id=p["id"], designator=p["designator"],
                           body=p["body"], modality=p["modality"])
                      for p in b["provision"] if p["body"]],
                attribution=ATTRIBUTION)


def get_context(node_id: str, hops: int = 1, budget_tokens: int = 6000) -> dict:
    """The mandatory-context bundle: provision text, every defined term it
    uses, what it cites, its explanatory notes, tables that form part of it,
    referenced standards, amendments, and reverse citations. This is the
    unit an agent should reason over. Never reason over get_provision alone
    for a requirement that uses defined terms - the definitions change the
    meaning."""
    b = build_bundle(db(), node_id, hops=hops, budget=budget_tokens)
    out = dict(
        anchor=b["anchor"], hub=b["hub"], dependency_count=b["dep_count"],
        approx_tokens=b["approx_tokens"],
        markdown=render(b),
        definitions=[dict(term=t["term"], id=t["id"], text=t["text"]) for t in b["terms"]],
        cites=[dict(id=x["id"], designator=x["designator"], heading=x["heading"])
               for x in b["cites"]],
        notes=[dict(id=x["id"], designator=x["designator"]) for x in b["notes"]],
        tables=[dict(id=x["id"], designator=x["designator"], rows=x.get("rows"))
                for x in b["tables"]],
        standards=[x["citation_text"] or x["id"] for x in b["standards"]],
        amendments=b["amendments"],
        cited_by=[x["id"] for x in b["cited_by"]],
        unresolved=b["unresolved"],
        attribution=ATTRIBUTION)
    if b["hub"]:
        out["warning"] = (f"Hub provision with {b['dep_count']} dependencies; "
                          f"cited provisions are NOT expanded. Query them by id.")
    return out


def neighbors(node_id: str) -> dict:
    """Structural neighbourhood: parent, children, and every typed edge in
    and out. For walking the graph one step at a time."""
    c = db()
    n = c.execute("SELECT * FROM node WHERE id=?", (node_id,)).fetchone()
    if n is None:
        return dict(error=f"no such node: {node_id}")
    kids = [_node(r) for r in c.execute(
        "SELECT * FROM node WHERE parent=? ORDER BY page, rowid", (node_id,))]
    out_e = [dict(kind=r["kind"], to=r["dst"], text=r["text"]) for r in c.execute(
        "SELECT kind, dst, text FROM ref WHERE src=? AND dst IS NOT NULL", (node_id,))]
    in_e = [dict(kind=r["kind"], from_=r["src"]) for r in c.execute(
        "SELECT kind, src FROM ref WHERE dst=? LIMIT 50", (node_id,))]
    terms = [dict(term=r["term"], definition=r["dst"]) for r in c.execute(
        "SELECT term, dst FROM term_resolved WHERE src=?", (node_id,))]
    return dict(node=_node(n), parent=n["parent"], children=kids,
                edges_out=out_e, edges_in=in_e, defined_terms=terms)


def what_cites(node_id: str, limit: int = 50) -> dict:
    """Every provision that depends on this one. Use before concluding a
    change here is isolated: a definition or a table is cited from many
    places, and the citing provisions are where the requirement lives."""
    c = db()
    ids = scope_ids(c, node_id)
    ph = ",".join("?" * len(ids))
    # Citation edges and defined-term usage are stored in different tables.
    # A reverse lookup that reads only `ref` reports zero users for every
    # definition - which is the answer an agent would least suspect and
    # most confidently misuse ("nothing depends on this term").
    rows = c.execute(
        f"""SELECT DISTINCT src, kind, type, designator, heading FROM (
              SELECT r.src, r.kind, n.type, n.designator, n.heading
              FROM ref r JOIN node n ON n.id=r.src WHERE r.dst IN ({ph})
              UNION
              SELECT t.src, 'uses_term', n.type, n.designator, n.heading
              FROM term_resolved t JOIN node n ON n.id=t.src WHERE t.dst IN ({ph}))
            LIMIT ?""", ids + ids + [limit]).fetchall()
    return dict(node_id=node_id, count=len(rows), citing=[
        dict(id=r["src"], kind=r["kind"], type=r["type"],
             designator=r["designator"], heading=r["heading"]) for r in rows])


# Each `cannot` line is a PROBE against the live database, not a sentence
# someone typed. When Track F-scope adds occupancy nodes, the applicability
# line disappears on its own; when B3 links heading notes, that line's count
# drops to zero and it disappears. A hand-written list is a latent lie the
# moment the graph changes - and this file shipped with one for two turns.
#
# Each probe: (id, sql, predicate_on_row, message). The message may use {n}.
CANNOT_PROBES = [
    ("applicability",
     "SELECT COUNT(*) FROM node WHERE type IN ('occupancy','applicability_predicate')",
     lambda n: n == 0,
     "determine which Part, occupancy group, or classification applies to a described building - no occupancy nodes or APPLIES_TO edges exist"),
    ("objectives",
     "SELECT COUNT(*) FROM node WHERE type IN ('objective','functional_statement')",
     lambda n: n == 0,
     "state the objective or functional statement a provision serves - not modelled"),
    ("temporal",
     "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name IN ('in_force','edition')",
     lambda n: n == 0,
     "confirm whether a provision is in force on a given date - amendments are recorded, no temporal model"),
    ("rules",
     "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='rule'",
     lambda n: n == 0,
     "check a design for compliance - no rule layer; modality tags are not executable rules"),
    ("semantic",
     # Not "does a vector table exist" - it does. "Does the search tool USE it."
     # Until G1 wires hybrid retrieval into search(), this line must stand.
     "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='vec_article'",
     lambda n: n == 0 or not _search_uses_vectors(),
     "find provisions by meaning without word overlap - search() does not query the vector index yet (Track G1)"),
    ("heading_notes",
     """SELECT COUNT(*) FROM node n WHERE n.heading LIKE '%See Note%'
        AND NOT EXISTS (SELECT 1 FROM ref r WHERE r.kind='note' AND r.src IN
          (SELECT descendant FROM closure WHERE ancestor=n.id))""",
     lambda n: n > 0,
     "reach an explanatory note referenced only from a heading - {n} such notes are unlinked"),
]


def _search_uses_vectors():
    import inspect
    src = inspect.getsource(search)
    return "vec_article" in src or "vec0" in src


def compute_cannot(c):
    out = []
    for pid, sql, pred, msg in CANNOT_PROBES:
        try:
            n = c.execute(sql).fetchone()[0]
        except Exception:
            n = 0            # table absent -> the capability is absent
            pred_hit = pred(0)
        else:
            pred_hit = pred(n)
        if pred_hit:
            out.append(dict(id=pid, text=msg.format(n=n), evidence=dict(sql=" ".join(sql.split()), value=n)))
    out.append(dict(id="official", text="give an official or legally authoritative reading",
                    evidence=dict(sql=None, value=None)))
    return out


def capabilities() -> dict:
    """What these tools can and cannot answer, computed from the database.

    Call before answering a question about applicability, classification,
    objectives, or currency. A confident answer to a question in `cannot` is a
    hallucination by construction - the data to support it does not exist.
    Every `cannot` entry carries the SQL that established it."""
    # A tool whose job is to state limits must still answer when the graph is
    # absent - that is the widest limit there is. Returning it as data beats
    # raising, because the agent can read it and stop rather than retry.
    try:
        c = db()
    except DataUnavailable as e:
        return dict(
            edition="2024 Building Code Compendium, current to 2025-01-16 (O. Reg. 5/25)",
            available=False,
            reason=str(e),
            remedy=DATA_REMEDY,
            database=DB_PATH,
            can=[],
            cannot=["anything at all: the graph is not present on this machine, "
                    "so every question about the Code is unanswerable here"],
            attribution=ATTRIBUTION)
    stats = dict(
        nodes=c.execute("SELECT COUNT(*) FROM node").fetchone()[0],
        articles=c.execute("SELECT COUNT(*) FROM node WHERE type='article'").fetchone()[0],
        definitions=c.execute("SELECT COUNT(*) FROM node WHERE type='defined_term'").fetchone()[0],
        tables=c.execute("SELECT COUNT(*) FROM node WHERE type='table'").fetchone()[0],
        ref_edges=c.execute("SELECT COUNT(*) FROM ref WHERE dst IS NOT NULL").fetchone()[0],
        modality_tagged=c.execute("SELECT COUNT(*) FROM node WHERE modality IS NOT NULL").fetchone()[0])
    return dict(
        edition="2024 Building Code Compendium, current to 2025-01-16 (O. Reg. 5/25)",
        stats=stats,
        can=[
            "find a provision by number, id, or words that appear in it",
            "return verbatim text with a citable node id and page",
            "assemble the definitions, citations, notes, tables and standards a provision depends on",
            "say whether a sentence is an obligation, prohibition, permission, exemption or statement",
            "walk parent/child and citation edges in either direction",
            "list which provisions cite a given definition, table or article",
            "report which references are unresolved and why",
        ],
        cannot=[x["text"] for x in compute_cannot(c)],
        cannot_evidence=compute_cannot(c),
        hub_threshold=HUB_DEPS,
        attribution=ATTRIBUTION)


# --------------------------------------------------------------------------
# schemas - consumable by any tool-using framework
# --------------------------------------------------------------------------

def _schema(name, desc, props, required):
    return dict(name=name, description=desc,
                input_schema=dict(type="object", properties=props, required=required))


TOOLS = [
    _schema("obc_capabilities", capabilities.__doc__, {}, []),
    _schema("obc_search", search.__doc__,
            dict(query=dict(type="string"), limit=dict(type="integer", default=8)), ["query"]),
    _schema("obc_get_provision", get_provision.__doc__,
            dict(node_id=dict(type="string")), ["node_id"]),
    _schema("obc_get_context", get_context.__doc__,
            dict(node_id=dict(type="string"), hops=dict(type="integer", default=1),
                 budget_tokens=dict(type="integer", default=6000)), ["node_id"]),
    _schema("obc_neighbors", neighbors.__doc__, dict(node_id=dict(type="string")), ["node_id"]),
    _schema("obc_what_cites", what_cites.__doc__,
            dict(node_id=dict(type="string"), limit=dict(type="integer", default=50)), ["node_id"]),
]

DISPATCH = dict(obc_capabilities=capabilities, obc_search=search,
                obc_get_provision=get_provision, obc_get_context=get_context,
                obc_neighbors=neighbors, obc_what_cites=what_cites)


def call(name: str, **kwargs):
    """Single entry point for any framework: call(tool_name, **args) -> dict."""
    return DISPATCH[name](**kwargs)


# --------------------------------------------------------------------------
# optional MCP server (mcp>=2)
# --------------------------------------------------------------------------

def build_mcp():
    """Tools (model-controlled), resources (application-read), prompts
    (user-controlled) - the three MCP primitives. Tools are load-bearing;
    resources and prompts are convenience and host support varies, so every
    resource is also reachable through a tool."""
    from mcp.server.mcpserver import MCPServer
    srv = MCPServer("obc")
    for fn in (capabilities, search, get_provision, get_context, neighbors, what_cites):
        srv.tool(name=f"obc_{fn.__name__}")(fn)

    @srv.resource("obc://capabilities")
    def r_capabilities() -> str:
        """What the graph can and cannot answer, with the SQL behind each cannot."""
        return json.dumps(capabilities(), ensure_ascii=False, indent=1)

    @srv.resource("obc://gate-board")
    def r_gate_board() -> str:
        """The most recent ci/gate-board.json: every gate, pass/fail/skip/known, with reasons."""
        p = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "ci", "gate-board.json")
        return open(p).read() if os.path.exists(p) else json.dumps({"error": "no board yet; run ci/run_gates.py"})

    @srv.resource("obc://provision/{+node_id}")
    def r_provision(node_id: str) -> str:
        """Verbatim text of one provision by node id, e.g. obc://provision/B/9/9.32.3.8"""
        return json.dumps(get_provision(node_id), ensure_ascii=False, indent=1)

    @srv.resource("obc://tracks")
    def r_tracks() -> str:
        """orchestration/tracks.yaml - the dependency DAG and the four pending decisions."""
        p = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "orchestration", "tracks.yaml")
        return open(p).read() if os.path.exists(p) else ""

    @srv.prompt("obc-seven-step-cycle")
    def p_cycle(track: str) -> str:
        """Execute one track under orchestration/PROTOCOL.md."""
        return (f"You are executing track {track} of the OBC pipeline. Read obc://tracks for its brief.\n"
                f"Follow the seven steps in order: DECLARE gates, BUILD in a copy, MUTATE (register an H10 "
                f"control in check35 for every ratio gate), INTEGRATE at real paths, RE-BAG via ci/regenerate.sh, "
                f"VERIFY with ci/run_gates.py from a clean tree, AUDIT an addendum.\n"
                f"Read obc://capabilities before answering anything about applicability, objectives, currency or compliance. "
                f"If the track touches any decision in obc://tracks decisions_pending, STOP and ask; do not assume.")

    @srv.prompt("obc-audit-addendum")
    def p_audit(track: str) -> str:
        """Template for the audit addendum a track must return."""
        return (f"Write the audit addendum for {track}. Four sections, all mandatory: "
                f"WHAT MOVED (with the gate ids and evidence digests), WHAT DID NOT (unchanged tracks, stated), "
                f"WHAT BROKE (every bug in your own patch, including ones that silently matched nothing), "
                f"WHAT WAS FOUND (every track so far found something the previous one missed; state yours). "
                f"Preserve earlier revisions unedited. No number without the check that produced it.")
    return srv


def serve_mcp():
    build_mcp().run()


def main():
    global DB_PATH
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default=DB_PATH)
    ap.add_argument("--mcp", action="store_true")
    ap.add_argument("--demo", action="store_true")
    ap.add_argument("--schemas", action="store_true")
    a = ap.parse_args()
    DB_PATH = a.db

    if a.schemas:
        print(json.dumps(TOOLS, indent=2)); return
    if a.mcp:
        serve_mcp(); return
    if a.demo:
        cap = call("obc_capabilities")
        print("CAN   :", *cap["can"], sep="\n  - ")
        print("CANNOT:", *cap["cannot"], sep="\n  - ")
        print()
        s = call("obc_search", query="secondary suite ventilation", limit=3)
        print("search ->", [r["id"] for r in s["results"]])
        top = s["results"][0]["id"]
        ctx = call("obc_get_context", node_id=top, hops=1, budget_tokens=4000)
        print(f"context({top}) -> {len(ctx['definitions'])} defs, {len(ctx['tables'])} tables, "
              f"{len(ctx['cites'])} cites, ~{ctx['approx_tokens']} tok, hub={ctx['hub']}")
        wc = call("obc_what_cites", node_id="DEF/secondary-suite")
        print(f"what_cites(DEF/secondary-suite) -> {len(wc['citing'])} provisions")
        return
    ap.print_help()


if __name__ == "__main__":
    main()
