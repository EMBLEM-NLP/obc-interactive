# Work package — D: Measurement

**Status in DAG:** `blocked`  ·  **Effort:** 1 week
**Depends on:** FSCOPE  ·  **Unblocks:** FRULES

## Produces

- `retrieval/evalset-v2.json`
- `retrieval/agent-tasks.json`
- `retrieval/checks/check36_modality.py`

## Items

- **D1** — 150 competency questions, >=40% paraphrase, hubs, Div C, Act, SB
- **D2** — agent-task evaluation — multi-step, scored on scoping + provisions + citations + refusal
- **D3** — modality accuracy vs 200-sentence human sample, >=98%
- **D4** — building-official review — 30 questions, 20 scoping cases, 50 labels

## Gates to declare

- `R3`
- `R7`
- `R8b`
- `D2`

Every gate that reports a ratio needs a mutation in `check35_controls.py` that drives it below its floor. The mutation targets the mechanism, never the ground truth. Untouched must exit 0; mutated must exit non-zero.

## Exit criteria

- keep the SHA-256 split, dev-only tuning, no-shared-content-word constraint
- D4 requires a human outside this system; if unavailable, D3 stays PLANNED and the accuracy claim stays unquantified

## Completion checklist (PROTOCOL.md — none optional)

- [ ] 1 DECLARE   gates written to gates/GATES-D.md before code
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