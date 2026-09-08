# Work package — G: Agent surface hardening

**Status in DAG:** `blocked`  ·  **Effort:** 1 week
**Depends on:** B  ·  **Unblocks:** FSCOPE

## Consumes

- `retrieval/lib/obc_agent_tools.py`
- `emitters/obc-vec.sqlite`

## Produces

- `retrieval/lib/obc_agent_tools.py (G1 hybrid search, G2 computed cannot-list)`
- `retrieval/checks/check38_capabilities.py`
- `retrieval/checks/check39_tools.py`
- `retrieval/refusal-evalset.json`

## Items

- **G1** — hybrid (vector ∪ BM25, RRF) inside obc_search; remove "no semantic index" from cannot
- **G2** — capabilities.cannot computed from graph state; check38 (G2c) proves every probe clears when its capability is seeded — DONE 2026-09-07
- **G3** — fixture + control per tool
- **G4** — refusal eval — hallucinated-applicability rate

## Gates to declare

- `G1`
- `G2`
- `G3`
- `G4`

Every gate that reports a ratio needs a mutation in `check35_controls.py` that drives it below its floor. The mutation targets the mechanism, never the ground truth. Untouched must exit 0; mutated must exit non-zero.

## Exit criteria

- G2's check has an H10 control — add an occupancy node, the applicability line must disappear from cannot
- hallucinated-applicability rate measured and near zero

## Completion checklist (PROTOCOL.md — none optional)

- [ ] 1 DECLARE   gates written to gates/GATES-G.md before code
- [ ] 2 BUILD     in a copy of the tree, never in the bag
- [ ] 3 MUTATE    every ratio gate registered in harden/checks/check35_controls.py; check35 PASS
- [ ] 4 INTEGRATE real paths, orchestration wired, superseded files moved not deleted
- [ ] 5 RE-BAG    bash ci/regenerate.sh; rebuild; provenance regenerated
- [ ] 6 VERIFY    python3 ci/run_gates.py from a CLEAN bag — every touched gate PASS, corpus mode
- [ ] 7 AUDIT     addendum: what moved, what did not, what broke, what was FOUND
- [ ] tracks.yaml updated: own status, and any new item discovered filed under its track

Returning a pack of loose files is step 2. It is not done.

---
Unofficial derived work. Current to 2025-01-16 (through O. Reg. 5/25). Not the official Building Code Compendium.
© King's Printer for Ontario, 2024. Reproduced with permission.