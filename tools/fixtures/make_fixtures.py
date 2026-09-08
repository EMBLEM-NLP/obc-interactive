#!/usr/bin/env python3
"""
make_fixtures.py - MAINT. Build the two synthetic editions M1 and M2 are
measured on, plus the seed manifest that says exactly what differs.

Why synthetic
-------------
This clone carries no derived data: `harden/checks/check40_dataintegrity.py
--quick` reports 29 of 29 declared files MISSING and exits 1, so
`model/docgraph-merged.jsonl.gz` does not exist and two real editions cannot be
diffed here. A tool tested on fixtures it can actually run beats a tool tested
on nothing, so M1 and M2 are established on these. **The corpus run is owed**
and is a precondition of MAINT reaching `done`. Nothing produced here is a
claim about the Ontario Building Code.

Where the record shape comes from
---------------------------------
From code, never from a guess and never from the graph:

    pipeline/stage3_tree.py:136        node constructor - id, type, number,
                                       heading, parent, children, text, provenance
    pipeline/stage3_tree.py:166        text token   {"p", "t", "b", "it"}
    pipeline/stage7_refs.py:197        refs element {"chunk","line","s","e",
                                                     "kind","text","target","why"}
    pipeline/stage7_refs.py:220        terms element {"chunk","term","target",
                                                      "to_page","to_y"}
    pipeline/stage9_amendments.py:99   amendment element, the legend entry minus
                                       `statement`: {"marker","kind","instrument","effective"}
    pipeline/emitters/stage15_sqlite.py:125  grid cell {"page","r","c","rowspan",
                                                        "colspan","text"}
    pipeline/vol2/stage10_merge.py:30  the `_meta` line and the per-node `volume`
    schema/obc.linkml.yaml             closed enums: NodeType, EdgeKind,
                                       Resolution, AmendmentKind

Every `type` used below is a permissible value of NodeType; every ref `kind` is
a permissible value of EdgeKind; every amendment `kind` is a permissible value
of AmendmentKind. Node ids follow the citation grammar
(`B/9/9.32.3.8/(1)/(a)`, `B/9/table/9.32.3.1`, `APPA/A-9.32.3.8`,
`DEF/secondary-suite`).

The two editions
----------------
base.jsonl.gz      15 nodes.
amended.jsonl.gz   the same 15 nodes REPAGINATED END TO END - every provenance
                   page and bbox and every text token's `p`/`b` shifted - plus
                   exactly five substantive changes:

    modified  B/9/9.32.3.8/(1)          body text amended; gains an amendment record
    added     B/9/9.32.3.8/(1)/(c)      a new clause, amendment kind `new`
    removed   B/9/9.32.3.9/(1)          revoked sentence
    modified  B/9/table/9.32.3.1        gains an amendment record; no text change
    modified  APPA/A-9.32.3.8           body text only; no marker, no ref change

The last one is not decoration. It is the only node whose sole substantive
difference is its text, and without it the recall half of the H10 control cannot
fail: every other seeded node is also reported through a `refs` or `amendment`
change, so a diff blinded to `body` still scores recall 1.0.

The repagination is the whole point of the fixture. It is what makes M2's
precision half meaningful: a diff that does not project layout away reports all
15 nodes, scores recall 1.0, and is useless. A gate on recall alone would be
green for exactly the tool this track exists to avoid shipping.

Removing B/9/9.32.3.9/(1) also changes its parent article's `children` list. The
parent must NOT be reported: `children` is derivable from `parent` and diffing
both reports one fact twice. That is a second assertion riding along for free.

    python3 tools/fixtures/make_fixtures.py [--out DIR]

Output is byte-deterministic: gzip mtime is pinned to 0 and every JSON dump is
sort_keys, so the fixtures themselves cannot be the source of an M1 failure.
"""
import argparse
import gzip
import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_OUT = os.path.join(_HERE, "build")

INSTRUMENT = "O. Reg. 163/24"
EFFECTIVE = "2024-07-01"

# --- amendment legend, shaped as pipeline/stage9_amendments.py writes it -----
LEGEND = {
    "*": {"kind": "amended", "instrument": INSTRUMENT, "effective": EFFECTIVE,
          "legend_page": 3},
    "**": {"kind": "new", "instrument": INSTRUMENT, "effective": EFFECTIVE,
           "legend_page": 3},
    "***": {"kind": "revoked", "instrument": INSTRUMENT, "effective": EFFECTIVE,
            "legend_page": 3},
}


def _amd(marker):
    """The legend entry minus `statement`, exactly as stage9 attaches it."""
    return {k: v for k, v in LEGEND[marker].items()
            if k not in ("statement", "legend_page")} | {"marker": marker}


def tok(page, y, text, italics=None):
    t = {"p": page, "t": text, "b": [72.0, float(y), 523.0, float(y) + 11.0]}
    if italics:
        t["it"] = list(italics)
    return t


def node(nid, ntype, number, heading, parent, page, y, volume=1, **extra):
    n = {"id": nid, "type": ntype, "number": number, "heading": heading,
         "parent": parent, "children": [], "text": [], "volume": volume,
         "provenance": [{"page": page, "bbox": [72.0, float(y), 523.0, float(y) + 11.0]}]}
    n.update(extra)
    return n


def base_nodes():
    """15 nodes modelled on Division B Part 9, Subsection 9.32.3."""
    n = []
    n.append(node("B", "division", "B", "Acceptable Solutions", None, 21, 700))
    n.append(node("B/9", "part", "9", "Housing and Small Buildings", "B", 640, 700))
    n.append(node("B/9/9.32", "section", "9.32.", "Ventilation", "B/9", 812, 690))
    n.append(node("B/9/9.32.3", "subsection", "9.32.3.",
                  "Mechanical Ventilation", "B/9/9.32", 814, 640))
    n.append(node("B/9/9.32.3.8", "article", "9.32.3.8.",
                  "Ventilation Capacity", "B/9/9.32.3", 816, 520))

    s1 = node("B/9/9.32.3.8/(1)", "sentence", "1", None, "B/9/9.32.3.8", 816, 505)
    s1["text"] = [
        tok(816, 505, "Except as provided in Sentence (2), the ventilation "
                      "capacity of a", ["dwelling unit"]),
        tok(816, 493, "shall conform to Table 9.32.3.3."),
    ]
    s1["refs"] = [
        {"chunk": "*", "line": 0, "s": 22, "e": 33, "kind": "code_ref",
         "text": "Sentence (2)", "target": "B/9/9.32.3.8/(2)", "why": "exact"},
        {"chunk": "*", "line": 1, "s": 20, "e": 38, "kind": "cap_ref",
         "text": "Table 9.32.3.3.", "target": "B/9/table/9.32.3.1", "why": "exact"},
    ]
    s1["terms"] = [{"chunk": 0, "term": "dwelling unit",
                    "target": "DEF/dwelling-unit", "to_page": 40, "to_y": 300.0}]
    n.append(s1)

    a = node("B/9/9.32.3.8/(1)/(a)", "clause", "a", None, "B/9/9.32.3.8/(1)", 816, 481)
    a["text"] = [tok(816, 481, "the total ventilation capacity, and")]
    n.append(a)

    b = node("B/9/9.32.3.8/(1)/(b)", "clause", "b", None, "B/9/9.32.3.8/(1)", 816, 469)
    b["text"] = [tok(816, 469, "the principal ventilation rate.")]
    n.append(b)

    s2 = node("B/9/9.32.3.8/(2)", "sentence", "2", None, "B/9/9.32.3.8", 816, 457)
    s2["text"] = [tok(816, 457, "Sentence (1) does not apply to a building "
                                "described in Article 9.32.3.9.")]
    s2["refs"] = [{"chunk": "*", "line": 0, "s": 44, "e": 66, "kind": "code_ref",
                   "text": "Article 9.32.3.9.", "target": "B/9/9.32.3.9",
                   "why": "exact"}]
    n.append(s2)

    n.append(node("B/9/9.32.3.9", "article", "9.32.3.9.",
                  "Ventilation Exhaust", "B/9/9.32.3", 817, 700))

    s3 = node("B/9/9.32.3.9/(1)", "sentence", "1", None, "B/9/9.32.3.9", 817, 688)
    s3["text"] = [tok(817, 688, "Exhaust ducts shall be constructed of "
                                "non-combustible material.")]
    n.append(s3)

    t = node("B/9/table/9.32.3.1", "table", "9.32.3.1.",
             "Ventilation Capacity Forming Part of Sentence 9.32.3.8.(1)",
             "B/9/9.32.3.8", 818, 600)
    t["grid"] = [
        {"page": 818, "r": 0, "c": 0, "rowspan": 1, "colspan": 1, "text": "Bedrooms"},
        {"page": 818, "r": 0, "c": 1, "rowspan": 1, "colspan": 1, "text": "L/s"},
        {"page": 818, "r": 1, "c": 0, "rowspan": 1, "colspan": 1, "text": "1"},
        {"page": 818, "r": 1, "c": 1, "rowspan": 1, "colspan": 1, "text": "25"},
    ]
    n.append(t)

    d = node("DEF/dwelling-unit", "defined_term", None, "dwelling unit",
             "A", 40, 300)
    d["text"] = [tok(40, 300, "means a suite operated as a housekeeping unit.")]
    n.append(d)

    ap = node("APPA/A-9.32.3.8", "note", "A-9.32.3.8.",
              "Ventilation Capacity", None, 120, 400, volume=2)
    ap["text"] = [tok(120, 400, "This Article establishes the minimum capacity.")]
    n.append(ap)

    n.append(node("A", "division", "A", "Compliance and General", None, 5, 700))

    # children, derived from parent exactly as stage3_tree builds it
    by_id = {x["id"]: x for x in n}
    for x in n:
        p = x.get("parent")
        if p and p in by_id:
            by_id[p]["children"].append(x["id"])
    return n


def repaginate(n, dp=2, dy=-37.5):
    """Move every node on the page without changing a word. This is the noise a
    real reprint produces and the reason the projection exists."""
    for pv in n.get("provenance", []):
        pv["page"] = pv["page"] + dp
        pv["bbox"] = [pv["bbox"][0], pv["bbox"][1] + dy,
                      pv["bbox"][2], pv["bbox"][3] + dy]
    for t in n.get("text", []):
        t["p"] = t["p"] + dp
        t["b"] = [t["b"][0], t["b"][1] + dy, t["b"][2], t["b"][3] + dy]
    for c in n.get("grid", []):
        if "page" in c:
            c["page"] = c["page"] + dp
    return n


def amended_nodes():
    """base, repaginated end to end, plus exactly four substantive changes."""
    nodes = {x["id"]: x for x in base_nodes()}

    # 1. MODIFIED - the sentence is amended and carries an amendment record.
    s1 = nodes["B/9/9.32.3.8/(1)"]
    s1["text"][1] = tok(816, 493, "shall conform to Table 9.32.3.1.")
    s1["refs"][1] = {**s1["refs"][1], "text": "Table 9.32.3.1."}
    s1["amendment"] = [_amd("*")]

    # 2. ADDED - a new clause.
    c = node("B/9/9.32.3.8/(1)/(c)", "clause", "c", None,
             "B/9/9.32.3.8/(1)", 816, 457)
    c["text"] = [tok(816, 457, "the maximum sound level of the fan.")]
    c["amendment"] = [_amd("**")]
    nodes[c["id"]] = c

    # 3. REMOVED - a revoked sentence. Its parent article's `children` changes;
    #    the parent must NOT be reported, because children is derived.
    del nodes["B/9/9.32.3.9/(1)"]

    # 4. MODIFIED, amendment only - the table gains a record, text unchanged.
    nodes["B/9/table/9.32.3.1"]["amendment"] = [_amd("*")]

    # 5. MODIFIED, body only - an editorial reword carrying no marker and
    #    changing no ref. This is the commonest real amendment shape and it is
    #    the ONLY node here whose sole substantive difference is its text.
    #    Without it the recall half of the H10 control is unfalsifiable: the
    #    control that blanks `body` from the projection left every other seeded
    #    node still reported through its `refs` or `amendment` change, so recall
    #    stayed 1.0 and the mutation read NEVER FAILS. The fixture was too weak,
    #    not the check.
    nodes["APPA/A-9.32.3.8"]["text"] = [
        tok(120, 400, "This Article establishes the minimum required capacity.")]

    for n in nodes.values():
        repaginate(n)

    out = {x["id"]: x for x in nodes.values()}
    for x in out.values():
        x["children"] = []
    for x in sorted(out.values(), key=lambda z: z["id"]):
        p = x.get("parent")
        if p and p in out:
            out[p]["children"].append(x["id"])
    return list(out.values())


def meta(nodes, edition):
    """The `_meta` line, shaped as pipeline/vol2/stage10_merge.py writes it."""
    return {"_meta": True, "merged": True, "nodes": len(nodes),
            "edition": edition,
            "amendment_legend": LEGEND,
            "amendment_stats": {"markers_on_page": 3, "legend": len(LEGEND),
                                "attached": 3, "orphans": []},
            "fixture": "synthetic; not the Ontario Building Code"}


def write(path, nodes, edition):
    """gzip mtime pinned to 0 so the fixture is byte-deterministic and cannot
    itself be the reason M1 fails."""
    raw = [json.dumps(meta(nodes, edition), sort_keys=True, ensure_ascii=False)]
    raw += [json.dumps(n, sort_keys=True, ensure_ascii=False) for n in nodes]
    payload = ("\n".join(raw) + "\n").encode("utf-8")
    with open(path, "wb") as fh:
        with gzip.GzipFile(fileobj=fh, mode="wb", mtime=0) as gz:
            gz.write(payload)


SEED = {
    "expected_modified": ["B/9/9.32.3.8/(1)", "B/9/table/9.32.3.1",
                          "APPA/A-9.32.3.8"],
    "expected_added": ["B/9/9.32.3.8/(1)/(c)"],
    "expected_removed": ["B/9/9.32.3.9/(1)"],
    "expected_amendment_events": 3,
    "must_not_be_reported": ["B/9/9.32.3.9", "B/9/9.32.3.8"],
    "repaginated": True,
    "note": "the amended edition is repaginated end to end; every node's page "
            "and bbox differ, so a diff that does not project layout away "
            "reports all of them and scores precision near zero",
}


def main(argv=None):
    ap = argparse.ArgumentParser(description="build the MAINT diff fixtures")
    ap.add_argument("--out", default=DEFAULT_OUT)
    a = ap.parse_args(argv)
    os.makedirs(a.out, exist_ok=True)

    b, m = base_nodes(), amended_nodes()
    write(os.path.join(a.out, "base.jsonl.gz"), b, "fixture-base")
    write(os.path.join(a.out, "amended.jsonl.gz"), m, "fixture-amended")

    seed = dict(SEED)
    seed["expected_changed"] = sorted(set(seed["expected_modified"])
                                      | set(seed["expected_added"])
                                      | set(seed["expected_removed"]))
    seed["base_nodes"] = len(b)
    seed["amended_nodes"] = len(m)
    with open(os.path.join(a.out, "seed.json"), "w", encoding="utf-8") as fh:
        json.dump(seed, fh, sort_keys=True, indent=2)
        fh.write("\n")

    print(f"base    {len(b)} nodes -> {os.path.join(a.out, 'base.jsonl.gz')}")
    print(f"amended {len(m)} nodes -> {os.path.join(a.out, 'amended.jsonl.gz')}")
    print(f"seed    {len(seed['expected_changed'])} expected changes, "
          f"repaginated={seed['repaginated']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
