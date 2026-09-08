# Fix plan

Every defect found across the three reviews, sequenced. Companion to `PHASES-v2.md`: that plan says what to build next, this says what to repair first.

Grouped into waves by **dependency**, not priority. Fixes inside a wave can run in any order; a wave should complete before the next begins, because later waves consume artifacts the earlier ones change.

---

## Status

| | count |
|---|---|
| Fixes built, tested, awaiting integration | 7 |
| Fixes identified, not yet written | 14 |
| Residuals to enumerate rather than fix | 3 |
| Estimated total | 4–5 weeks |

---

## Wave 0 — Integrate what already works *(1 day)*

No new code. Everything here is built and green in `obc-remediation-pack`.

**F1 — fold the pack into the pipeline.**

| action | item | destination |
|---|---|---|
| ADD | `stage18_definitions.py` | `pipeline/`, in `run.sh` after stage 7 |
| ADD | `stage20_modality.py` | `pipeline/`, after stage 18 |
| ADD | `check29_definitions.py` | `pipeline/checks/` |
| ADD | `check35_controls.py` | `pipeline/checks/` |
| **REMOVE** | `check33_completeness.py` | delete from pipeline; keep in history |
| ADD | `check33b_completeness.py` | `retrieval/checks/` |
| UPDATE | `obc_context.py` | `retrieval/lib/` |
| ADD | `GATES-remediation.md` | `gates/`, registering D1, R4a–c, R8, H10 |
| UPDATE | `GATES-retrieval.md` | strike R4; point at R4a–c |

**Verify:** `sh run.sh obc.sqlite` ends green; `make_bag.py` + `check21_bagit.py` revalidate; `Payload-Oxum` updated.

**Note:** R4 is currently marked `[x]` on a gate that cannot fail. Until F1 lands, the board is reporting a pass that does not exist.

---

## Wave 1 — Model-changing fixes *(3 days)*

These three all alter the model or the vectors. **Do all three, then re-embed once.** Re-embedding after each is three times the cost for the same result.

**F2 — UPDATE `stage19_embed.py`: suppress flattened article bodies before embedding.**

179 of 1,640 body-bearing articles repeat their entire table as run-on prose in `body`. Mean body for those articles is 1,693 characters against 91 for articles without a table — 303,204 characters of duplicated grid, and it is what got embedded. `B/11/11.5.1.1` contributes 126,177 characters; `B/1/1.3.1.2` contributes 56,202.

Reuse the `FLAT_BODY_CHARS` / `owns_table` logic already in `obc_context.py` so the assembler and the embedder agree on what an article's text is. They must not diverge.

**Verify:** `embed_meta.vectors_sha256` changes; count of articles whose embedded text exceeds 2,000 characters drops to near zero; **recall@5 on the current eval set must not regress**. If it does, the suppression is cutting real text and the threshold is wrong.

**F3 — UPDATE the SQLite emitter: write `forming_part_of` as an explicit `ref` edge.**

299 of 320 tables carry `forming_part_of` in the JSONL; only 40 became `ref` edges. The other 259 survive only as `node.parent`. Two encodings of one fact is exactly how they went missing — my first assembler followed `ref` alone and silently dropped 87% of tables.

**ADD `check37_tables.py`:** every table binds by both encodings and the two counts agree. Control: delete the `ref` edges and require the count mismatch to fail the check.

**F4 — UPDATE `stage7`: scan headings for note references.**

44 of 64 nodes whose heading contains "See Note" have no `note` edge. `9.32.3.8` — heading *Protection Against Depressurization (See Note A-9.32.3.8.)* — carries no link to its own explanatory note. Stage 7 scans body text only.

**Verify:** count of "See Note" headings without a note edge → 0. **Control:** disable the heading scan and require the count to return to 44.

**Then:** re-run `stage19_embed.py` once. Re-run `check33b` in `--all-articles` mode.

---

## Wave 2 — Verification integrity *(2 days)*

The highest-leverage wave. Three real defects have shipped green so far, and all three were invisible because the check that should have caught them could not fail.

**F5 — ADD H10 controls to every ratio-reporting check.**

Audit result: **9 of 57 checks report a ratio. Exactly 3 checks in the whole pipeline have any control path** (`check23_controls`, `check27_actions`, `check34_control`), and none of the three covers a ratio.

| check | control to register |
|---|---|
| `check0_coverage` | drop a page range; coverage must fall |
| `check4_capture` | blank a body; capture must fall |
| `check5_tables` | delete cell rows; table completeness must fall |
| `check7_refs` | delete ref rows; resolution rate must fall |
| `check10_index` | drop index entries; must fall |
| `check14_crossvol` | delete Volume 2 nodes; cross-volume resolution must fall |
| `check24_metamorphic` | perturb an input the transform should be sensitive to |
| `check31_evalset` | inject a question whose target does not exist |
| ~~`check33_completeness`~~ | **removed — metric cannot fail** |

**The rule, written into `check35_controls.py`:** a mutation must target the *mechanism* under test, never the ground truth the mechanism is scored against. Writing this caught a fault in my own C1 control — deleting the `ref` table shrank numerator and denominator together and left the ratio at 100%, the same tautology as `check33` one level up. Parameter mutations (`hops=0`, `budget=200`) and mechanism-only data mutations avoid it.

**Extend `check23_controls.py`** to enumerate the ratio checks and fail if any lacks a registered mutation, so a new ratio gate cannot be added without one.

**F6 — UPDATE `check22_docs.py` scope, and reconcile the docs.**

`ROADMAP.md` and `GATED_STATUS.md` still describe Phases 5–9 as future and G15/G16 as UNMET. The artifacts contradict this: emitters ship, Volume 2 is merged, the Act and Index are parsed, and the built-from-model PDF carries 37,370 links against the patched v9's 27,928. `check22_docs.py` passes over both files, so H3 overstates what it guarantees.

Extend its scope to `reports/*.md`. Move closed items to `CHANGELOG.md`.

---

## Wave 3 — Measurement capacity *(1 week)*

Nothing after this wave can be trusted further than the eval set can measure.

**F7 — ADD eval set v2.**

The `test` split is 27 questions of which **5** are `paraphrase`. R3's central claim — that the vector layer earns its place where lexical retrieval fails — rests on those five. No hub article appears anywhere in the set, which is why the 90.06% delivery problem was invisible until the corpus run.

- 150 questions, **≥40% paraphrase**.
- Include the four hubs (`B/1/1.3.1.2`, `B/11/11.5.1.1`, `B/9/9.41.2.2`, `B/3/3.2.2.18`), Division C, the Act, and Supplementary Standards.
- Keep the SHA-256 split, the dev-only weight tuning, and the no-shared-content-word constraint on paraphrases. Those are already right.
- Keep the stated limitation about official review — and try to close it.

**F8 — ADD `check36_modality.py`.**

`stage20` classifies 15,960 leaves (38.0% obligation, 6.6% permission, 3.6% exemption, 3.2% prohibition, 48.7% statement) with no accuracy measurement. H10 covers the *mechanism* — ablating the prohibition rule drives prohibition share to 0.0% — but not whether the labels are right.

Needs a 200-sentence stratified hand-labelled sample, ≥98% agreement. This requires a human. Record provenance as honestly as `evalset.json` does.

**Highest-value external input available:** a building official reviewing 30 eval questions and 50 modality labels. Two days of someone's time removes the largest unquantified risk in the project.

---

## Wave 4 — Table fidelity *(1–2 weeks)*

Blocks Phase 13. Numeric compliance checking over tables whose rows are wrong is worse than none.

**F9 — ADD header-row flagging.** 0 of 320 tables mark header rows. Multi-level headers render as blank-heavy grids: in `9.23.4.2.-L`, "Specified Snow Load, kPa" spans five unlabelled columns. Forward-fill merged headers.

**F10 — FIX row boundaries.** Now visible in `9.30.3.1`: `Matched hardwood (interior use only) 400 7.9 19.0 600 7.9 33.3` is a whole logical row collapsed into one cell. A reproducible instance of the gap-register item.

**F11 — ADD round-trip verification.** 20 grids diffed against their source page region. Control: perturb a cell and require the diff to fail.

---

## Wave 5 — Residuals and absence claims *(1 week)*

**F12 — resolve the 173 remaining Volume 2 externals** (111 supplementary standard, 60 Appendix A, 2 forms). G15 cannot close otherwise.

**F13 — ADD H4 controls to the absence claims.** 629 `not-in-this-edition` and 363 `not-in-Table-1.3.1.2` are assertions that something is *absent*. A detector that reports these because it is broken looks identical to one reporting them because they are true. Verify a sample against the printed Code.

**F14 — bind the remainder:** 313 figure assets, 44 compliance-alternative rows (these feed the `B/11/11.5.1.1` hub), 13 notes-to-table blocks.

---

## Wave 6 — Only after F2 and F7 *(3 days)*

**F15 — embedding model experiment.** `all-MiniLM-L6-v2` (384-dim) is a reasonable default and probably weak on technical and legal text. Rebuilding 2,749 vectors is cheap.

**Do not start before F2 and F7.** With flattened table text still in the embedded corpus the experiment measures noise, and with 5 paraphrase questions in `test` there is no power to detect an improvement either way.

---

## Enumerate, do not fix

Three items should be recorded as permanent residuals rather than chased. Each is already enumerated in a check so the set cannot grow silently.

1. **11 definition terms containing a comma or slash** (`boarding, lodging or rooming house`, `class 1 fire sprinkler/standpipe systems`, `live/work unit`). Admitting those characters to the boundary grammar would split on any capitalised list item. Cost of the residual: 302 of 16,075 term edges.
2. **`DEF/cavity-wall` remains merged.** The next term is *Certificate for the occupancy of a building described in Sentence 1.3.3.4.(3) of Division C* — fifteen words containing periods. No word cap safe for ordinary terms captures it.
3. **`B/11/11.5.1.1` renders at 11,830 tokens** even after hub policy and flattened-body suppression, because it owns five large tables. Decide explicitly: a per-table row cap for hubs, or accept that one article exceeds an 8,000-token budget and say so. Do not let it sit undecided.

---

## Sequencing

```
W0  integrate the pack           1 day    ── R4 is green today and cannot fail;
                                             this is the first honest board
W1  model-changing fixes         3 days   ── F2+F3+F4 together, ONE re-embed
W2  verification integrity       2 days   ── highest leverage; 9 ratio checks,
                                             0 controls between them
W3  measurement capacity         1 wk     ── nothing later is trustworthy
                                             beyond what this can measure
W4  table fidelity               1-2 wk   ── blocks Phase 13
W5  residuals + absence claims   1 wk     ── parallel with W4
W6  model experiment             3 days   ── strictly after W1 and W3
```

**Assumptions:** one to two engineers; source edition stable; a human available for two days of labelling in W3.

**Risks:**

1. **Skipping W2 because W1 feels more productive.** Every defect found so far shipped green. Controls are cheap; the reason tautological metrics survive is that nobody is required to write one.
2. **Re-embedding three times.** F2, F3 and F4 all invalidate vectors. Batch them.
3. **Running W6 early.** A model comparison on a noisy corpus with five paraphrase questions produces a number with no meaning, and it will be believed.
4. **Leaving residual 3 undecided.** An article that silently exceeds every budget is the kind of thing that resurfaces as a production bug.

---

Unofficial derived work. Current to 2025-01-16 (through O. Reg. 5/25). Not the official Building Code Compendium.
© King's Printer for Ontario, 2024. Reproduced with permission.
