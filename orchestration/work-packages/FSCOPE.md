# Work package — FSCOPE: Applicability — occupancy, predicates, APPLIES_TO, obc_scope

**Status in DAG:** `blocked`  ·  **Human effort (typed):** 2 weeks  ·  **Agent effort:** unmeasured  ·  **Human gate:** DEC4 — a building official for S3
**Depends on:** G  ·  **Unblocks:** D, FOBJ

> **Trap.** This is not a rule engine. Division A 1.1.2 is a predicate table. Do not reach for LegalRuleML here.

## Consumes

- `Division A 1.1.2`
- `Division A 3.1.2`
- `Division B 3.1.2`
- `defined_term nodes`

## Produces

- `retrieval/stage21_occupancy.py`
- `retrieval/stage22_applicability.py`
- `retrieval/lib/obc_agent_tools.py (obc_scope)`
- `proposed/FSCOPE/GATES-FSCOPE.md`

## Staged, then promoted by a human (PROTOCOL step 4a, R13)

You write the left column. You may not write the right column — `.claude/settings.json`, `protect-checks.sh` and `guard-machinery.sh` all refuse it, and gate E2 catches it however it is produced.

| you write | a human installs at |
|---|---|
| `proposed/FSCOPE/GATES-FSCOPE.md` | `gates/GATES-FSCOPE.md` |

## Serialises on

Another track writes these too. `dispatch.py` will not place two tracks sharing one of them in the same wave.

- `retrieval/lib/obc_agent_tools.py`

## Items

- **F1** — occupancy nodes A1-A4, B1-B3, C, D, E, F1-F3
- **F2** — Part-applicability predicate table with node-id provenance
- **F3** — APPLIES_TO edges
- **F4** — obc_scope tool — returns applicable Parts with justifying provision ids and an explicit not-considered list

## Gates to declare

- `S1`
- `S2`
- `S3`
- `S4`

Every gate that reports a ratio needs a mutation in `check35_controls.py` that drives it below its floor. The mutation targets the mechanism, never the ground truth. Untouched must exit 0; mutated must exit non-zero.

## Exit criteria

- {'S3': 'obc_scope on 20 hand-verified building descriptions matches a building official'}
- {'S4 (H10)': 'ablate the predicate table, obc_scope must REFUSE not guess'}

## Completion checklist (PROTOCOL.md — none optional)

- [ ] 1 DECLARE   gates written to gates/GATES-FSCOPE.md before code
- [ ] 2 BUILD     in a copy of the tree, never in the bag
- [ ] 3 MUTATE    every ratio gate registered in harden/checks/check35_controls.py; check35 PASS
- [ ] 4 INTEGRATE real paths, orchestration wired, superseded files moved not deleted
- [ ] 4a PROMOTE  every protected output STAGED at proposed/FSCOPE/<basename> and declared
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