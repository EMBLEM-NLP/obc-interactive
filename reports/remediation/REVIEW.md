# Review: `obc-interactive-bag.zip`

Reviewed 2026-09-06 against the architecture recommendation from the previous turn.

---

## 1. What was verified

| Check | Command | Result |
|---|---|---|
| Tag manifest | `sha256sum -c tagmanifest-sha256.txt` | 5/5 OK |
| Payload manifest | `sha256sum -c manifest-sha256.txt` | 144/144 present files OK |
| Payload-Oxum | recomputed over `data/` | `197980529.144` — exact match |
| Fetch-only inputs | `fetch.txt` | 2 entries; the only 2 manifest failures are exactly these |
| Hardening gates | `gates/GATES-hardening.md` | H1, H1b, H2, H3, H4, H5, H6, H7, H8, H9 — all `[x]` with evidence digests |

The bag is a valid *incomplete* BagIt bag. That is the correct construction here, not a defect: `fetch.txt` records where the Crown-copyright source PDFs come from and the manifest records what they must hash to, so the package is verifiable without redistributing them. This directly resolves the licensing constraint raised in §7 of the architecture recommendation.

## 2. Model integrity

| Metric | Value |
|---|---|
| Nodes | 27,421 |
| Node types | 22 (division → part → section → subsection → article → sentence → clause → subclause, plus `act_*`, `table`, `note`, `index_*`, `supplementary_standard`) |
| `ref` edges | 29,952 (`code_ref` 23,636 · `cap_ref` 2,443 · `std` 2,268 · `note` 940 · `act_ref` 368 · `supp` 251 · `ca` 44 · `form` 2) |
| `term` edges | 16,075 |
| **Dangling ref targets** | **0 / 28,430** |
| **Dangling term targets** | **0 / 16,075** |
| Unresolved refs | 1,522 — all categorised (`not-in-this-edition` 629, `not-in-Table-1.3.1.2` 363, …), i.e. deliberate |
| Transitive closure | 139,967 rows |
| Table cells | 21,313 across 320 tables, with rowspan/colspan preserved |
| Amendments | 144 |
| Link harvest | `pdf-links-v1` 41,064 · `pdf-links-v2` 4,478 (cross-volume, with `remote` targets) |

Zero dangling edges across 44,505 relationships is the headline number. Verification steps 1–3 and 5 from the architecture recommendation are satisfied by construction.

The SQLite emitter already carries FTS5 (porter, `remove_diacritics 2`), a trigram index for substring and citation matching, and a materialised closure table. Against the ranked storage options, **this is effectively option #3 built properly**, and for a single-document corpus it is the right answer — a server graph database would add operational cost without buying anything at this scale.

## 3. Defect found: definition granularity

**Symptom.** 570 distinct defined terms resolved to only **6 target nodes**. The largest, `A/1/1.4.1.2/(1)/(i)`, is 31,199 characters holding ~136 definitions as continuous prose.

**Why the graph looked correct.** `stage7` resolved every italicised term to the clause that genuinely defines it. The edge is true. Traversal is unaffected.

**Why it was fatal for the stated purpose.** Retrieving "the definition of *secondary suite*" returned 16 KB of alphabetically adjacent definitions beginning with sanitary sewers, and any truncation returned a *different term's definition*. An LLM handed that context cites the wrong rule with full confidence. This is precisely the failure mode the graph exists to prevent.

**Fix.** `stage18_definitions.py` splits the blobs on the `<Term> means …` pattern and repoints every term edge at the specific definition.

| | Before | After |
|---|---|---|
| Distinct definition targets | 6 | **383** |
| `defined_term` nodes | 0 | **403** |
| Mean definition length | 16,930 chars | **215 chars** |
| Term edges resolved to a specific definition | 0% | **98.12%** (15,773 / 16,075) |

Four bugs were found and fixed while building it, each worth recording:

1. **Greedy capture.** `Exit means that part of a means of egress` let the term swallow up to the *second* `means`, producing the term `Exit means that part of a` and losing `Exit` entirely — 509 edges. Fixed with `(?!means\b)` inside the word repetition.
2. **Parenthetical qualifiers.** `Assembly occupancy (Group A) means …` did not match. Cost ~20 definitions across Groups A–F.
3. **Plural rule ordering.** Applying suffix rules in priority order mapped `fixtures → fixtur` because the `es` rule fired before `s`. Fixed by trying *all* candidate singulars, and by inflecting the last word of multi-word terms (`storage garages → storage garage`). Worth **+3.4 pp** on its own.
4. **Two definition conventions.** The Code writes `Building means …`; the Act writes `"building" means …`, and the Act's `building` definition has a 30-character body with the substance in child subclauses. Both needed separate handling.

**Validation is structural, not a threshold.** Definitions run alphabetically within a clause, so a false boundary breaks monotonicity and is rejected by a longest-non-decreasing-subsequence filter. That is a real oracle. It is deliberately conservative, so a second pass re-splits any node that still contains a boundary *following a sentence end* — which is how consecutive definitions join, and which a mid-definition `… X means …` never satisfies.

**Residual, enumerated rather than tolerated:**
- 11 terms containing a comma or slash (`boarding, lodging or rooming house`, `class 1 fire sprinkler/standpipe systems`, `live/work unit`). Admitting those characters would split on any capitalised list item.
- 1 merged node, `DEF/cavity-wall`. The next term is `Certificate for the occupancy of a building described in Sentence 1.3.3.4.(3) of Division C` — fifteen words containing periods. No word cap safe for ordinary terms can capture it.

Both sets are listed in `check29_definitions.py` so they cannot grow silently.

`stage18` is deterministic: two runs produce identical definition sets and edge counts, consistent with gate H1.

## 4. Deliverables

| File | Purpose |
|---|---|
| `stage18_definitions.py` | Splits definition blobs, emits `defined_term` nodes, rewires term edges. Writes a new DB; never mutates the input. |
| `check29_definitions.py` | Gate check D1–D4 with a `NEGATIVE=1` control, matching the H4 discipline already in the bag. |
| `obc_context.py` | Mandatory-context bundle assembler — the retrieval layer. |
| `sample-bundle-9.32.3.8.md` | Worked output for Article 9.32.3.8, ~1,400 tokens. |

```bash
python3 stage18_definitions.py --in obc.sqlite --out obc-defs.sqlite
python3 check29_definitions.py --db obc-defs.sqlite        # RESULT: PASS
NEGATIVE=1 python3 check29_definitions.py --db /tmp/neg.sqlite  # RESULT: FAIL D1

python3 obc_context.py 9.32.3.8 --db obc-defs.sqlite
python3 obc_context.py "secondary suite ventilation" --hops 2 --budget 6000
python3 obc_context.py --modality-report
```

`obc_context.py` resolves a node id, a designator, or free text; walks ancestors for scope, the subtree for provision text, `term_resolved` for definitions, `ref` outbound for citations, notes and standards, and `ref` inbound for tables that declare they form part of the provision; renders tables from the `cell` grid; and appends amendments, reverse citations, and the enumerated unresolved references. Output is Markdown with the required attribution footer, budgeted by dropping the least load-bearing sections first — provision text and definitions are never dropped.

Two ranking corrections were needed: index and TOC nodes repeat provision wording verbatim and outranked the provisions themselves under raw BM25, so they are demoted rather than excluded; and modality is derived per sentence (`shall not` before `shall`).

Modality over 15,960 text-bearing leaf nodes: **37.9% obligation, 6.6% permission, 3.4% exemption, 3.0% prohibition**, 49.0% non-normative — 6,541 normative provisions.

## 5. Recommended next actions

**ADD — embeddings.** The only substantive layer still missing. FTS5 and trigram give exact and lexical matching; there is no semantic recall, so "how much makeup air does a range hood need" will not reach 9.32.3.8 unless the wording overlaps. Embed at **article level** (~2,749 vectors — small), keep sentence and clause nodes addressable for citation, and use `sqlite-vec` so it stays in one file alongside FTS5. Fuse with Reciprocal Rank Fusion. Apply contextual retrieval: prepend the scope trail `obc_context.py` already computes to each chunk before embedding.

**ADD — a retrieval eval set.** 50–100 gold question → expected-node-id pairs, weighted toward definition-dependent and table-dependent questions, since those are where naive retrieval fails and where the graph earns its cost. Measure recall@k and *mandatory-context completeness*: did expansion pull every required definition, table and note? Gate releases on it, as `check0`–`check29` already gate the build.

**ADD — objective attribution.** The Code is objective-based and `Objective` / `FunctionalStatement` nodes are not yet modelled. Only 26 nodes mention functional statements, so the Division B → OS/OP attribution tables are not yet parsed. This is required before any alternative-solution reasoning.

**UPDATE — promote modality into the model.** It is currently derived at query time in `obc_context.py`. Persist it as a `modality` column on `node`, written by a stage with its own check. It is the deontic core any compliance layer needs, and deriving it per query means it is never validated.

**UPDATE — `stage7` should target `DEF/*` directly.** `stage18` is a corrective post-pass. Once stable, fold the split into the tree stage so `term.dst` is specific at source and `term_resolved` becomes redundant.

**REMOVE — nothing.** No component reviewed is redundant or misconceived.

**DEFER — Akoma Ntoso export, a graph database, and any rules engine.** The AKN projection is worth doing for interoperability but buys nothing until there is a second document. A graph database buys nothing over the closure table at 27k nodes. A rules engine (LegalRuleML / Datalog / SHACL) should wait until modality is persisted and the eval set exists, and should then be scoped to numeric Part 9 provisions — spans, spacing, dimensions — where deterministic checking is tractable. Everything else stays cited decision-support: independent evaluation of purpose-built legal-AI tools still measures 17–33% hallucination rates, so citation grounding and a human building official in the loop remain mandatory.

---

Unofficial derived work. Current to 2025-01-16 (through O. Reg. 5/25). Not the official Building Code Compendium.
© King's Printer for Ontario, 2024. Reproduced with permission.
