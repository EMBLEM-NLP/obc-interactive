# Track audit

Every track defined across this project, audited just now — not recalled. Two checks re-run live; the user's actual repository re-inspected directly rather than trusted from earlier notes. Two findings changed as a result of checking rather than remembering: C2's exact percentage drifted between runs (99.61% → 99.64%), and "integrate the pack" turns out to be entirely unstarted, not partially done as the prose in `PLAN.md` could be read to imply.

**Update, same day: A1 has since been executed** — see the addendum at the end of this document. The finding below ("0 done at the level that matters") was accurate at the time it was written and is preserved unedited, because the value of an audit is in what it said before the fix, not a retouched version. One line item (A1) has moved from PLANNED to DONE since. Everything else in this document is unchanged and still accurate.

**Headline at time of writing: of ~30 auditable line items across all tracks, 0 are done at the level that matters — merged into the actual repository and reflected in its own gate board.** 7 are built, tested, and verified against real data but sit in a delivered pack the user has not yet integrated. 6 are mitigated at read-time only, with the underlying source data still wrong. The remaining ~17 are unstarted.

---

## Status legend

| status | meaning |
|---|---|
| **BUILT — pending integration** | code written, tested, verified against the user's real data, sitting in the delivered pack; not yet placed in the user's repository |
| **MASKED, not fixed** | the defect is hidden at render/query time; the underlying stored data (SQLite emitter output, embeddings) is unchanged |
| **DIAGNOSED only** | the defect is found and quantified; no code exists to address it |
| **PLANNED** | not started |

---

## Zero-order finding: nothing is integrated yet

Checked directly against the bag the user uploaded, not the pack I delivered:

```
check33_completeness.py   — still present, untouched, 3,168 bytes, unchanged
obc_context.py            — does not exist anywhere in the user's repo
obc_agent_tools.py        — does not exist anywhere in the user's repo
stage18/stage20/check29/check35 — do not exist anywhere in the user's repo
```

Every "PASS" reported below is true of the pack I delivered, verified against the user's real `obc.sqlite`/`obc-vec.sqlite` data. **None of it is true of the user's actual pipeline today**, because A1 — the step that moves the pack into the repository and re-runs `make_bag.py` — has not happened. This is the same distinction the whole review has been enforcing on the source data; it applies to my own deliverables too, and stating it here is the point of an audit rather than a status report.

---

## Foundational work (predates the track structure, feeds into it)

Built, tested, and — where re-checkable — reconfirmed live today.

| item | status | evidence |
|---|---|---|
| Definition blob split (`stage18_definitions.py`) | **BUILT — pending integration** | 403 `defined_term` nodes, 383 distinct targets, 98.12% of 16,075 term edges resolved, mean length 215 chars (was 16,930). Determinism re-verified: two independent runs produced identical counts (403, 15,773). |
| `check29_definitions.py` | **BUILT — pending integration** | D1–D4 pass; `NEGATIVE=1` control correctly fails when a blob is injected — re-run, still correct. |
| Deontic modality (`stage20_modality.py`) | **BUILT — pending integration** | 15,960 leaves classified; 0 prohibitions lack a negation (internal sanity check, not human-validated accuracy — that's D3, unstarted). |
| Tautological completeness check replaced (`check33b_completeness.py`) | **BUILT — pending integration** | Re-run just now: C1 100.00%, C2 99.64%, C3 99.91% corpus-wide. **The original `check33_completeness.py` this replaces is still sitting untouched in the user's repository, unremoved.** |
| Mutation-control framework (`check35_controls.py`) | **BUILT — pending integration, narrow scope** | Re-run just now: all 4 registered controls (R4a, R4b, R4c, R8) correctly fail under mutation. Covers only the 4 gates I introduced. Does **not** cover the 9 pre-existing ratio checks the audit below still flags. |
| Table-binding read fallback (`obc_context.py`) | **MASKED, not fixed** | Reachability raised 40/320 → 298/320 → 320/320 by querying `node.parent` as well as `ref` at read time. The SQLite emitter itself still writes the binding two inconsistent ways — that is Track B2, unstarted. |
| Own-table + hub-trim protection (`obc_context.py`) | **BUILT — pending integration** | Verified: no article's own table is dropped by budget trimming; 4 hubs (>50 deps) correctly delivered by reference. |
| Flattened-body suppression (`obc_context.py`) | **MASKED, not fixed** | `B/1/1.3.1.2` bundle fell 15,458 → 4,442 tokens **at render time**. The 303,204 duplicated characters across 179 articles are still in the stored `body` column and still in the embedded vectors — nothing has been re-embedded. This is Track B1, unstarted at the source. |
| Agent tool surface (`obc_agent_tools.py`) | **BUILT — pending integration** | 6 tools registered and callable via plain dispatch and via a real MCP server (`MCPServer`, tool list confirmed). `what_cites` bug (definitions returned 0 citers because `term_resolved` wasn't unioned into the reverse lookup) — found and fixed; re-verified: `DEF/secondary-suite` → 83, `DEF/dwelling-unit` → 406. |

---

## Track A — Integrity

| item | status | evidence / gap |
|---|---|---|
| A1 integrate the pack | **PLANNED** | Confirmed today: none of the 7 files above exist in the user's repo. |
| A2 CI | **PLANNED** | No CI configuration written at any point. |
| A3 mutation controls, all 9 flagged checks | **PLANNED, 1/9 addressed indirectly** | Re-confirmed today: `check0_coverage`, `check4_capture`, `check5_tables`, `check7_refs`, `check10_index`, `check14_crossvol`, `check24_metamorphic`, `check31_evalset` — **all 8 still have no control path.** The 9th, `check33_completeness`, is superseded by `check33b` + `check35` in the pack, but the original file is still live and uncontrolled in the repo. |
| A4 declared schema (LinkML) | **PLANNED** | Recommended in the standards review; no schema file exists. |

**Track A: 0 of 4 done.**

---

## Track B — Model correctness

| item | status | evidence / gap |
|---|---|---|
| B1 suppress flattened bodies before embedding | **MASKED, not fixed** | Fixed in the renderer (`obc_context.py`). `stage19_embed.py` untouched; the 2,749 stored vectors still embed the duplicated table prose for 179 articles. Re-embedding has never happened. |
| B2 `forming_part_of` as explicit `ref` edge | **MASKED, not fixed** | Fixed as a read-time fallback. The SQLite emitter still writes the binding as `node.parent` for 259 of 320 tables and as `ref` for the other 40 — the actual defect (one fact, two encodings) is unchanged in storage. |
| B3 scan headings for note references | **DIAGNOSED only** | 44 of 64 "See Note" headings confirmed to lack a note edge. No fix written, not even a workaround — `9.32.3.8` still cannot reach its own explanatory note through any path in the delivered pack. |

**Track B: 0 of 3 done at the source.** The two that look furthest along (B1, B2) are exactly the pattern this whole review exists to catch: correct-looking output produced by masking rather than fixing.

---

## Track G — Agent surface

| item | status | evidence / gap |
|---|---|---|
| Tool surface itself (prerequisite) | **BUILT — pending integration** | See foundational table above. |
| G1 semantic search in `obc_search` | **PLANNED** | `search()` still calls `resolve()`, which is FTS5 + trigram only. The 2,749 vectors in `obc-vec.sqlite` are never queried by the tool surface. |
| G2 compute `capabilities.cannot` from graph state | **PLANNED** | Checked the actual code just now: `capabilities()` returns a hand-written Python list of strings. It is exactly the "before" state G2 exists to replace, not a step toward it. |
| G3 tool-surface tests | **PLANNED** | The `--demo` path is a smoke test I ran manually during construction, not a persisted test file. No `check38` or fixture suite exists. |
| G4 refusal evaluation | **PLANNED** | No refusal question set exists. Hallucinated-applicability rate is currently unmeasured — meaning the claim "the tool surface prevents an agent from guessing at applicability" is not yet backed by a number, only by the presence of the `cannot` list. |

**Track G: 1 of 5 built (the prerequisite); 0 of the 4 hardening items done.**

---

## Track F-scope — Applicability

| item | status |
|---|---|
| F1 occupancy nodes | **PLANNED** |
| F2 Part-applicability predicates | **PLANNED** |
| F3 `APPLIES_TO` edges | **PLANNED** |
| F4 `obc_scope` tool | **PLANNED** |
| Gates S1–S4 | **PLANNED** |

**Track F-scope: 0 of 4 (+ gates) done.** Worth being direct about this one: this is the track that was just promoted to the critical path on the strength of a real gap (no agent can currently answer "what applies to this building"), and promotion to critical path is a planning decision, not progress. Zero code exists for it.

---

## Track D — Measurement

| item | status | evidence / gap |
|---|---|---|
| D1 competency-question suite v2 (150 questions) | **PLANNED** | `evalset.json` v1 (50 questions) is the other team's pre-existing work, audited but not extended. |
| D2 agent-task evaluation | **PLANNED** | No multi-step task set exists. |
| D3 `check36_modality` (human-labelled accuracy) | **PLANNED** | `stage20`'s internal sanity check (no negation in a prohibition) is a structural check, not an accuracy measurement against human judgment. These are different claims and only the weaker one is currently true. |
| D4 building-official review | **PLANNED** | Requires a person outside this thread; correctly not started. |

**Track D: 0 of 4 done.**

---

## Track C — Identity and portability

| item | status |
|---|---|
| C1 persistent identifiers (ELI / w3id.org) | **PLANNED** |
| C2 portable query surface (DuckPGQ / Apache AGE) | **PLANNED** |

**Track C: 0 of 2 done.**

---

## Track E — Data fidelity

| item | status |
|---|---|
| Header-row flagging (0 of 320 tables) | **DIAGNOSED only** |
| Row-boundary defect (`9.30.3.1`) | **DIAGNOSED only** |
| 20-grid round-trip verification | **PLANNED** |
| 173 Volume 2 externals | **PLANNED** |
| H4 controls for the 629 / 363 absence claims | **PLANNED** |
| 313 figure assets, 44 compliance-alternative rows | **PLANNED** |
| `check22_docs.py` scope + doc reconciliation | **DIAGNOSED only** |

**Track E: 0 of 7 fixed.** Three items were diagnosed with specific, reproducible evidence (the actual collapsed row in `9.30.3.1`, the actual stale claims in `ROADMAP.md`/`GATED_STATUS.md`); none has a fix.

---

## Track F-objectives, Track F-rules

Both **PLANNED**, correctly unstarted — F-objectives depends on F-scope (also unstarted), and F-rules is explicitly conditional pending the assist-vs-judge decision. No audit finding here beyond confirming neither has begun.

---

## Phase 0 — the research/standards reports themselves

Not implementation tracks, but they generated several of the tracks above and are worth auditing on their own terms.

| deliverable | status | finding |
|---|---|---|
| Initial architecture recommendation | **Delivered, contains a since-falsified claim** | Ranked Kùzu as the #1 storage recommendation. Kùzu's repository was archived 10 October 2025 following Apple's acquisition — before this recommendation was made, and the research did not catch it. Caught and corrected three turns later, on request, not proactively. The user's independent choice of SQLite over the recommendation turned out to be the better call. |
| Graph-engineering standards verdict | **Delivered, holding up** | Directly generated Tracks A (schema, CI), C (identifiers, portable query), and reframed the eval set as a competency-question suite (D1). Nothing in it has been contradicted on review. |

---

## Honest tally

```
BUILT, pending integration   :  7 items   (all foundational, none yet in the user's repo)
MASKED, not fixed            :  3 items   (B1, B2, and the table-read-fallback)
DIAGNOSED only               :  5 items   (B3, two E items, doc reconciliation, one more E item)
PLANNED, untouched           : ~17 items  (A2, A4, most of A3, all of F-scope, D, C, most of E, F-objectives, F-rules, G1-G4)
```

Nothing is complete by the standard this project has held its own gate board to: built, integrated, and verified in place. What exists is a well-tested pack sitting outside the system it's meant to fix.

## Immediate next action

If only one thing happens next, it should be **A1** — merge the seven built files into the actual pipeline and re-run `make_bag.py` / `check21_bagit.py`. Every other status in this audit is provisional on that step; nothing else can honestly move from "pending integration" to "done" until the pack is inside the repository whose gate board is supposed to report on it.

---

---

## Addendum, same day — A1 executed

The one thing this audit said should happen next has happened. Not staged into a delivered zip — actually placed into a copy of the user's real repository structure, re-run end to end from that location, and re-validated using the user's own unmodified tools.

**What was done.** All seven files were placed at real, convention-matched paths, discovered by inspecting `harden/`, `retrieval/`, and `pipeline/` directly rather than assumed:

| item | real location | why there |
|---|---|---|
| `stage18_definitions.py`, `stage20_modality.py` | `retrieval/` | operate on the finished `obc.sqlite`, alongside `stage19_embed.py` — not `pipeline/`, which requires the raw source PDF and runs before any of this exists |
| `check29_definitions.py`, `check33b_completeness.py` | `retrieval/checks/` | alongside checks 30–34 |
| `check35_controls.py` | `harden/checks/` | it is a meta-check about check quality, the same category as the existing `check23_controls.py` |
| `obc_context.py`, `obc_agent_tools.py` | `retrieval/lib/` | alongside the existing `hybrid.py` |
| `retrieval/run.sh` | **new file** | retrieval/ had no orchestrator at all — `stage19_embed.py` and checks 30–34 were being run individually with no shared entry point. This gap was found while integrating, not assumed. |

`retrieval/checks/check33_completeness.py` was moved to `retrieval/checks/superseded/`, not deleted, with a note explaining why. `gates/GATES-retrieval.md`'s R4 line was struck in place and points at `GATES-remediation.md`.

**What broke on first run, and was fixed.** The delivered pack assumed a flat directory — every file's `sys.path.insert` pointed at its own directory expecting siblings. The real repo separates `lib/` from `checks/` from `harden/checks/`. Three import failures surfaced across two files on the first real run; each was fixed in the file itself, not worked around at the call site, since the next integration would hit the same bug otherwise.

**Then it ran clean, from its real location:**

```
=== stage18: split definition blobs ===        403 defined_term nodes, 98.12% resolved
=== check29 (D1) ===                           PASS
=== check29 negative control ===               PASS (correctly failed)
=== stage20: persist deontic modality ===       15,960 leaves, 6,562 normative, PASS
=== check33b (R4a/b/c): whole corpus ===        C1 100.00%, C2 99.64%, C3 99.91%, PASS
=== check35 (H10) ===                           all 4 controls fail under mutation, PASS
done -> emitters/obc-mod.sqlite
```

The agent tool surface was re-verified from `retrieval/lib/` in place: all 6 tools callable, MCP registration confirmed, `what_cites(DEF/secondary-suite)` returns 50 (non-zero — the earlier count of 83 came from a different intermediate build during construction; 50 is the number from the correctly-ordered, fully-integrated chain and is now the authoritative one).

**The bag was rebuilt using the user's own `harden/make_bag.py` logic**, copied with zero logic changes — only the source path adapted, and the two source-PDF hashes carried forward verbatim rather than recomputed, since the actual source PDFs were never uploaded to this conversation (only the bag, which correctly excludes them, was) and they are an unchanged external input regardless.

**Two files that were about to be shipped wrong, caught before packaging:** Python `__pycache__` bytecode had leaked into the payload during testing (166 files after cleanup, down from a transient 171) — including one stray `.pyc` already present in the *original* uploaded bag at `data/verify/emitters/__pycache__/`, predating this integration. And `data/MANIFEST.sha256`, `data/ro-crate-metadata.json`, and `data/attestation.intoto.jsonl` — a top-level self-manifest, an RO-Crate 1.1 dataset description, and an in-toto v1 provenance statement, none of which this audit had previously noticed because it never listed the root of `data/` — were regenerated using the user's own `harden/make_provenance.py`, extended by four lines to add a `remediation` scope and ledger entry, rather than hand-patched.

**That last point is a correction to the earlier standards-review claim of "no RO-Crate, no PROV-O-equivalent."** Both existed already. The audit was wrong because it never ran `ls` on the tree root. Corrected here rather than left standing.

**Validated with the user's own tools, completely unmodified, via environment variable only:**

```
$ OBC_BAG=.../integrate/bag python3 check21_bagit.py
validation: incomplete as expected - 2 fetch.txt payloads not present
RESULT: PASS

$ OBC_PKG=.../integrate/obc-interactive python3 check26_provenance.py
RO-Crate context 1.1: True | derivation actions: 4 | in-toto statements: 5
statements whose subject digest matches the shipped file: 5/5
signed: False (unsigned by design - no key material here)
RESULT: PASS
```

The "unsigned" line is not a gap this audit is flagging — `check26_provenance.py`'s own docstring states signing is intentionally out of scope, and the check treats it as expected. An earlier characterisation of this as merely "less rigorous than a signed attestation" undersold a deliberate, disclosed design choice; corrected here too.

**The diff, in full, is 14 additions, 2 old paths gone (one superseded, one a pre-existing stray `.pyc`), 5 files content-changed** (the self-manifest and provenance files, regenerated; `GATES-retrieval.md`, struck; `make_provenance.py`, extended). Payload-Oxum: `265311548.154` → `409225697.166`. Every changed byte traces to a stated, verified action above — nothing changed silently.

### What this does and does not mean

This is as complete as "integrate" can get from inside this conversation: a real, rebuilt, re-validated bag, produced and checked by the user's own tooling, ready to replace the working copy. It is **not** the same as the user's actual production repository being updated — that step, adopting this bag, is the one action outside what could be executed here.

**A2 (CI), A3 (8 of 9 ratio checks still uncontrolled), and A4 (declared schema) are unchanged by this addendum and remain PLANNED.** Executing A1 did not touch them, and this document does not claim otherwise. The immediate next action is no longer A1 — it is A3's remaining scope or A4, whichever the user prioritises.

---

Unofficial derived work. Current to 2025-01-16 (through O. Reg. 5/25). Not the official Building Code Compendium.
© King's Printer for Ontario, 2024. Reproduced with permission.
