#!/usr/bin/env python3
"""S0: validate the declared OBC graph schema against itself and the emitted DB.

Modes:
  --schema-only   validate the schema's own closed-world invariants.
  --db PATH       ensure every emitted node type and edge kind is declared.
  --strict        additionally report model-shape defects.
  --json          emit a machine-readable summary line prefixed with ``JSON ``.

`NEGATIVE=1` removes a reverse label from one EdgeKind and passes only when the
schema validator detects that mutation. This path needs no corpus data.
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
_PKG = os.path.normpath(os.path.join(_HERE, "..", ".."))
SCHEMA = os.environ.get("OBC_SCHEMA", os.path.join(_PKG, "schema", "obc.linkml.yaml"))

CONTAINER, PROVISION, OTHER = "container", "provision", "other"


def load_schema(path=None):
    with open(path or SCHEMA) as fh:
        return yaml.safe_load(fh)


def node_types(schema):
    return schema["enums"]["NodeType"]["permissible_values"]


def edge_kinds(schema):
    return schema["enums"]["EdgeKind"]["permissible_values"]


def roles(schema):
    return {
        key: (value.get("annotations") or {}).get("role")
        for key, value in node_types(schema).items()
    }


def declared_types_of_class(cls):
    usage = ((cls.get("slot_usage") or {}).get("type") or {})
    if "equals_string" in usage:
        return {usage["equals_string"]}
    return {
        constraint["equals_string"]
        for constraint in usage.get("any_of", [])
        if "equals_string" in constraint
    }


def binding_target_types(schema):
    slot = schema["slots"].get("forms_part_of", {})
    raw = (slot.get("annotations") or {}).get("allowed_node_types", "")
    if isinstance(raw, dict):
        raw = raw.get("value", "")
    return tuple(x.strip() for x in str(raw).split(",") if x.strip())


def check_schema(schema):
    failures = []
    types = node_types(schema)
    kinds = edge_kinds(schema)
    role_map = roles(schema)

    for node_type, role in role_map.items():
        if role not in (CONTAINER, PROVISION, OTHER):
            failures.append(
                f"NodeType '{node_type}' has no valid role annotation (got {role!r})"
            )

    for kind, value in kinds.items():
        reverse = (value.get("annotations") or {}).get("reverse")
        if not reverse:
            failures.append(
                f"EdgeKind '{kind}' declares no reverse label; relation is not bidirectionally traversable"
            )

    for name, cls in schema["classes"].items():
        if (cls.get("annotations") or {}).get("closed") != "true":
            failures.append(f"class {name} is not annotated closed: true")

    concrete = {
        name: cls
        for name, cls in schema["classes"].items()
        if cls.get("is_a") == "Node"
    }
    covered, overlap = set(), set()
    for cls in concrete.values():
        declared = declared_types_of_class(cls)
        overlap |= covered & declared
        covered |= declared

    missing = set(types) - covered
    if missing:
        failures.append(
            f"NodeType values declared but assigned to no concrete Node class: {sorted(missing)}"
        )
    if overlap:
        failures.append(
            f"NodeType values claimed by two concrete Node classes: {sorted(overlap)}"
        )
    extra = covered - set(types)
    if extra:
        failures.append(
            f"classes constrain types absent from NodeType: {sorted(extra)}"
        )

    # Defect 1: containment and caption binding must be different relations.
    table_cls = schema["classes"].get("Table", {})
    if (table_cls.get("slot_usage") or {}).get("parent", {}).get("range") != "StructuralContainer":
        failures.append(
            "Table.parent is not narrowed to StructuralContainer; binding can be overloaded into containment"
        )
    binding_slot = schema["slots"].get("forms_part_of", {})
    if binding_slot.get("range") != "Node":
        failures.append("forms_part_of must range over Node; captions may bind above leaf Provision level")
    allowed = binding_target_types(schema)
    if not allowed:
        failures.append("forms_part_of declares no allowed_node_types")
    undeclared_allowed = set(allowed) - set(types)
    if undeclared_allowed:
        failures.append(
            f"forms_part_of allows undeclared node types: {sorted(undeclared_allowed)}"
        )
    holders = [
        name for name, cls in schema["classes"].items()
        if "forms_part_of" in (cls.get("slots") or [])
    ]
    if holders != ["Table"]:
        failures.append(f"forms_part_of is held by {holders}, must be Table alone")
    if "forms_part_of" not in kinds:
        failures.append("'forms_part_of' is not an EdgeKind")

    # Structural containers and text-bearing leaves remain disjoint even though
    # forms_part_of is allowed to target selected members of both groups.
    if (
        set(declared_types_of_class(schema["classes"]["StructuralContainer"]))
        & set(declared_types_of_class(schema["classes"]["Provision"]))
    ):
        failures.append("StructuralContainer and Provision overlap")

    # Defect 2: semantic relations share the Edge carrier.
    carriers = [
        name for name, cls in schema["classes"].items()
        if "kind" in (cls.get("slots") or [])
    ]
    if carriers != ["Edge"]:
        failures.append(f"edge kinds are carried by {carriers}, must be Edge alone")
    if "term" not in kinds:
        failures.append("'term' is not an EdgeKind")
    if not schema["classes"]["Edge"].get("unique_keys"):
        failures.append("Edge has no unique key; duplicate copies are representable")
    for name, cls in schema["classes"].items():
        for slot in (cls.get("slots") or []) + list((cls.get("attributes") or {})):
            if slot in ("terms", "term_resolved", "refs"):
                failures.append(
                    f"class {name} has slot '{slot}'; a second relation carrier is declared"
                )

    # Defect 3: Node itself carries only containment; all other node-to-node
    # relationships travel through Edge.
    node_slots = schema["classes"]["Node"]["slots"]
    node_relations = [
        slot for slot in node_slots
        if schema["slots"].get(slot, {}).get("range") == "Node"
    ]
    if sorted(node_relations) != ["children", "parent"]:
        failures.append(
            f"Node carries Node-ranged slots {sorted(node_relations)}; only parent/children are permitted"
        )
    if schema["slots"]["parent"].get("inverse") != "children":
        failures.append("parent does not declare inverse: children")
    if schema["slots"].get("dst", {}).get("range") != "Node":
        failures.append("Edge.dst does not range over Node")

    return failures


def measure(db_path, schema):
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    declared_types = set(node_types(schema))
    declared_kinds = set(edge_kinds(schema))

    rows = conn.execute("SELECT type, COUNT(*) FROM node GROUP BY type").fetchall()
    node_count = sum(count for _, count in rows) or 1
    unknown_types = {t: n for t, n in rows if t not in declared_types}
    type_share = 1.0 - sum(unknown_types.values()) / node_count

    kind_rows = conn.execute("SELECT kind, COUNT(*) FROM ref GROUP BY kind").fetchall()
    kinds = list(kind_rows)
    for table in ("term_resolved", "term"):
        exists = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)
        ).fetchone()
        if exists:
            kinds.append(
                ("term", conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])
            )
            break

    edge_count = sum(count for _, count in kinds) or 1
    unknown_kinds = {k: n for k, n in kinds if k not in declared_kinds}
    kind_share = 1.0 - sum(unknown_kinds.values()) / edge_count
    conn.close()

    return {
        "nodes": node_count,
        "edges": edge_count,
        "declared_type_share": type_share,
        "declared_kind_share": kind_share,
        "undeclared_types": unknown_types,
        "undeclared_kinds": unknown_kinds,
    }


def conformance(db_path, schema):
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    allowed = binding_target_types(schema)
    out = []

    # A table physically nested under a level that can also be a semantic
    # binding target is the legacy overloaded representation. R4 stage5 puts V1
    # tables under their Part instead.
    placeholders = ",".join("?" * len(allowed))
    count = conn.execute(
        f"""SELECT COUNT(*) FROM node t JOIN node p ON p.id=t.parent
            WHERE t.type='table' AND p.type IN ({placeholders})""",
        allowed,
    ).fetchone()[0]
    out.append((
        "D1 table.parent carries semantic binding",
        count,
        "table.parent must be structural containment only",
    ))

    binding_count = conn.execute(
        "SELECT COUNT(*) FROM ref WHERE kind='forms_part_of' AND dst IS NOT NULL"
    ).fetchone()[0]
    out.append((
        "D1 forms_part_of not emitted",
        0 if binding_count else 1,
        "canonical table binding must be emitted as ref.kind=forms_part_of",
    ))

    invalid_binding = conn.execute(
        f"""SELECT COUNT(*)
            FROM ref r
            LEFT JOIN node s ON s.id=r.src
            LEFT JOIN node d ON d.id=r.dst
            WHERE r.kind='forms_part_of'
              AND (s.type IS NOT 'table' OR d.type NOT IN ({placeholders}))""",
        allowed,
    ).fetchone()[0]
    out.append((
        "D1 invalid forms_part_of endpoint",
        invalid_binding,
        f"forms_part_of target type must be one of {allowed}",
    ))

    # Transitional storage for term relations remains visible here. Track B may
    # leave this as an explicitly deferred defect, but it cannot be hidden.
    carriers = [
        row[0]
        for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' "
            "AND name IN ('ref','term','term_resolved')"
        )
    ]
    out.append((
        "D2 edge carriers beyond one",
        max(0, len(carriers) - 1),
        f"found {carriers}; one relation should have one carrier",
    ))

    if "term_resolved" in carriers:
        count = conn.execute(
            """SELECT COUNT(*) FROM term_resolved t
               LEFT JOIN node n ON n.id=t.dst
               WHERE n.type IS NOT 'defined_term'"""
        ).fetchone()[0]
        out.append((
            "D2 term edge not landing on a defined_term",
            count,
            "term edges must resolve to defined_term nodes",
        ))

    count = conn.execute(
        """SELECT COUNT(*) FROM ref r JOIN node n ON n.id=r.src
           WHERE r.kind='cap_ref' AND n.type='table'"""
    ).fetchone()[0]
    out.append((
        "D3 cap_ref emitted from a table",
        count,
        "cap_ref is a prose citation, not a table binding",
    ))

    conn.close()
    return out


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", default=os.environ.get("OBC_DB", "emitters/obc-mod.sqlite"))
    parser.add_argument("--schema", default=SCHEMA)
    parser.add_argument("--schema-only", action="store_true")
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    schema = load_schema(args.schema)
    failures = check_schema(schema)

    if os.environ.get("NEGATIVE") == "1":
        key = sorted(edge_kinds(schema))[0]
        edge_kinds(schema)[key].get("annotations", {}).pop("reverse", None)
        after = check_schema(schema)
        ok = len(after) > len(failures)
        print(
            f"negative control: stripped reverse from EdgeKind '{key}' -> "
            f"{len(failures)} failures became {len(after)}"
        )
        print("RESULT:", "PASS" if ok else "FAIL - schema validator cannot go red")
        return 0 if ok else 1

    print(f"schema              : {args.schema}")
    print(f"node types declared : {len(node_types(schema))}")
    print(f"edge kinds declared : {len(edge_kinds(schema))}")
    for failure in failures:
        print(f"   SCHEMA  {failure}")

    result = {
        "declared_type_share": None,
        "declared_kind_share": None,
        "schema_failures": len(failures),
    }

    if not args.schema_only:
        if not os.path.exists(args.db):
            print(f"\nno database at {args.db} - run: bash ci/fetch_data.sh")
            print("RESULT: FAIL - S0 cannot be established without the graph")
            return 1

        measured = measure(args.db, schema)
        result.update({
            "declared_type_share": measured["declared_type_share"],
            "declared_kind_share": measured["declared_kind_share"],
            "nodes": measured["nodes"],
            "edges": measured["edges"],
        })

        print(f"\nnodes                 : {measured['nodes']}")
        print(f"edges (ref + term)     : {measured['edges']}")
        print(f"declared_type_share    : {measured['declared_type_share']:.6f}")
        print(f"declared_kind_share    : {measured['declared_kind_share']:.6f}")

        for node_type, count in sorted(measured["undeclared_types"].items()):
            failures.append(f"undeclared node type {node_type!r} on {count} nodes")
            print(f"   UNDECLARED TYPE  {node_type!r}  {count} nodes")
        for kind, count in sorted(measured["undeclared_kinds"].items()):
            failures.append(f"undeclared edge kind {kind!r} on {count} edges")
            print(f"   UNDECLARED KIND  {kind!r}  {count} edges")

        if args.strict:
            print("\nconformance to declared shape:")
            for name, count, why in conformance(args.db, schema):
                print(f"   {'FAIL' if count else 'ok  '}  {name:<44} {count}")
                if count:
                    print(f"          {why}")
                    failures.append(f"{name}: {count}")

    result["conforms"] = 0.0 if failures else 1.0
    result["exit_zero"] = 0.0 if failures else 1.0
    if args.json:
        print("JSON " + json.dumps(result, sort_keys=True))

    print("\nRESULT:", "PASS" if not failures else f"FAIL {len(failures)} - " + "; ".join(failures[:4]))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
