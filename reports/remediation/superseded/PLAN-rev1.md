# Execution plan

Supersedes `FIXPLAN.md` and `PHASES-v2.md`. Both remain valid in substance; they are merged here because three overlapping plans is itself a problem — work gets done in whichever document was opened most recently.

---

## Where we are

The build is strong on the axes most knowledge-graph projects fail: zero dangling edges across 44,505 relationships, categorised unresolved references, per-node page/bbox provenance, BagIt fixity, and a 57-check gate board with cryptographic evidence. The standards review put it in the top decile on verification discipline.

It is weak on the axes that define graph engineering as a discipline: **no declared schema, no persistent identifiers, no CI, no portable query language, no ontology.** The verdict was "good engineering that is mislabelled" — an excellent pipeline and archival artifact wearing the label "graph."

Four defects have now shipped with a fully green board. That is the pattern the plan has to break.

---

## What the standards review changed

Four genuinely new items, one reframe, one correction.

**NEW — declared schema.** Ranked as the highest-consequence gap. The two-way table encoding (defect #3) is the textbook case a schema with keys and cardinality constraints makes unrepresentable. This was not in either previous plan.

**NEW — CI.** The gate board is excellent and runs only when a human runs it. Everything else in this plan is contingent on it: discipline that depends on someone remembering is not discipline.

**NEW — portable query surface.** All traversal is bespoke SQL. Not a performance problem; a reviewability and portability one. SQL/PGQ via DuckPGQ, or openCypher via Apache AGE, adds a standard graph-query surface without abandoning the embedded single-file model.

**NEW — persistent identifiers.** Raised in the first architecture report as ELI-style IDs, then dropped out of both subsequent plans. It belongs back in, sequenced before the next Code edition.

**REFRAME — the eval set is a competency-question suite.** In ontology engineering (NeOn, eXtreme Design) competency questions are the requirements instrument, and they drive *schema* coverage, not just retrieval quality. Naming it correctly changes what goes in it.

**CORRECTION — Kùzu is dead.** My first report ranked it the #1 storage choice. Its GitHub repository was archived 10 October 2025 after Apple's acquisition, continuing only as the LadybugDB and Bighorn forks. You chose SQLite instead and the standards review endorses that as correct at 27k nodes. Where a graph surface is wanted, DuckPGQ and Apache AGE are the lower-risk options now.

---

## Track A — Integrity *(2 weeks, critical path)*

Nothing else is worth doing until the board is honest and automatic.

**A1 — integrate the remediation pack.** *1 day.* Seven fixes built and green: `stage18` definitions, `stage20` modality, `check29`, `check33b` replacing `check33`, `check35` controls, the assembler fixes, `GATES-remediation.md`. Until this lands, R4 sits marked `[x]` on a metric that cannot fail.

**A2 — ADD CI.** *1 day.* Run the full board, determinism gate, and eval set on every commit. **No artifact ships without a green board produced by CI rather than by hand.** This is the multiplier; do it before the schema work, not after.

**A3 — complete the mutation controls.** *2 days.* The audit found **9 of 57 checks report a ratio and only 3 checks have any control path, none covering a ratio.** Register a mutant for each of `check0_coverage`, `check4_capture`, `check5_tables`, `check7_refs`, `check10_index`, `check14_crossvol`, `check24_metamorphic`, `check31_evalset`. Extend `check23_controls.py` so a new ratio gate cannot be merged without one.

**A4 — ADD a declared schema.** *3–5 days.* Author once in **LinkML** — it generates SHACL, JSON-Schema, SQL DDL and Pydantic from one YAML, so the schema stays single-source. Minimum viable constraint set must make defect #3 unrepresentable: *each table binds to exactly one provision via exactly one edge kind.*

> **Sanity threshold from the review:** if the 22 node types and 8 edge kinds cannot be expressed in under ~300 lines, the model is more complex than it looks and should be refactored before anything is built on it.

---

## Track B — Model correctness *(3 days, after A4)*

Sequenced *after* the schema deliberately. With A4 in place these become "make the data conform, verified by the schema" rather than three more ad-hoc emitter patches.

Batch all three, then **re-embed once**. Each one invalidates vectors; doing them separately is triple cost for identical output.

- **B1** — suppress flattened article bodies before embedding. 179 of 1,640 body-bearing articles carry their table as run-on prose; mean body 1,693 chars against 91. Reuse `obc_context`'s `owns_table` logic so assembler and embedder cannot disagree about what an article's text is.
- **B2** — write `forming_part_of` as an explicit `ref` edge. 299 of 320 tables carry it in JSONL; 40 became edges. Now schema-enforced rather than convention.
- **B3** — scan headings for note references. 44 of 64 "See Note" headings have no note edge; `9.32.3.8` has no link to its own note.

**Verify:** `embed_meta.vectors_sha256` changes; recall@5 must not regress. If it does, B1's threshold is cutting real text.

---

## Track C — Identity and portability *(1 week, before the next Code edition)*

**C1 — persistent identifiers.** Mint dereferenceable HTTP URIs on **ELI** conventions or Akoma Ntoso `eId`, served through **w3id.org**. Keep `B/9/9.32.3.8` as an internal key mapped to the public identity, not as the identity itself. Without this, cross-edition diffing and any external citation break.

**C2 — portable query surface.** Expose the graph through **DuckPGQ** (SQL/PGQ, ISO/IEC 9075-16:2023) or **Apache AGE** (openCypher on Postgres) alongside SQLite. Not Kùzu. Ship before any third party needs to query this, not after.

---

## Track D — Measurement *(1 week, after B)*

**D1 — competency-question suite v2.** Currently 50 questions, test split 27, of which **5** are paraphrase — R3's central claim rests on those five, and no hub article appears at all. Target 150 questions, ≥40% paraphrase, including the four hubs, Division C, the Act, and Supplementary Standards. Keep the SHA-256 split, dev-only weight tuning, and the no-shared-content-word constraint; those are already right. Add questions that exercise *schema* coverage, not only retrieval.

**D2 — `check36_modality`.** 200-sentence stratified hand-labelled sample, ≥98% agreement. `check35` covers the mechanism; nothing yet covers whether the labels are correct.

**D3 — building-official review.** Two days of one qualified person reviewing 30 eval questions and 50 modality labels. **This is the highest-value external input available to the project** and the only thing that closes the largest unquantified risk.

---

## Track E — Data fidelity *(2 weeks, parallel with C)*

Blocks any compliance work. Numeric checking over tables whose rows are wrong is worse than none.

- Header-row flagging — 0 of 320 tables flag headers; `9.23.4.2.-L` renders five unlabelled columns under one spanning header.
- Row boundaries — `9.30.3.1` collapses a whole logical row into one cell.
- Round-trip verification of 20 grids against source pages, with a perturbation control.
- 173 remaining Volume 2 externals; H4 controls for the 629 `not-in-this-edition` and 363 `not-in-Table-1.3.1.2` absence claims; 313 figure assets; 44 compliance-alternative rows.
- `check22_docs.py` scope → `reports/*.md`; reconcile `ROADMAP.md` and `GATED_STATUS.md`.

---

## Track F — Semantics *(4+ weeks, conditional — see decisions)*

Only if compliance checking is a real goal rather than an aspiration.

- Objectives and functional statements from Division A Parts 2–3; the Code is objective-based and the graph does not yet contain its logical spine.
- Occupancy classification and `APPLIES_TO` edges.
- **LegalRuleML** (OASIS Standard, 2021) and/or **RASE** markup for checkable rules. Persisted modality is a necessary down payment, not sufficient — the system currently cannot *check* compliance, only retrieve provisions relevant to it.
- Versioning on the Akoma Ntoso FRBR expression layer, so editions are diffable.
- Amendment diff pipeline. Start this early regardless of Track F: the next amendment lands whether or not the rest is ready.

---

## Critical path

```
A1 integrate         1d  ─┐
A2 CI                1d  ─┤ Track A: 2 weeks, blocks everything
A3 mutation controls 2d  ─┤
A4 declared schema  3-5d ─┘
        │
B  model fixes + ONE re-embed    3d
        │
D  measurement                   1 wk   ── nothing later is trustworthy
        │                                  beyond what this measures
   ├─ C identity + portability   1 wk   ── parallel
   └─ E data fidelity            2 wk   ── parallel
        │
F  semantics + compliance        4 wk+  ── conditional
```

Roughly **7 weeks** to the end of E; Track F is a separate commitment.

---

## Decisions only you can make

These need an answer, not more analysis. Each changes the plan materially.

1. **Is compliance checking a real goal, or is retrieval enough?** Track F is 4+ weeks and pulls in LegalRuleML, objectives, and occupancy modelling. If the answer is "retrieval and agent context," say so and delete Track F — the system is close to done at the end of E.
2. **Will this ever leave your organisation?** Determines whether C1 is urgent or optional, whether RO-Crate packaging matters, and whether you need written permission from **both** MMAH and NRC (the technical content is NBC material adopted by reference).
3. **Who else can run this?** CI fixes the automation half of bus-factor. It does not fix the fact that the design rationale lives in one head.
4. **`B/11/11.5.1.1` renders at 11,830 tokens** after every fix, because it owns five large tables. Per-table row cap for hubs, or accept and document? Don't leave it undecided; that shape of thing resurfaces as a production bug.
5. **Can you get a building official for two days?** If not, D2 and D3 need a different plan and the accuracy claims stay unquantified.

---

## Not doing

- **Not replacing SQLite.** Endorsed by the standards review at this scale. The storage choice was right.
- **Not adopting Kùzu.** Archived October 2025.
- **Not building a full PROV-O derivation graph.** Over-engineering for a single-source, single-derivation artifact. RO-Crate over the existing BagIt is the proportionate upgrade *if* decision 2 says this goes external.
- **Not converting wholesale to RDF or Akoma Ntoso.** Defensible to skip for the retrieval goal; revisit only under Track F.
- **Not chasing three enumerated residuals:** the 11 comma/slash definition terms, `DEF/cavity-wall`, and hub sizing beyond decision 4.

---

## Standing risk

Every defect found so far shipped green. Structural validity is not semantic correctness, and the board reports that checks ran — not that the data is right. A2 and A3 are what turn that from a hope into a property of the system. Do them first even though A4 is more interesting.

---

Unofficial derived work. Current to 2025-01-16 (through O. Reg. 5/25). Not the official Building Code Compendium.
© King's Printer for Ontario, 2024. Reproduced with permission.
