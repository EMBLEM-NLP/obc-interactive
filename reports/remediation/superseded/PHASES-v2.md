# Phase plan v2

Supersedes `PHASES.md` (2026-09-06). Rewritten after reviewing the retrieval build.

---

## Why this is a refactor and not an edit

v1 assumed the next phase would be built onto a sound base and measured by gates that work. The retrieval build tested that assumption and it half-held.

The engineering was good. The **verification had a hole**, and it was the same hole in a new place.

| | found in | shipped state | detected by an existing gate? |
|---|---|---|---|
| 570 defined terms collapsed into 6 blob nodes | first review | all gates green | **no** — every edge was valid, so nothing was wrong to find |
| `check33` completeness is arithmetically incapable of failing | this review | R4 green | **no** — R5 controls R3, not R4 |
| Article's own table silently dropped from every bundle | this review | — | **no** — my own code, and my own review missed it first pass |

Three real defects, none visible on a green board. The common shape: **a metric computed from the same source it is checked against, or an assertion with no mutation that can drive it down.**

Gate H4 already encodes the cure for *absence* assertions ("every absence assertion has a negative control that proves the detector can report presence"). It does not cover **ratio** assertions, and `check33` is a ratio. That is the single structural change in v2.

The second structural change: **measure over the corpus, not over the eval set.** C1/C2/C3 all passed on the 26 eval targets and the corpus run immediately exposed a 90.06% delivery rate concentrated in two hub articles. A 50-question eval set cannot find a problem that lives in the tail.

---

## Numbering as it actually stands

Adopting the shipped numbering, not v1's proposal.

| | used | next free |
|---|---|---|
| Stages | 0–17, **19** (`stage19_embed`) | 18 (definitions, pending), **20+** |
| Checks | 0–28, **30–34** | 29 (definitions, pending), **35+** |
| Gates | G1–G16, V1–V8, H1–H9, **R1–R5** | D1, **R6+, H10** |

v1 proposed stage19 = modality; the shipped build used stage19 = embed. Modality moves to stage 20.

---

## Phase 10 — reopened (2–3 weeks)

Not a new phase. R1–R5 are marked met and two of the five do not hold as stated. Close them before anything else starts.

### 10.1 — Fold in the definition split *(1 day)*

`stage18_definitions.py`, `check29_definitions.py` → `pipeline/`, added to `run.sh` after stage 7. Gate **D1** with the `NEGATIVE=1` control.

The vector index does **not** need rebuilding — article embeddings are unaffected by the split. What must exist at retrieval time is `term_resolved`. Without it, usability stays at 1.89%.

Result: 403 `defined_term` nodes, 383 distinct targets, 98.12% of term edges rewired, mean definition 215 chars against 16,930.

### 10.2 — Replace R4 *(2 days)*

**REMOVE** `check33_completeness.py`. **ADD** `check33b_completeness.py`. Restate the single gate as three, because they fail for different reasons and a blended number hides which:

- **R4a reachability** — expansion reaches each dependency at *n* hops. Floor 99%.
- **R4b delivery** — the rendered, budget-trimmed bundle contains it. Floor 95%.
- **R4c usability** — a delivered definition is that term's own, not a blob. Floor 99%.

Each gate runs in **both** modes: eval targets *and* `--all-articles`. The corpus mode is the one that gates.

### 10.3 — Assembler and table binding *(3 days)*

- **Own-table fix** — shipped in `obc_context.py`. A table belonging to the anchor is a descendant, lands in `seen` before expansion, is skipped by both the outbound and inbound paths, and renders as nothing because table text lives in `cell` not `body`. Reachability: **40 → 298 → 320/320**; 688 of 2,749 articles surface a table.
- **UPDATE the SQLite emitter** to write `forming_part_of` as an explicit `ref` edge in addition to the parent relation. 299 of 320 tables carry it in the JSONL; only 40 became `ref` edges. Two encodings of one fact is how the other 259 went missing.
- **check35_tables.py** — every table binds to ≥1 provision by *both* encodings; counts agree.

### 10.4 — Hub-article policy *(3 days)*

Corpus delivery is **90.06%** and two articles are **90.5% of the entire shortfall**:

| article | delivered | dependencies |
|---|---|---|
| `B/1/1.3.1.2` Applicable Editions | 1 | 677 |
| `B/11/11.5.1.1` Compliance Alternatives | 7 | 382 |
| `B/9/9.41.2.2` Performance Level Evaluation | 3 | 71 |
| `A/1/1.4.1.2` Definitions | 8 | 35 |

Not a budget problem: 8k → 32k tokens moves delivery only 90.06% → 92.52%. The median article has **3** dependencies and the 95th percentile has **11**.

**ADD** a bundle-by-reference mode for articles above ~50 dependencies: deliver the table plus a count and a pointer, never the expansion. **Enumerate the set** in the check, so it cannot grow silently — the discipline `check29` already uses for its residual.

### 10.5 — Eval set v2 *(4 days)*

The `test` split is 27 questions of which **5** are `paraphrase`. R3's central claim — that the vector layer earns its place where lexical retrieval fails — rests on those five. And no hub article appears anywhere in the set, which is why 10.4 was invisible.

- Raise to **150 questions**, ≥40% paraphrase, keeping the SHA-256 split and the no-shared-content-word constraint.
- Deliberately include high-dependency targets, Division C, the Act, and Supplementary Standards.
- Keep the stated limitation: not reviewed by a building official. Getting one to review even 30 questions would be the highest-value external input available.

### 10.6 — stage20 modality *(3 days)*

Deferred from v1's 10a and still not built. `obc_context.py` derives modality at query time, and anything derived at query time is never validated.

Persist to `node.modality` for the 15,960 text-bearing leaves. Current derivation: 37.9% obligation, 6.6% permission, 3.4% exemption, 3.0% prohibition, 49.0% non-normative — **6,541 normative provisions**. `check36_modality.py`: 200-sentence hand-labelled stratified sample, ≥98% agreement, with a `shall not` control.

**Phase 10 exit:** D1, R4a–c, R6 (hub policy), R7 (eval v2), R8 (modality) green, each in corpus mode, each with a mutation control.

---

## Cross-cutting — H10, the change that matters most

**ADD gate H10: every gate reporting a ratio must have a mutation that drives it below its floor.**

H4 covers absence assertions. `check33` was a ratio, and a ratio computed from its own source is indistinguishable from a healthy one. Extend `check23_controls.py` to enumerate every ratio-reporting check and require a registered mutation for each:

| check | mutation that must fail it |
|---|---|
| R4a reachability | delete a `ref` row the target depends on |
| R4b delivery | set budget to 100 tokens |
| R4c usability | run against a DB without `term_resolved` — must report ≈1.9%, not 100% |
| D1 definitions | inject an unsplit blob (already implemented) |
| R3 fusion | scramble the vector index (already implemented) |

This is cheap — most mutations are three lines — and it is the only thing that would have caught all three defects found so far. **Make it a precondition for closing any phase, not a task inside one.**

---

## Phase 11 — objectives and occupancy (3 weeks)

Unchanged in substance from v1. Can start once 10.3 lands.

- **stage21_objectives.py** — `Objective` (OS/OP) and `FunctionalStatement` nodes from Division A Parts 2–3; `ATTRIBUTED_TO_OBJECTIVE` edges from Division B via the attribution tables. Only 26 nodes currently mention functional statements, so these tables are unparsed.
- **stage22_occupancy.py** — `Occupancy` nodes and `APPLIES_TO` edges. The vocabulary is already recovered in the split definitions (`Assembly occupancy (Group A)`, `Care occupancy (Group B, Division 3)`).
- Checks 37–38, gates S1–S4, each with an H10 mutation.

Without this, "what applies to a Group C building of 3 storeys" is answerable only by keyword luck.

---

## Phase 12 — gap-register closure (3 weeks)

Runs in parallel with 11. Now carries a concrete example for the table defect.

| item | count | note |
|---|---|---|
| Vol 2 externals unresolved | 173 | 111 supp · 60 App A · 2 forms. G15 cannot close otherwise |
| `not-in-this-edition` | 629 | **absence claims — need H4 controls** |
| `not-in-Table-1.3.1.2` | 363 | same |
| `figure asset` | 313 | bind to extracted assets |
| `compliance-alternative row` | 44 | model as a node type; feeds the `B/11/11.5.1.1` hub |
| table header rows | 0 of 320 flagged | `9.30.3.1` renders `Matched hardwood (interior use only) 400 7.9 19.0 600 7.9 33.3` as one cell — a whole logical row collapsed. Reproducible example |
| definition terms with comma/slash | 11 | enumerated in `check29` |
| `DEF/cavity-wall` merged | 1 | 15-word term containing an internal citation; accept, keep enumerated |
| notes-to-table blocks | 13 | link to parent table |
| figure region ↔ asset | untested | positional only |
| table cell reading order | untested | the `9.30.3.1` case is evidence this is real, not theoretical |
| bilingual policy | none | front matter is bilingual; emitters have no policy |

---

## Phase 13 — compliance, narrowly scoped (4+ weeks)

**Hard-blocked by Phase 10 exit, and the block is now stronger than in v1.** A compliance layer measured by a check that cannot fail is worse than no compliance layer, because it produces confident output and a green board.

- Scope to numeric Part 9 provisions only — spans, spacing, dimensions, loading rates.
- Modality from stage20 is the input. LegalRuleML for normative structure and exceptions, feeding Datalog or a defeasible engine.
- Everything else stays cited decision-support. Independent evaluation of purpose-built legal-AI tools measures 17–33% hallucination rates; citation grounding and a human building official in the loop remain mandatory.
- Gates C1–C4, each with an H10 mutation. C-series must include: perturb a numeric threshold in the source and require the engine to change its answer.

---

## Phase 14 — maintenance and interoperability (start now, finish later)

Promoted from "ongoing" to **start the diff pipeline during Phase 11**, not after Phase 13. The Code will be amended and there is currently no way to re-verify cheaply.

- **Amendment diff.** Re-run, diff the graph, review only what changed. 144 amendment records and the `AmendmentEvent` model exist; the diff and the review workflow do not.
- **Embedding model experiment.** `all-MiniLM-L6-v2` (384-dim) is a reasonable default but weak on technical and legal text. Rebuilding 2,749 vectors is cheap. **Do not run this experiment before eval set v2** — with 5 paraphrase questions in `test` there is no power to detect an improvement.
- **Akoma Ntoso + ELI export.** Worth doing for interoperability; buys nothing until a second document exists.
- **Second-document generalisation.** Every threshold was calibrated on Volume 1; Volume 2 needed a second container model in stage 3. The NBC or another provincial code is the real test.
- **Licensing.** Internal use is covered. Commercial release needs written permission from **both** MMAH (`buildingtransformation@ontario.ca`) and NRC, because the technical content is NBC material adopted by reference. Resolve before launch, not after.

---

## Phase 9.5 — still open

Carried unchanged from v1 and still not done. One day.

- `ROADMAP.md` and `GATED_STATUS.md` describe Phases 5–9 as future and G15/G16 as UNMET. The artifacts contradict this: emitters ship, Volume 2 is merged, the Act and Index are parsed, and the built-from-model PDF carries **37,370 links** against the patched v9's 27,928.
- `check22_docs.py` passes over both files, so gate H3 overstates what it guarantees. **Extend its scope to `reports/*.md`.**

---

## Sequencing

```
9.5   reconcile + re-bag         1 day    ── cheapest, blocks nothing
H10   ratio-mutation discipline  2 days   ── do FIRST; it changes how every
                                             later phase is judged
10    retrieval, reopened        2-3 wk   ── CRITICAL PATH
11    objectives + occupancy     3 wk     ── parallel after 10.3
12    gap-register closure       3 wk     ── parallel, independent
14a   amendment diff pipeline    2 wk     ── start during 11, not after 13
13    compliance (Part 9)        4 wk     ── hard-blocked by Phase 10 exit
14b   model experiment, AKN      —        ── after eval set v2
```

**What changed from v1:** Phase 10 reopened rather than closed. H10 added as a precondition on every phase. Hub-article policy and eval set v2 are new work items that did not exist in v1 because the problems were not visible. The amendment diff pipeline moved earlier. Modality slipped from 10a to 10.6 and stage19 to stage20.

**Assumptions:** one to two engineers; source edition stable through the plan; embedding model unchanged until eval v2 exists.

**Risks, re-ranked:**

1. **Treating a green gate board as evidence.** Three real defects have now shipped green. Until H10 lands, the board reports that checks ran, not that the thing is right.
2. **Measuring only on the eval set.** Every corpus-wide run so far has found something the eval set missed. Corpus mode should be the default, eval mode the convenience.
3. **Starting Phase 13 before Phase 10 exit.** Confident compliance output with no way to know it is wrong.
4. A Code amendment landing with no diff pipeline — forces full re-verification instead of reviewing what changed.
5. Doc drift becoming normal. H3 passes today over two stale files.

---

Unofficial derived work. Current to 2025-01-16 (through O. Reg. 5/25). Not the official Building Code Compendium.
© King's Printer for Ontario, 2024. Reproduced with permission.
