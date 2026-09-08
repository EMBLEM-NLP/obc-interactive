# Work package — G: Agent surface hardening

**Status in DAG:** `blocked`  ·  **Human effort (typed):** 1 week  ·  **Agent effort:** unmeasured  ·  **Human gate:** DEC1 — assist-vs-judge shapes G4's refusal set, built here
**Depends on:** B  ·  **Unblocks:** FSCOPE

## Consumes

- `retrieval/lib/obc_agent_tools.py`
- `emitters/obc-vec.sqlite`

## Produces

- `retrieval/lib/obc_agent_tools.py (G1 hybrid search, G2 computed cannot-list)`
- `proposed/G/check38_capabilities.py`
- `proposed/G/check39_tools.py`
- `retrieval/refusal-evalset.json`

## Staged, then promoted by a human (PROTOCOL step 4a, R13)

You write the left column. You may not write the right column — `.claude/settings.json`, `protect-checks.sh` and `guard-machinery.sh` all refuse it, and gate E2 catches it however it is produced.

| you write | a human installs at |
|---|---|
| `proposed/G/check38_capabilities.py` | `retrieval/checks/check38_capabilities.py` |
| `proposed/G/check39_tools.py` | `retrieval/checks/check39_tools.py` |
| `proposed/G/GATES-G.md` | `gates/GATES-G.md` |

## Serialises on

Another track writes these too. `dispatch.py` will not place two tracks sharing one of them in the same wave.

- `retrieval/lib/obc_agent_tools.py`

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

- [ ] 1 DECLARE   gates written to proposed/G/GATES-G.md before code — STAGED,
                  because gates/ is refused to every executor (R13). A human promotes it.
- [ ] 2 BUILD     in a copy of the tree, never in the bag
- [ ] 3 MUTATE    every ratio gate registered in harden/checks/check35_controls.py; check35 PASS
- [ ] 4 INTEGRATE real paths, orchestration wired, superseded files moved not deleted
- [ ] 4a PROMOTE  every protected output STAGED at proposed/G/<basename> and declared
                  under `promotes:` in tracks.yaml — never written at its real path (R13);
                  flat per track, never proposed/harden/checks/... (R14)
- [ ] 5 RE-BAG    bash ci/regenerate.sh; rebuild; provenance regenerated
- [ ] 6 VERIFY    python3 ci/run_gates.py from a CLEAN bag — every touched gate PASS, corpus mode
- [ ] 7 AUDIT     addendum: what moved, what did not, what broke, what was FOUND
- [ ] tracks.yaml updated: own status, and any new item discovered filed under its track

Returning a pack of loose files is step 2. It is not done.

---
Unofficial derived work. Current to 2025-01-16 (through O. Reg. 5/25). Not the official Building Code Compendium.
© King's Printer for Ontario, 2024. Reproduced with permission.