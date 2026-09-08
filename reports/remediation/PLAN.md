# Execution plan — revision 2

Supersedes revision 1 of this file, `FIXPLAN.md`, and `PHASES-v2.md`. One plan.

---

## What changed since revision 1

Revision 1 left one decision open: *is compliance checking a real goal, or is retrieval enough?* An empirical test answered half of it.

I ran a design question through the system — *"2-storey house with a secondary suite, what ventilation applies?"* — and traced what an agent gets at each step. Retrieval, context assembly, citation, and modality all work. **Scoping does not.** "Does Part 9 apply to this building?" returned the Compliance Alternatives hub and the front matter. The graph has no occupancy nodes and no `APPLIES_TO` edges, so an agent must read Division A scoping prose and reason its way to an answer — precisely where legal LLMs hallucinate at 17–33%.

Three consequences:

1. **Applicability modelling moves from conditional Track F to the critical path.** If the app's agent is meant to do design work, it must be able to scope a building before it retrieves anything. Occupancy classification and `APPLIES_TO` edges are the minimum. This is *not* the same as compliance checking, which stays conditional.

2. **A new track for the agent surface.** `obc_agent_tools.py` now exists — six JSON-schema tools, MCP-servable. Its `capabilities` tool returns an explicit `cannot` list so an agent can discover a question is unanswerable rather than guess. That list should be **generated from graph state and verified in CI**, so the honesty surface stays honest as tracks close.

3. **A third instance of one-fact-two-tables.** `what_cites` on any definition returned zero, because term usage lives in `term_resolved` while citations live in `ref`. "Nothing depends on this term" is the answer an agent would least suspect and most confidently misuse. Fixed — and it is further evidence for the declared schema in A4.

---

## Where we are

Strong on integrity, provenance, and verification discipline (top decile). Weak on schema, identifiers, CI, portable query, and ontology. Now also: **read-agency works, act-agency does not.** An agent can navigate, retrieve, quote, and know what a sentence obligates. It cannot determine what applies to a building, what objective a provision serves, whether a provision is in force today, or whether a design complies.

Four defects have shipped green, plus two more caught while building the agent surface. The pattern is unchanged: structural validity is not semantic correctness.

---

## Track A — Integrity *(2 weeks, critical path, unchanged)*

- **A1** integrate the remediation pack — now including `obc_agent_tools.py` and `tool-schemas.json`. *1 day.*
- **A2** CI: full board, determinism gate, eval set, and tool-surface tests on every commit. *1 day.*
- **A3** mutation controls for the 9 ratio-reporting checks; extend `check23_controls.py` so no ratio gate merges without one. *2 days.*
- **A4** declared schema in **LinkML**. The constraint set must now make *three* known defects unrepresentable: table binding encoded two ways; definition usage and citation split across tables; and any future edge kind added without a reverse-lookup path. *3–5 days.*

> Sanity threshold: if 22 node types and 8 edge kinds need more than ~300 lines of schema, refactor the model first.

---

## Track B — Model correctness *(3 days, after A4)*

Batch, then re-embed **once**.

- **B1** suppress flattened article bodies before embedding (179 articles; mean body 1,693 chars vs 91).
- **B2** `forming_part_of` as an explicit `ref` edge, schema-enforced.
- **B3** scan headings for note references. **Promoted in importance:** 44 of 64 "See Note" headings have no edge, which means an agent cannot reach the explanatory note for `9.32.3.8` from `9.32.3.8`. For an agent, that is a silent context hole.

---

## Track G — Agent surface *(1 week, new, after B)*

**G1 — expose semantic search in the tool surface.** *1 day.* The vectors exist in `obc-vec.sqlite`; `obc_search` currently reaches only FTS5 and trigram. Wire hybrid retrieval (vector ∪ BM25, RRF) into `obc_search` and remove "no semantic index" from the `cannot` list. Cheapest single improvement to agent recall.

**G2 — generate `capabilities.cannot` from graph state.** *1 day.* Each `cannot` item becomes a query: *no occupancy nodes* → `SELECT COUNT(*) FROM node WHERE type='occupancy'`; *notes unlinked from headings* → the 44/64 count; *no temporal model* → absence of an in-force table. The list is computed, not typed. **`check38_capabilities.py`** fails CI if the hand-written list and the computed list disagree. When Track F-scope lands, the applicability line disappears on its own.

**G3 — tool-surface tests.** *2 days.* Every tool has a fixture and a control. `what_cites` on a definition must return >0; `get_context` on a hub must set `hub=true` and warn; `search` must rank a provision above its index entry.

**G4 — refusal evaluation.** *2 days.* A set of questions that fall in the `cannot` list — *which occupancy group is this building?*, *is 9.32.3.8 in force today?* — where the correct agent behaviour is to call `obc_capabilities` and decline. Measure **hallucinated-applicability rate**: the fraction of `cannot` questions the agent answers anyway. This is the safety metric for act-agency and it must be near zero before any design workflow ships.

---

## Track F-scope — Applicability *(2 weeks, promoted to critical path, after G)*

The minimum an agent needs to scope a building. **Not** a rule engine.

**F1 — occupancy nodes.** Groups A–F with divisions (A1–A4, B1–B3, C, D, E, F1–F3) from Division A 3.1.2 and Division B 3.1.2. The vocabulary is already recovered in the split definitions (`Assembly occupancy (Group A)`, `Care occupancy (Group B, Division 3)`).

**F2 — Part-applicability predicates.** Division A 1.1.2 encoded as a small structured table, not prose: *Part 9 applies where storeys ≤ 3, building area ≤ 600 m², major occupancy ∈ {C, D, E, F2, F3}; Part 3 otherwise.* Plus the handful of scoping exceptions. This is a predicate table with node-id provenance, tractable in days, and it does not require LegalRuleML.

**F3 — `APPLIES_TO` edges.** Parts and Sections → occupancy groups, derived from F2 and from explicit scope statements in Part headings ("Application of Part 9").

**F4 — `obc_scope` tool.** `obc_scope(storeys, building_area_m2, occupancy, ...)` → applicable Parts and Sections with the provision ids that justify each, and an explicit list of what the tool did *not* consider. This is what turns the design question's step one from "read and reason" into "query and cite."

**Gates S1–S4**, each with an H10 mutation: every Part carries an applicability predicate; every occupancy group is reachable from Division A; `obc_scope` on 20 hand-verified building descriptions matches a building official's answer; ablating the predicate table must make `obc_scope` refuse rather than guess.

---

## Track D — Measurement *(1 week, after F-scope; extended)*

**D1 — competency-question suite v2.** 150 questions, ≥40% paraphrase, hubs, Division C, Act, Supplementary Standards. Schema-coverage questions, not only retrieval.

**D2 — agent-task evaluation.** *New.* Multi-step tasks, not single questions: *given this building, list applicable ventilation provisions with citations.* Scored on: correct scoping (F-scope), correct provision set, every claim cited to a node id, and correct refusal where the graph cannot answer. This is the evaluation that measures agency rather than retrieval.

**D3 — `check36_modality`.** 200-sentence labelled sample, ≥98%.

**D4 — building-official review.** Two days: 30 competency questions, 20 scoping cases, 50 modality labels. Still the highest-value external input available.

---

## Track C — Identity and portability *(1 week, parallel with E)*

- **C1** persistent identifiers on ELI conventions via w3id.org; internal `B/9/...` keys become a mapping. Before the next Code edition.
- **C2** portable query surface: **DuckPGQ** (SQL/PGQ) or **Apache AGE**. Not Kùzu — archived October 2025.

---

## Track E — Data fidelity *(2 weeks, parallel with C)*

- Header-row flagging (0 of 320); row boundaries (`9.30.3.1`); 20-grid round-trip with a perturbation control.
- 173 Volume 2 externals; H4 controls for the 629 and 363 absence claims; 313 figure assets; 44 compliance-alternative rows.
- `check22_docs.py` scope → `reports/*.md`; reconcile `ROADMAP.md` and `GATED_STATUS.md`.

---

## Track F-objectives *(2 weeks, after F-scope)*

Objectives (OS/OP) and functional statements from Division A Parts 2–3, with `ATTRIBUTED_TO_OBJECTIVE` edges from Division B. Needed for alternative-solution reasoning and for an agent to answer "why does this provision exist." Not needed for scoping; hence after F-scope.

---

## Track F-rules — Compliance checking *(4+ weeks, still conditional)*

**LegalRuleML** and/or **RASE** markup for executable rules; a rules engine for numeric Part 9 provisions; temporal model on the Akoma Ntoso FRBR expression layer. Persisted modality is a down payment, not a rule layer. The system cannot check compliance today and this track is the only thing that changes that.

**The decision that remains:** scoping and retrieval let an agent *assist* design work. Compliance checking lets it *judge* it. The second carries liability the first does not. Decide it explicitly.

---

## Critical path for agency

```
A  integrity                    2 wk  ── blocks everything
B  model fixes + ONE re-embed   3 d   ── B3 matters more now
G  agent surface                1 wk  ── semantic search, computed cannot-list,
                                          refusal eval
F-scope applicability           2 wk  ── THE gap between read and act
D  measurement incl. agent tasks 1 wk ── first honest number for agency
   ├─ C identity + portability  1 wk  ── parallel
   └─ E data fidelity           2 wk  ── parallel
F-objectives                    2 wk
F-rules                         4 wk+ ── conditional
```

**~9 weeks** to an agent that can scope a building, retrieve with citations, and refuse what it cannot answer, with a measured hallucinated-applicability rate. F-objectives adds two; F-rules is a separate commitment.

---

## Decisions

Resolved by evidence:
- ~~Is agentic design work a goal?~~ The app has an agent; agency without scoping is guessing. **F-scope is on the critical path.**

Still open:
1. **Compliance *checking* — assist or judge?** Determines F-rules and the liability posture. The refusal evaluation in G4 is only meaningful once this is answered, because "what should the agent refuse" depends on it.
2. **External exposure** — determines C1 urgency, RO-Crate, and MMAH + NRC permission.
3. **Bus factor** — CI fixes automation; design rationale still lives in one head.
4. **`B/11/11.5.1.1` at 11,830 tokens** — per-table cap or accept. Decide.
5. **Building official for two days** — now needed for scoping cases too.

---

## Not doing

Unchanged: not replacing SQLite; not adopting Kùzu; not building full PROV-O; not converting to RDF/Akoma Ntoso wholesale; not chasing the three enumerated residuals.

**Added:** not letting the agent answer applicability questions by reasoning over prose while F-scope is unbuilt. The `cannot` list and G4 exist to prevent exactly that. A confident wrong answer about which Part applies is the highest-consequence failure this system can produce.

---

## Standing risk

Every defect so far shipped green, including the two found while building the agent surface. The board reports that checks ran, not that the data is right. A2, A3, and G2 turn that into a property of the system: the checks run themselves, every ratio can be driven to fail, and the agent's own statement of its limits is computed from the data rather than remembered by a person.

---

Unofficial derived work. Current to 2025-01-16 (through O. Reg. 5/25). Not the official Building Code Compendium.
© King's Printer for Ontario, 2024. Reproduced with permission.
