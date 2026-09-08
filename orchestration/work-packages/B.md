# Work package — B: Model correctness — fix at source, one re-embed

**Status in DAG:** `blocked`  ·  **Effort:** 3 days
**Depends on:** A4  ·  **Unblocks:** G

> **Trap.** B1 must reuse obc_context.owns_table so the assembler and embedder agree on what an article's text is. Two definitions of "the text" is how the table-binding bug happened.

## Consumes

- `pipeline/emitters/stage15_sqlite.py`
- `retrieval/stage19_embed.py`
- `pipeline/stage7_refs.py`

## Produces

- `emitters/obc.sqlite (regenerated, byte-reproducible)`
- `emitters/obc-vec.sqlite (re-embedded)`
- `emitters/obc-mod.sqlite`

## Items

- **B1** — suppress flattened article bodies BEFORE embedding (179 articles, 303,204 chars)
- **B2** — forming_part_of as explicit ref edge in the emitter, schema-enforced
- **B3** — stage7 scans headings for note references (44 of 64 unlinked)
- **B4** — regenerate obc.sqlite so the shipped file no longer carries the wall-clock date

## Gates to declare

- `G5`
- `V3`
- `R4a`
- `R4b`
- `R4c`
- `D1`
- `S0`

Every gate that reports a ratio needs a mutation in `check35_controls.py` that drives it below its floor. The mutation targets the mechanism, never the ground truth. Untouched must exit 0; mutated must exit non-zero.

## Exit criteria

- all four items land, THEN one re-embed; never three
- embed_meta.vectors_sha256 changes; recall@5 on evalset must not regress
- shipped obc.sqlite byte-matches a fresh rebuild (check20 whole-file)

## Completion checklist (PROTOCOL.md — none optional)

- [ ] 1 DECLARE   gates written to gates/GATES-B.md before code
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