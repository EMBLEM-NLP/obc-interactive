#!/usr/bin/env python3
"""
check36_schema.py - S0. The graph conforms to a declared schema, and an
undeclared node type fails validation.

HANDOFF NOTE - THIS FILE IS NOT AT ITS REAL PATH
------------------------------------------------
A4 `produces` names `harden/checks/check36_schema.py`. That path is inside the
protected set (`harden/checks/check41_machinery.py` PROTECTED,
`.claude/hooks/protect-checks.sh`) and the guard refused the write, correctly:
an executor that writes the check grading its own work has moved a gate, not
passed one. So this sits at `schema/proposed/`. A human must review it and
install it at `harden/checks/check36_schema.py`. Until then S0 is undeclared
and A4 is not done.

It has never been run against data. This container holds the control plane and
none of the 323 MB of derived artifacts: `emitters/obc-mod.sqlite` is absent and
`obc_capabilities` reports `available: false`. Only `--schema-only` was
exercised here. What it needs in order to run for real:

    emitters/obc-mod.sqlite   (bash ci/fetch_data.sh)
    schema/obc.linkml.yaml    (present)
    pyyaml                    (present; linkml itself is NOT needed)

Why it does not import linkml
-----------------------------
`linkml` is not in requirements.txt and is not installed. Rather than add a
heavy dependency to the gate path, this validates the subset of LinkML the
schema actually uses - closed enums, closed classes, range narrowing, inverse
pairs, unique keys - directly against the SQLite rows. If `linkml` is later
pinned, `--schema-only` should be extended to also run `linkml-lint`; that is a
strictly additional assertion, not a replacement.

Three modes
-----------
  --schema-only   the schema's own well-formedness. No database. Runs anywhere.
  --db PATH       S0 proper: every emitted node type and edge kind is declared.
  --strict        adds conformance of today's emitted database to the declared
                  shape. EXPECTED TO FAIL until Track B fixes the model at
                  source; the failures are the A4 -> B work list, not bugs here.

    python3 check36_schema.py --schema-only
    python3 check36_schema.py --db emitters/obc-mod.sqlite
    python3 check36_schema.py --db emitters/obc-mod.sqlite --json
    NEGATIVE=1 python3 check36_schema.py --schema-only    # must FAIL
"""

import argparse
import json
import os
import sqlite3
import sys

try:
    import yaml
except ImportError:
    sys.exit("check36 needs pyyaml (it is in requirements.txt)")

_HERE = os.path.dirname(os.path.abspath(__file__))
# tolerate both the proposed location (schema/proposed/) and the real one
# (harden/checks/); the schema is at <pkg>/schema/obc.linkml.yaml either way.
_PKG = os.path.normpath(os.path.join(_HERE, "..", ".."))
SCHEMA = os.environ.get("OBC_SCHEMA", os.path.join(_PKG, "schema", "obc.linkml.yaml"))

CONTAINER, PROVISION, OTHER = "container", "provision", "other"


# --------------------------------------------------------------------------
# schema reading
# --------------------------------------------------------------------------

def load_schema(path=None):
    with open(path or SCHEMA) as fh:
        return yaml.safe_load(fh)


def node_types(s):
    return s["enums"]["NodeType"]["permissible_values"]


def edge_kinds(s):
    return s["enums"]["EdgeKind"]["permissible_values"]


def roles(s):
    """type -> role, from the NodeType annotations. The role partition is what
    makes StructuralContainer and Provision disjoint, which is what makes
    defect 1 unrepresentable."""
    return {k: (v.get("annotations") or {}).get("role") for k, v in node_types(s).items()}


def declared_types_of_class(cls):
    """The NodeType values a class constrains itself to, read out of
    slot_usage.type. Returns a set."""
    t = ((cls.get("slot_usage") or {}).get("type") or {})
    if "equals_string" in t:
        return {t["equals_string"]}
    return {c["equals_string"] for c in t.get("any_of", []) if "equals_string" in c}


# --------------------------------------------------------------------------
# S0-b: the schema validates itself
# --------------------------------------------------------------------------

def check_schema(s):
    f = []
    nt, ek, rl = node_types(s), edge_kinds(s), roles(s)

    for t, r in rl.items():
        if r not in (CONTAINER, PROVISION, OTHER):
            f.append(f"NodeType '{t}' has no role annotation (got {r!r})")

    # DEFECT 3: no edge kind may exist without a declared reverse-lookup label.
    for k, v in ek.items():
        rev = (v.get("annotations") or {}).get("reverse")
        if not rev:
            f.append(f"EdgeKind '{k}' declares no reverse: label - "
                     f"defect 3, an edge kind with no reverse-lookup path")

    # every class closed; a widened class is how an undeclared relation gets in
    for name, c in s["classes"].items():
        if (c.get("annotations") or {}).get("closed") != "true":
            f.append(f"class {name} is not annotated closed: true")

    # the role partition must be total and disjoint over the concrete Node
    # subclasses. Adding a NodeType without giving it a class fails here.
    concrete = {n: c for n, c in s["classes"].items()
                if c.get("is_a") == "Node"}
    covered, overlap = set(), set()
    for n, c in concrete.items():
        d = declared_types_of_class(c)
        overlap |= (covered & d)
        covered |= d
    missing = set(nt) - covered
    if missing:
        f.append(f"NodeType values declared but assigned to no class: {sorted(missing)}")
    if overlap:
        f.append(f"NodeType values claimed by two classes: {sorted(overlap)}")
    if covered - set(nt):
        f.append(f"classes constrain types absent from NodeType: {sorted(covered - set(nt))}")

    # DEFECT 1: the table binding has exactly one home, and it is not `parent`.
    tbl = s["classes"].get("Table", {})
    if (tbl.get("slot_usage") or {}).get("parent", {}).get("range") != "StructuralContainer":
        f.append("Table.parent is not narrowed to StructuralContainer - "
                 "defect 1, the binding can be written into parent")
    if s["slots"].get("forms_part_of", {}).get("range") != "Provision":
        f.append("forms_part_of does not range over Provision")
    holders = [n for n, c in s["classes"].items() if "forms_part_of" in (c.get("slots") or [])]
    if holders != ["Table"]:
        f.append(f"forms_part_of is held by {holders}, must be Table alone - "
                 "defect 1, two places to write one binding")
    if set(declared_types_of_class(s["classes"]["StructuralContainer"])) & \
       set(declared_types_of_class(s["classes"]["Provision"])):
        f.append("StructuralContainer and Provision overlap; narrowing Table.parent "
                 "no longer excludes provisions")

    # DEFECT 2: one edge carrier, one vocabulary, no resolved-copy class.
    carriers = [n for n, c in s["classes"].items() if "kind" in (c.get("slots") or [])]
    if carriers != ["Edge"]:
        f.append(f"edge kinds are carried by {carriers}, must be Edge alone - "
                 "defect 2, citation and term usage split across classes")
    if "term" not in ek:
        f.append("'term' is not an EdgeKind - defect 2, definition usage is not a citation")
    if not s["classes"]["Edge"].get("unique_keys"):
        f.append("Edge has no unique_keys - a resolved and an unresolved copy of the "
                 "same citation could coexist")
    for name, c in s["classes"].items():
        for slot in (c.get("slots") or []) + list((c.get("attributes") or {})):
            if slot in ("terms", "term_resolved", "refs"):
                f.append(f"class {name} has slot '{slot}' - defect 2, a second edge container")

    # DEFECT 3, second half: Node exposes exactly one Node-ranged relation and
    # it is the containment inverse pair. Everything else must be an Edge.
    nodeslots = s["classes"]["Node"]["slots"]
    rel = [x for x in nodeslots if s["slots"].get(x, {}).get("range") == "Node"]
    if sorted(rel) != ["children", "parent"]:
        f.append(f"Node carries Node-ranged slots {sorted(rel)}; only the "
                 "parent/children inverse pair is permitted, or an edge kind "
                 "can be added as a slot and bypass EdgeKind")
    if s["slots"]["parent"].get("inverse") != "children":
        f.append("parent declares no inverse: children - containment has no reverse path")
    if s["slots"].get("dst", {}).get("range") != "Node":
        f.append("Edge.dst does not range over Node - there is no reverse index")

    return f


# --------------------------------------------------------------------------
# S0: the emitted database uses only declared types and kinds
# --------------------------------------------------------------------------

def measure(db, s):
    c = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    nt, ek = set(node_types(s)), set(edge_kinds(s))

    rows = c.execute("SELECT type, COUNT(*) FROM node GROUP BY type").fetchall()
    total = sum(n for _, n in rows) or 1
    bad_t = {t: n for t, n in rows if t not in nt}
    type_share = 1.0 - sum(bad_t.values()) / total

    kinds = [(k, n) for k, n in
             c.execute("SELECT kind, COUNT(*) FROM ref GROUP BY kind").fetchall()]
    # `term` rows are edges too, whatever table they were emitted into
    for tbl in ("term_resolved", "term"):
        if c.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
                     (tbl,)).fetchone():
            kinds.append(("term", c.execute(f"SELECT COUNT(*) FROM {tbl}").fetchone()[0]))
            break
    ktotal = sum(n for _, n in kinds) or 1
    bad_k = {k: n for k, n in kinds if k not in ek}
    kind_share = 1.0 - sum(bad_k.values()) / ktotal

    c.close()
    return {"nodes": total, "edges": ktotal,
            "declared_type_share": type_share, "declared_kind_share": kind_share,
            "undeclared_types": bad_t, "undeclared_kinds": bad_k}


# --------------------------------------------------------------------------
# --strict: conformance of today's database. Expected to fail until Track B.
# --------------------------------------------------------------------------

def conformance(db, s):
    c = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    rl = roles(s)
    prov = tuple(t for t, r in rl.items() if r == PROVISION)
    out = []

    n = c.execute(f"""SELECT COUNT(*) FROM node t JOIN node p ON p.id = t.parent
                      WHERE t.type='table' AND p.type IN ({','.join('?' * len(prov))})""",
                  prov).fetchone()[0]
    out.append(("D1 table.parent is a provision", n,
                "pipeline/stage5_bind.py:81 `parent = target or pid` overloads parent "
                "with the caption binding; declared shape says StructuralContainer"))

    has_binding = bool(c.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='table_binding'").fetchone())
    cols = {r[1] for r in c.execute("PRAGMA table_info(node)")}
    out.append(("D1 forms_part_of not emitted",
                0 if (has_binding or "forms_part_of" in cols) else 1,
                "stage5_bind writes node['forming_part_of'] but "
                "pipeline/emitters/stage15_sqlite.py's node INSERT has no such column, "
                "so the binding survives only in the overloaded parent"))

    carriers = [r[0] for r in c.execute(
        "SELECT name FROM sqlite_master WHERE type='table' "
        "AND name IN ('ref','term','term_resolved')")]
    out.append(("D2 edge carriers beyond one", max(0, len(carriers) - 1),
                f"found {carriers}; one Edge class means one carrier, so "
                "'what does this cite' is not a UNION the caller must remember"))

    if "term_resolved" in carriers:
        n = c.execute("""SELECT COUNT(*) FROM term_resolved t
                         LEFT JOIN node n ON n.id = t.dst
                         WHERE n.type IS NOT 'defined_term'""").fetchone()[0]
        out.append(("D2 term edge not landing on a defined_term", n,
                    "Edge rule R2_term_always_resolves_to_a_definition"))

    n = c.execute("""SELECT COUNT(*) FROM ref r JOIN node n ON n.id = r.src
                     WHERE r.kind='cap_ref' AND n.type='table'""").fetchone()[0]
    out.append(("D3 cap_ref emitted from a table", n,
                "Edge rule R3_cap_ref_is_never_a_binding"))

    c.close()
    return out


# --------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default=os.environ.get("OBC_DB", "emitters/obc-mod.sqlite"))
    ap.add_argument("--schema", default=SCHEMA)
    ap.add_argument("--schema-only", action="store_true")
    ap.add_argument("--strict", action="store_true")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()

    s = load_schema(a.schema)
    fails = check_schema(s)

    if os.environ.get("NEGATIVE") == "1":
        # remove a reverse label; the schema check must go red or it is a light
        k = sorted(edge_kinds(s))[0]
        edge_kinds(s)[k].get("annotations", {}).pop("reverse", None)
        n = len(check_schema(s))
        ok = n > len(fails)
        print(f"negative control: stripped reverse: from EdgeKind '{k}' -> "
              f"{len(fails)} failures became {n}")
        print("RESULT:", "PASS" if ok else "FAIL - the schema check cannot go red")
        return 0 if ok else 1

    print(f"schema            : {a.schema}")
    print(f"node types declared: {len(node_types(s))}")
    print(f"edge kinds declared: {len(edge_kinds(s))}")
    for x in fails:
        print(f"   SCHEMA  {x}")

    result = {"declared_type_share": None, "declared_kind_share": None,
              "schema_failures": len(fails)}

    if not a.schema_only:
        if not os.path.exists(a.db):
            print(f"\nno database at {a.db} - run: bash ci/fetch_data.sh")
            print("RESULT: FAIL - S0 cannot be established without the graph")
            return 1
        m = measure(a.db, s)
        result.update({k: m[k] for k in ("declared_type_share", "declared_kind_share")})
        result["nodes"], result["edges"] = m["nodes"], m["edges"]
        print(f"\nnodes                : {m['nodes']}")
        print(f"edges (ref + term)   : {m['edges']}")
        print(f"declared_type_share  : {m['declared_type_share']:.6f}")
        print(f"declared_kind_share  : {m['declared_kind_share']:.6f}")
        for t, n in sorted(m["undeclared_types"].items()):
            fails.append(f"undeclared node type {t!r} on {n} nodes")
            print(f"   UNDECLARED TYPE  {t!r}  {n} nodes")
        for k, n in sorted(m["undeclared_kinds"].items()):
            fails.append(f"undeclared edge kind {k!r} on {n} edges")
            print(f"   UNDECLARED KIND  {k!r}  {n} edges")

        if a.strict:
            print("\nconformance to the declared shape (Track B owns the fixes):")
            for name, n, why in conformance(a.db, s):
                print(f"   {'FAIL' if n else 'ok  '}  {name:<44} {n}")
                if n:
                    print(f"          {why}")
                    fails.append(f"{name}: {n}")

    result["conforms"] = 0.0 if fails else 1.0
    result["exit_zero"] = 0.0 if fails else 1.0
    if a.json:
        print("JSON " + json.dumps(result, sort_keys=True))
    print("\nRESULT:", "PASS" if not fails else f"FAIL {len(fails)} - " + "; ".join(fails[:4]))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
