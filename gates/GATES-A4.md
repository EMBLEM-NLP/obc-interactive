# Gates — A4 (declared schema)

This ledger activates the declared-schema track. The schema source is
`schema/obc.linkml.yaml`; the executable validator is
`harden/checks/check36_schema.py`.

## Gates

- [ ] **S0 — emitted graph uses only declared node types and edge kinds.**
  - CHECK: `python3 harden/checks/check36_schema.py --db emitters/obc-mod.sqlite`
  - EXPECT: `declared_type_share == 1.000000` and
    `declared_kind_share == 1.000000`, exit 0.
  - A node or edge carrying an undeclared enum value must make this fail.

- [ ] **S0-a — negative control proves the schema validator can go red.**
  - CHECK: `NEGATIVE=1 python3 harden/checks/check36_schema.py --schema-only`
  - EXPECT: the control strips one reverse relation declaration and the validator
    detects the mutation; the control command itself exits 0 only when detection
    succeeds.

- [ ] **S0-b — schema is internally closed and well formed.**
  - CHECK: `python3 harden/checks/check36_schema.py --schema-only`
  - EXPECT: exit 0.
  - Required invariants include:
    - every `NodeType` belongs to exactly one concrete Node subclass,
    - every `EdgeKind` has a reverse traversal label,
    - every class is closed,
    - table containment is distinct from `forms_part_of`,
    - term usage is an `EdgeKind` rather than a parallel relation carrier,
    - Node-ranged relationships outside containment are carried by `Edge`.

- [ ] **S0-c — current emitted graph conforms to the declared shape.**
  - CHECK: `python3 harden/checks/check36_schema.py --db emitters/obc-mod.sqlite --strict`
  - EXPECT: this remains informational/expected-red until Track B / issue #5
    removes the known source-model defects identified by the validator.

## Completion rule

A4 may be marked complete when S0, S0-a and S0-b pass against the hydrated
corpus in CI. S0-c is intentionally owned by Track B / issue #5 and must not be
silently weakened to make A4 green.

## Provenance

The schema was authored from the existing pipeline type/edge vocabulary and is
validated against the emitted graph rather than inferred from a single database
snapshot. The canonical graph remains `model/docgraph-merged.jsonl.gz`.
