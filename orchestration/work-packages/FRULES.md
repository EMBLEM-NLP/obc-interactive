# Work package — FRULES: Compliance checking — LegalRuleML / RASE

**Status in DAG:** `conditional`  ·  **Human effort (typed):** 4 weeks+  ·  **Agent effort:** unmeasured  ·  **Human gate:** DEC1 — assist or judge; the track may not start without it
**Depends on:** D, FOBJ  ·  **Unblocks:** (nothing downstream)

> **CONDITIONAL.** DECISION REQUIRED: assist or judge? Scoping lets the agent help with design; compliance checking lets it pass judgement on one. The second carries liability the first does not. Do not start without an explicit answer.

## Staged, then promoted by a human (PROTOCOL step 4a, R13)

You write the left column. You may not write the right column — `.claude/settings.json`, `protect-checks.sh` and `guard-machinery.sh` all refuse it, and gate E2 catches it however it is produced.

| you write | a human installs at |
|---|---|
| `proposed/FRULES/GATES-FRULES.md` | `gates/GATES-FRULES.md` |

## Gates to declare

- `C1`
- `C2`
- `C3`
- `C4`

Every gate that reports a ratio needs a mutation in `check35_controls.py` that drives it below its floor. The mutation targets the mechanism, never the ground truth. Untouched must exit 0; mutated must exit non-zero.

## Decisions this track needs from a human

- **DEC1** — Compliance checking — assist or judge?

Do not resolve these by assumption. A track that guesses a decision produces confident output with no way to know it is wrong.

## Completion checklist (PROTOCOL.md — none optional)

- [ ] 1 DECLARE   gates written to gates/GATES-FRULES.md before code
- [ ] 2 BUILD     in a copy of the tree, never in the bag
- [ ] 3 MUTATE    every ratio gate registered in harden/checks/check35_controls.py; check35 PASS
- [ ] 4 INTEGRATE real paths, orchestration wired, superseded files moved not deleted
- [ ] 4a PROMOTE  every protected output STAGED at proposed/FRULES/<basename> and declared
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