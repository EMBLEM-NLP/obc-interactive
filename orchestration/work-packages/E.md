# Work package — E: Data fidelity and gap-register closure

**Status in DAG:** `ready`  ·  **Human effort (typed):** 2 weeks  ·  **Agent effort:** unmeasured  ·  **Human gate:** none
**Depends on:** PORT  ·  **Unblocks:** (nothing downstream)
**May run in parallel with:** A2, A4, C — on a separate copy of the tree; serialise on shared files.

## Staged, then promoted by a human (PROTOCOL step 4a, R13)

You write the left column. You may not write the right column — `.claude/settings.json`, `protect-checks.sh` and `guard-machinery.sh` all refuse it, and gate E2 catches it however it is produced.

| you write | a human installs at |
|---|---|
| `proposed/E/GATES-E.md` | `gates/GATES-E.md` |

## Serialises on

Another track writes these too. `dispatch.py` will not place two tracks sharing one of them in the same wave.

- `emitters/obc.sqlite`

## Items

- **E1** — header-row flagging (0 of 320 tables)
- **E2** — row-boundary defect (9.30.3.1 collapses a logical row)
- **E3** — 20-grid round-trip with perturbation control
- **E4** — page 728 Volume 1 — 7 orphaned body lines, first real capture residual
- **E5** — 173 Volume 2 externals; H4 controls for 629 + 363 absence claims
- **E6** — 313 figure assets; 44 compliance-alternative rows; 13 notes-to-table
- **E7** — check22_docs scope -> reports/*.md; reconcile ROADMAP.md, GATED_STATUS.md
- **E8** — check8_build needs the v9 baseline PDF — ship it or retire the check

## Gates to declare

- `T1`
- `T2`
- `T3`
- `T4`
- `T5`

Every gate that reports a ratio needs a mutation in `check35_controls.py` that drives it below its floor. The mutation targets the mechanism, never the ground truth. Untouched must exit 0; mutated must exit non-zero.

## Exit criteria

- {'E5 absence claims need H4 controls': 'a detector reporting zero must be shown to report presence on a seeded fixture'}

## Completion checklist (PROTOCOL.md — none optional)

- [ ] 1 DECLARE   gates written to gates/GATES-E.md before code
- [ ] 2 BUILD     in a copy of the tree, never in the bag
- [ ] 3 MUTATE    every ratio gate registered in harden/checks/check35_controls.py; check35 PASS
- [ ] 4 INTEGRATE real paths, orchestration wired, superseded files moved not deleted
- [ ] 4a PROMOTE  every protected output STAGED at proposed/E/<basename> and declared
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