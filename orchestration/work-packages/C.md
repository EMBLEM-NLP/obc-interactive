# Work package — C: Identity and portability

**Status in DAG:** `ready`  ·  **Human effort (typed):** 1 week  ·  **Agent effort:** unmeasured  ·  **Human gate:** DEC2 — external exposure sets C1 urgency and RO-Crate depth
**Depends on:** PORT  ·  **Unblocks:** (nothing downstream)
**May run in parallel with:** A2, A4, E — on a separate copy of the tree; serialise on shared files.

## Produces

- `schema/identifiers.md`
- `retrieval/lib/eli.py`
- `query/duckpgq/ or query/age/`

## Staged, then promoted by a human (PROTOCOL step 4a, R13)

You write the left column. You may not write the right column — `.claude/settings.json`, `protect-checks.sh` and `guard-machinery.sh` all refuse it, and gate E2 catches it however it is produced.

| you write | a human installs at |
|---|---|
| `proposed/C/GATES-C.md` | `gates/GATES-C.md` |

## Items

- **C1** — ELI-convention HTTP URIs via w3id.org; internal B/9/... keys become a mapping
- **C2** — DuckPGQ (SQL/PGQ) or Apache AGE surface alongside SQLite. Not Kùzu (archived Oct 2025)

## Gates to declare

- `C1`
- `C2`

Every gate that reports a ratio needs a mutation in `check35_controls.py` that drives it below its floor. The mutation targets the mechanism, never the ground truth. Untouched must exit 0; mutated must exit non-zero.

## Completion checklist (PROTOCOL.md — none optional)

- [ ] 1 DECLARE   gates written to gates/GATES-C.md before code
- [ ] 2 BUILD     in a copy of the tree, never in the bag
- [ ] 3 MUTATE    every ratio gate registered in harden/checks/check35_controls.py; check35 PASS
- [ ] 4 INTEGRATE real paths, orchestration wired, superseded files moved not deleted
- [ ] 4a PROMOTE  every protected output STAGED at proposed/C/<basename> and declared
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