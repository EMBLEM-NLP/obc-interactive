#!/usr/bin/env python3
"""
diff_editions.py - MAINT. Diff two editions of the document graph so an
amendment can be reviewed by reading only what changed.

Why a raw JSON diff does not work
---------------------------------
The graph record carries where the text sat on the page as well as what it
said: `provenance[].page`, `provenance[].bbox`, and `p`/`b` on every text
token. Between two printings of the Compendium all of those move for every
node, because the Ministry repaginates. A diff over the raw records therefore
reports 27,421 changed nodes for an amendment that changed four sentences, and
a review queue of 27,421 is not a review queue. The tool is discarded on first
use and the amendment ships unreviewed - the same outcome as a diff that
reports nothing, reached from the opposite direction.

So this tool diffs a declared SUBSTANTIVE PROJECTION of each node and accounts
for layout drift separately and by count. `substance()` below is the whole
definition of "what counts as a change", and it is deliberately one function in
one place so that it can be read, argued with, and mutated by a control.

What is substantive
    id, type, number, heading, parent, volume    identity and place in the tree
    body                                         the joined, whitespace-normalised text
    italics                                      defined-term runs; the definition changes the meaning
    refs                                         (kind, text, target, why), sorted
    terms                                        (term, target), sorted
    amendment                                    (marker, kind, instrument, effective), sorted
    grid                                         table cells by (r, c), text; page dropped

What is layout, and excluded
    provenance                                   page and bbox
    text token `p` and `b`                       page and bbox per token
    children                                     derived from parent; diffing both reports one fact twice

`body` is compared as normalised joined text rather than as a token list on
purpose. A reflow can re-split one sentence across a different number of lines
without changing a word of it; token-list equality would call that a change and
it is not one.

Nothing here is a claim about the Code. It is a claim about two files.

    python3 tools/diff_editions.py OLD.jsonl.gz NEW.jsonl.gz
    python3 tools/diff_editions.py OLD NEW --format text
    python3 tools/diff_editions.py OLD NEW -o diff.json
    python3 tools/diff_editions.py OLD NEW --amendments-only

Paths resolve from the package root with an env override (R7): OBC_GRAPH names
the default OLD when only NEW is given.
"""
import argparse
import gzip
import hashlib
import io
import json
import os
import re
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.normpath(os.path.join(_HERE, ".."))

# ---------------------------------------------------------------------------
# The projection. These three constants ARE the definition of "a change".
# The H10 control for M2 mutates them - emptying LAYOUT_FIELDS makes every
# repaginated node register as changed and precision collapses; that is the
# reason they are data rather than inline in the function body.
# ---------------------------------------------------------------------------
LAYOUT_FIELDS = ("provenance",)
LAYOUT_TOKEN_KEYS = ("p", "b")
DERIVED_FIELDS = ("children",)

# Compared one by one, so the report says WHICH part of a node moved.
SUBSTANTIVE_FIELDS = ("type", "number", "heading", "parent", "volume",
                      "body", "italics", "refs", "terms", "amendment", "grid")

_WS = re.compile(r"\s+")


def _norm(s):
    return _WS.sub(" ", (s or "").strip())


def load(path):
    """Read a docgraph JSONL, gzipped or not. Returns (meta, nodes, order).

    Mirrors pipeline/emitters/emit_common.py:load_graph, extended to accept a
    plain .jsonl so a fixture need not be a binary blob in git.
    """
    opener = gzip.open if str(path).endswith(".gz") else io.open
    meta, nodes, order = None, {}, []
    with opener(path, "rt", encoding="utf-8") as fh:
        for ln, line in enumerate(fh, 1):
            line = line.strip()
            if not line:
                continue
            try:
                r = json.loads(line)
            except json.JSONDecodeError as e:
                raise SystemExit(f"diff_editions: {path}:{ln}: not JSON: {e}")
            if r.get("_meta"):
                meta = r
                continue
            if "id" not in r:
                raise SystemExit(f"diff_editions: {path}:{ln}: record has no `id`")
            if r["id"] in nodes:
                raise SystemExit(f"diff_editions: {path}:{ln}: duplicate id {r['id']!r}")
            nodes[r["id"]] = r
            order.append(r["id"])
    return meta, nodes, order


def _tokens(n):
    return n.get("text") or []


def body(n):
    """Joined, whitespace-normalised text. emit_common.node_text, normalised."""
    return _norm(" ".join(t.get("t", "") for t in _tokens(n)))


def italics(n):
    """Defined-term runs, deduplicated and sorted. stage3_tree writes `it` as a
    list of runs; a bare truthy value is tolerated and ignored."""
    out = set()
    for t in _tokens(n):
        it = t.get("it")
        if isinstance(it, (list, tuple)):
            out.update(_norm(x) for x in it if _norm(x))
    return sorted(out)


def _refs(n):
    return sorted([r.get("kind"), _norm(r.get("text")), r.get("target"), r.get("why")]
                  for r in (n.get("refs") or []))


def _terms(n):
    return sorted([t.get("term"), t.get("target")] for t in (n.get("terms") or []))


def _amendment(n):
    return sorted([a.get("marker"), a.get("kind"), a.get("instrument"), a.get("effective")]
                  for a in (n.get("amendment") or []))


def _grid(n):
    """Table cells. `page` is dropped: a table that moves to the next page is
    not an amendment to the table."""
    return sorted([c.get("r"), c.get("c"), c.get("rowspan"), c.get("colspan"),
                   _norm(c.get("text"))] for c in (n.get("grid") or []))


# Node keys the explicit projection above already accounts for. Anything else
# on a record is carried through UNLESS it is named as layout or derived, so a
# field added to the graph later is diffed loudly rather than dropped silently.
_REPRESENTED = {"id", "type", "number", "heading", "parent", "volume",
                "text", "refs", "terms", "amendment", "grid"}
_TOKEN_REPRESENTED = {"t", "it"}


def substance(n):
    """The projection every comparison in this tool is made over.

    LAYOUT_FIELDS and LAYOUT_TOKEN_KEYS name what is EXCLUDED. Emptying either
    lets layout back into the projection, so every repaginated node registers
    as changed and M2's precision collapses. That is what the H10 control
    mutates, and the default sense must therefore be exclusion - an earlier
    revision of this function had it inverted and added the layout fields in,
    which reported all 15 fixture nodes as modified.
    """
    s = {"type": n.get("type"), "number": n.get("number"),
         "heading": _norm(n.get("heading")) or None, "parent": n.get("parent"),
         "volume": n.get("volume"), "body": body(n), "italics": italics(n),
         "refs": _refs(n), "terms": _terms(n), "amendment": _amendment(n),
         "grid": _grid(n)}
    for k, v in n.items():
        if k in _REPRESENTED or k in DERIVED_FIELDS or k in LAYOUT_FIELDS:
            continue
        s[k] = v
    extra = [{kk: vv for kk, vv in sorted(t.items())
              if kk not in _TOKEN_REPRESENTED and kk not in LAYOUT_TOKEN_KEYS}
             for t in _tokens(n)]
    if any(extra):
        s["_token_layout"] = extra
    return s


def _raw(n):
    """Everything except the derived children list, for layout-drift detection."""
    return {k: v for k, v in sorted(n.items()) if k not in DERIVED_FIELDS}


def diff(old_path, new_path):
    o_meta, o_nodes, _ = load(old_path)
    n_meta, n_nodes, _ = load(new_path)

    o_ids, n_ids = set(o_nodes), set(n_nodes)
    added = sorted(n_ids - o_ids)
    removed = sorted(o_ids - n_ids)

    modified, layout_only = [], []
    for nid in sorted(o_ids & n_ids):
        a, b = substance(o_nodes[nid]), substance(n_nodes[nid])
        if a == b:
            if _raw(o_nodes[nid]) != _raw(n_nodes[nid]):
                layout_only.append(nid)
            continue
        fields = sorted(k for k in set(a) | set(b) if a.get(k) != b.get(k))
        entry = {"id": nid, "type": b.get("type"), "fields": fields}
        if "body" in fields:
            entry["body_before"] = a.get("body")
            entry["body_after"] = b.get("body")
        modified.append(entry)

    # AmendmentEvents: the tie to the 144 amendment records already in the graph.
    events = []
    for nid in sorted(n_ids):
        before = {tuple(x) for x in _amendment(o_nodes[nid])} if nid in o_nodes else set()
        after = {tuple(x) for x in _amendment(n_nodes[nid])}
        for m in sorted(after - before):
            events.append({"node": nid, "change": "added", "marker": m[0],
                           "kind": m[1], "instrument": m[2], "effective": m[3]})
        for m in sorted(before - after):
            events.append({"node": nid, "change": "removed", "marker": m[0],
                           "kind": m[1], "instrument": m[2], "effective": m[3]})
    for nid in sorted(o_ids - n_ids):
        for m in sorted({tuple(x) for x in _amendment(o_nodes[nid])}):
            events.append({"node": nid, "change": "node-removed", "marker": m[0],
                           "kind": m[1], "instrument": m[2], "effective": m[3]})

    changed = sorted(set(added) | set(removed) | {m["id"] for m in modified})
    return {
        "tool": "tools/diff_editions.py",
        "projection": {"layout_fields": sorted(LAYOUT_FIELDS),
                       "layout_token_keys": sorted(LAYOUT_TOKEN_KEYS),
                       "derived_fields": sorted(DERIVED_FIELDS),
                       "substantive_fields": sorted(SUBSTANTIVE_FIELDS)},
        "old": {"path": os.path.basename(str(old_path)), "nodes": len(o_nodes)},
        "new": {"path": os.path.basename(str(new_path)), "nodes": len(n_nodes)},
        "meta_changed": sorted(k for k in set(o_meta or {}) | set(n_meta or {})
                               if (o_meta or {}).get(k) != (n_meta or {}).get(k)),
        "summary": {"added": len(added), "removed": len(removed),
                    "modified": len(modified), "layout_only": len(layout_only),
                    "changed_nodes": len(changed),
                    "amendment_events": len(events)},
        "added": added,
        "removed": removed,
        "modified": modified,
        "layout_only": layout_only,
        "amendment_events": events,
        "changed_nodes": changed,
    }


def render(report):
    """Canonical bytes. sort_keys, so the digest covers the whole artifact and
    not whatever order dict insertion happened to take (R5)."""
    return json.dumps(report, sort_keys=True, ensure_ascii=False, indent=2) + "\n"


def as_text(r):
    s, out = r["summary"], []
    out.append(f"{r['old']['path']} ({r['old']['nodes']} nodes)  ->  "
               f"{r['new']['path']} ({r['new']['nodes']} nodes)")
    out.append(f"added {s['added']}  removed {s['removed']}  modified {s['modified']}"
               f"  layout-only {s['layout_only']}")
    out.append(f"amendment events: {s['amendment_events']}")
    if r["meta_changed"]:
        out.append("meta keys changed: " + ", ".join(r["meta_changed"]))
    for nid in r["added"]:
        out.append(f"  + {nid}")
    for nid in r["removed"]:
        out.append(f"  - {nid}")
    for m in r["modified"]:
        out.append(f"  ~ {m['id']}  [{', '.join(m['fields'])}]")
        if "body_before" in m:
            out.append(f"      was: {m['body_before'][:160]}")
            out.append(f"      now: {m['body_after'][:160]}")
    for e in r["amendment_events"]:
        out.append(f"  ! {e['node']}  {e['change']} {e['marker']} "
                   f"({e['kind']}, {e['instrument']}, eff. {e['effective']})")
    return "\n".join(out) + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="diff two editions of the OBC document graph",
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("old", nargs="?", default=os.environ.get(
        "OBC_GRAPH", os.path.join(PKG, "model", "docgraph-merged.jsonl.gz")))
    ap.add_argument("new")
    ap.add_argument("-o", "--out", help="write the JSON report here (default stdout)")
    ap.add_argument("--format", choices=("json", "text"), default="json")
    ap.add_argument("--amendments-only", action="store_true",
                    help="report only nodes whose amendment records changed")
    ap.add_argument("--digest", action="store_true",
                    help="print only the sha256 of the canonical JSON report")
    a = ap.parse_args(argv)

    for p in (a.old, a.new):
        if not os.path.isfile(p):
            sys.exit(f"diff_editions: no such edition: {p}\n"
                     f"  the derived graph is not kept in git; run: bash ci/fetch_data.sh")

    r = diff(a.old, a.new)
    if a.amendments_only:
        keep = {e["node"] for e in r["amendment_events"]}
        r["added"] = [n for n in r["added"] if n in keep]
        r["removed"] = [n for n in r["removed"] if n in keep]
        r["modified"] = [m for m in r["modified"] if m["id"] in keep]
        r["layout_only"] = []
        r["changed_nodes"] = sorted(keep)
        r["summary"] = {**r["summary"], "added": len(r["added"]),
                        "removed": len(r["removed"]), "modified": len(r["modified"]),
                        "layout_only": 0, "changed_nodes": len(keep)}

    payload = render(r)
    if a.digest:
        print(hashlib.sha256(payload.encode()).hexdigest())
        return 0
    if a.out:
        with open(a.out, "w", encoding="utf-8") as fh:
            fh.write(payload)
        print(f"-> {a.out}  ({r['summary']['changed_nodes']} changed nodes, "
              f"{r['summary']['layout_only']} layout-only)")
    else:
        sys.stdout.write(payload if a.format == "json" else as_text(r))
    return 0


if __name__ == "__main__":
    sys.exit(main())
