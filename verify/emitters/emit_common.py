#!/usr/bin/env python3
"""Shared identity layer for every emitter.

The research recommendation that changes the design: the JSONL graph is
canonical, and every output must carry (a) a URL-safe permalink derived from the
node id, (b) a version-independent id kept distinct from a point-in-time one,
and (c) a currency stamp plus an unofficial-version notice. Retrofitting those
is expensive, so they are fixed here once and imported by all three emitters.
"""
import gzip, json, re

GRAPH = "out/docgraph-merged.jsonl.gz"

# derived from the amendment legend parsed in stage 9, not hard-coded prose
CURRENT_TO = "16 January 2025"
CURRENT_TO_ISO = "2025-01-16"
THROUGH = "O. Reg. 5/25"

NOTICE = (
    "Unofficial version. This is not the official Building Code Compendium. "
    f"Current to {CURRENT_TO} (through {THROUGH}). "
    "Consult the official Compendium published by Publications Ontario for "
    "authoritative text."
)
COPYRIGHT = (
    "© King's Printer for Ontario, 2024. Reproduced with permission. "
    "Contains material copyrighted by the National Research Council of Canada, "
    "reproduced under a licence agreement."
)
LICENCE = (
    "Permitted for personal use and non-commercial reproduction and "
    "distribution only, and only where this product is made available to the "
    "public free of charge. Any use that is not free to the public is treated "
    "by the Ministry of Municipal Affairs and Housing as commercial use and "
    "requires a licence: buildingtransformation@ontario.ca"
)

VOLUME_FILE = {1: "301880_built_from_model.pdf", 2: "301881_built_from_model.pdf"}

def permalink(nid):
    """URL-safe, stable, and reversible enough to be documented.

    B/9/9.10.16.1/(2)/(a)  ->  B/9/9.10.16.1/s2/c-a
    ACT/15.4.2/(1)         ->  ACT/15.4.2/s1
    APPA/A-3.1.2.          ->  APPA/A-3.1.2.
    The designator itself is preserved, so an inserted 9.10.16.1A slots in
    without renumbering its siblings and a repealed provision keeps its slug.
    """
    parts = []
    for seg in nid.split("/"):
        m = re.fullmatch(r"\((\d+(?:\.\d+)?)\)", seg)
        if m:
            parts.append("s" + m.group(1)); continue
        m = re.fullmatch(r"\(([a-z](?:\.\d+)?)\)", seg)
        if m:
            parts.append("c-" + m.group(1)); continue
        m = re.fullmatch(r"\(([ivx]+)\)", seg)
        if m:
            parts.append("sc-" + m.group(1)); continue
        parts.append(re.sub(r"[^A-Za-z0-9._-]", "-", seg))
    return "/".join(parts)

def anchor(nid):
    return permalink(nid).replace("/", "__")

def load_graph(path=GRAPH):
    nodes, order, meta = {}, [], None
    for line in gzip.open(path, "rt", encoding="utf-8"):
        r = json.loads(line)
        if r.get("_meta"):
            meta = r
        else:
            nodes[r["id"]] = r
            order.append(r["id"])
    return nodes, order, meta

def node_text(n):
    return " ".join(t["t"] for t in n.get("text", [])).strip()

def designator(n):
    """what the page prints for this node"""
    t, num = n["type"], (n.get("number") or "")
    if not num:
        return ""
    if t in ("sentence", "clause", "subclause", "act_subsection",
             "act_clause", "act_subclause"):
        return f"({num})"
    return num if num.endswith(".") else num + "."

def breadcrumb(nodes, nid):
    out, cur = [], nid
    seen = set()
    while cur and cur in nodes and cur not in seen:
        seen.add(cur)
        n = nodes[cur]
        label = (designator(n) + " " + (n.get("heading") or "")).strip()
        out.append(label or n["type"])
        cur = n.get("parent")
    return " > ".join(reversed(out))
