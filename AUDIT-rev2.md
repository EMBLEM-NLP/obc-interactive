# Track audit — revision 2

Every track, audited after two execution passes today: A1 (integrate) and A3 (mutation controls). Statuses below are from live re-execution and direct inspection of the rebuilt bag, not from memory of earlier output. Revision 1 of this audit is preserved unedited in `AUDIT.md`; this file supersedes its status table but not its findings.

**Headline: 2 of 4 Track A items are now DONE. Executing A3 found three more vacuous gates — two of them foundational — and fixed them. Every other track is where revision 1 left it.**

---

## Status legend

| status | meaning |
|---|---|
| **DONE** | built, integrated into the rebuilt bag, verified by the user's own unmodified tools |
| **BUILT — pending integration** | code exists and is verified but is not in the bag |
| **MASKED, not fixed** | defect hidden at render/query time; stored data unchanged |
| **DIAGNOSED only** | found and quantified; no code addresses it |
| **PLANNED** | not started |

---

## What executing A3 found

The task was to add mutation controls to the eight ratio-reporting checks that had none. Doing so required first establishing which checks can run from the shipped bag at all — and that audit, plus the controls themselves, produced findings that change the picture more than the controls do.

### Finding 1 — the strongest-looking gates are the least reproducible

A scan of all 59 check scripts for hardcoded build-session paths:

```
runnable from the bag as-is        : 46
need an env-var override           :  5
BLOCKED (hardcoded /home/claude/…) :  8
```

The eight blocked include **`check20_determinism.py` (H1)**, **`check23_controls.py` (H4)**, `check24_metamorphic.py` (H5), and `check28_byteidentical.py` — the hardening gates. H1 and H4 are the two gates this whole review has praised most. Neither can be re-run by anyone who receives the bag. They read `/home/claude/obc/out/301880_built.pdf`, `/home/claude/emit/out/obc.sqlite`, `/home/claude/labels.json` — intermediates of the original build session that were never packaged. Their evidence digests are real; their reproducibility is not.

`verify/verify.sh` — the bag's own re-verification entry point, whose header reads *"everything else is included"* — additionally requires `unlazy/scripts/gate-check.mjs`, an external Node tool that is not in the bag. The individual check scripts print their own `RESULT:` line, so they can be run without it; the gate-board aggregation cannot.

### Finding 2 — two more gates could not fail

The controls were written as black boxes: each runs the *shipped check script* twice, once on an untouched copy of its working set (must exit 0) and once with a single output file mutated (must exit non-zero). Both directions, because a check that always fails passes a mutation-only test. This tests the check, not a reimplementation of its metric — which would have been `check33`'s error one level up.

Four of six passed first time. Two reported NEVER FAILS, and both turned out to be real:

**`check31_evalset` (R2).** Computes real word overlap between each question and its target into `q["_overlap"]` — then gates on `q["kind"] == "lexical"`, the hand-written label, and never uses the overlap it measured. Replacing 70% of question texts with nonsense left the ratio at 82%. The labels happened to be accurate; the gate just wasn't checking them. **Fixed in place**: gate on `_overlap`, and fail on any question labelled lexical that shares no content word. Now exits 1 under mutation.

**`check4_capture` (G5 and V3).** The pipeline's most foundational claim — *"content text lands in the node tree rather than being dropped."* It compares corpus-wide character multisets. The tree carries 4,697,394 characters against 2,742,659 on the page: a 71% surplus from index entries, the Act, notes, and headings, none of which are in body roles. So the tree has more of every letter than the body needs, and no amount of deletion registers.

```
untouched      orphaned      0  (0.000%)   PASS
50% blanked    orphaned  2,631  (0.096%)   PASS
100% blanked   orphaned  3,853  (0.140%)   PASS   ← 7,667 sentences, ~1.39M chars removed
```

The check's own comment records it being tuned "by ~1%." It is insensitive at 100%. **Replaced by `check4b_capture.py`**, which compares per page. Writing it took three iterations, each a false positive the old multiset never had to face — headings live in `n["heading"]` not text runs; `provenance` is a list not a dict; the reconstructed lead inserts a period the page doesn't print. The final version is punctuation-blind and reports:

```
Volume 1   orphaned  976  (0.040%)  23 pages, worst p.728 (7 lines)   PASS
Volume 2   orphaned  123  (0.008%)   3 pages                          PASS
```

Real, non-zero numbers — which is what a sensitive check looks like. Fails under the same mutation on both volumes. G5 and V3 struck in all four gate files with the evidence digest left in place and annotated: the check ran and exited 0, and that proves nothing about capture.

### Finding 3 — `check7_refs` prints a ratio it does not gate on

It prints "resolved to a node: 28430 (94.9%)" but its exit condition is `fail == 0 and bad <= 4` — zero parse failures and at most four inconsistencies in a 200-ref spot check. The percentage is decorative. The control targets the real gate (re-pointing 35% of refs at wrong articles drives `bad` far past 4) and works; noted so the number is not read as a floor.

---

## The registry as it now stands

```
in-process (check35 part 1)              floor    real   mutated
  R4a reachability                        99%   100.0%    54.5%   ok
  R4b delivery                            95%    98.6%    49.4%   ok
  R4c usability                           99%    99.9%     0.1%   ok
  R8  modality                             2%     3.2%     0.0%   ok

black-box subprocess (check35 part 2)  untouched  mutated
  check4b_capture  (G5)                   exit 0   exit 1   ok
  check4b_capture  (V3)                   exit 0   exit 1   ok
  check5_tables                           exit 0   exit 1   ok
  check7_refs                             exit 0   exit 1   ok
  check10_index                           exit 0   exit 1   ok
  check14_crossvol                        exit 0   exit 1   ok
  check31_evalset  (R2, fixed)            exit 0   exit 1   ok

proven vacuous and superseded (enumerated)
  check4_capture, check31 original gate, check33_completeness

uncontrollable from the bag (enumerated, need portability fixes)
  check0_coverage      reads the source PDF (fetch-only by design — legitimate)
  check24_metamorphic  hardcodes /home/claude/obc/out/{inventory,geometry}.jsonl.gz
```

Eleven ratio gates now have a registered mutation that drives them below their floor. Before today: zero.

---

## Track A — Integrity

| item | status | evidence |
|---|---|---|
| A1 integrate the pack | **DONE** | Rebuilt bag, 169 payload files, `check21_bagit.py` PASS, `check26_provenance.py` 5/5 PASS. See `AUDIT.md` addendum. |
| A2 CI | **PLANNED** | No CI configuration exists. The runnability audit above is the input CI needs and did not exist before today. |
| A3 mutation controls | **DONE, with two enumerated exceptions** | 6 of 8 controlled and verified; 2 uncontrollable from the bag (one legitimately, one needing a path fix). `check23_controls.py` itself remains blocked by hardcoded paths — see Finding 1. |
| A4 declared schema | **PLANNED** | No schema file exists. |

**Track A: 2 of 4 done.**

---

## Track B — Model correctness

| item | status | evidence / gap |
|---|---|---|
| B1 suppress flattened bodies before embedding | **MASKED, not fixed** | `stage19_embed.py` untouched; stored vectors still embed 303,204 chars of duplicated table prose for 179 articles. Unchanged from revision 1. |
| B2 `forming_part_of` as explicit `ref` edge | **MASKED, not fixed** | SQLite emitter still writes it two ways. Unchanged. |
| B3 heading note references | **DIAGNOSED only** | 44 of 64 still unlinked. Unchanged. |

**Track B: 0 of 3.** Unchanged.

---

## Track G — Agent surface

| item | status | evidence / gap |
|---|---|---|
| tool surface (prerequisite) | **DONE** | Integrated to `retrieval/lib/`, 6 tools verified in place, MCP registration confirmed. |
| G1 semantic search in `obc_search` | **PLANNED** | Still FTS5 + trigram only. |
| G2 computed `cannot` list | **PLANNED** | Still a hand-written list. |
| G3 tool-surface tests | **PLANNED** | No persisted test file. |
| G4 refusal evaluation | **PLANNED** | No refusal set. |

**Track G: 1 of 5.** Unchanged except integration.

---

## Track F-scope — Applicability

All four items and gates S1–S4: **PLANNED**. Zero code. Unchanged.

---

## Track D — Measurement

| item | status | note |
|---|---|---|
| D1 competency-question suite v2 | **PLANNED** | The v1 set's gate (`check31`) is now real for the first time — it verifies the property, not the label. |
| D2 agent-task evaluation | **PLANNED** | |
| D3 `check36_modality` | **PLANNED** | |
| D4 building-official review | **PLANNED** | |

**Track D: 0 of 4.**

---

## Track C — Identity and portability

Both items **PLANNED**. Unchanged.

---

## Track E — Data fidelity

All items **PLANNED** or **DIAGNOSED only**, unchanged — with two additions from today:

- **NEW — page 728, Volume 1, 7 orphaned body lines.** The first real capture residual anyone has been able to see. Belongs in Track E's investigation list.
- **NEW — eight checks hardcode build-session paths.** `check20`, `check23`, `check24`, `check25`, `check28`, `check0`, `check8`, `check11`, `check15`. Making them read from `verify/data/` would convert H1, H4, and H5 from "green but unreproducible" to reproducible. This is a small, mechanical portability fix per check, and it is the precondition for A2 meaning anything.

---

## Tracks F-objectives, F-rules

**PLANNED**, correctly unstarted. Unchanged.

---

## Phase 0 reports

Unchanged from revision 1, with one correction already recorded there: the standards review's "no RO-Crate" claim was wrong; both RO-Crate and an in-toto attestation existed at the tree root, and the audit had never listed it.

---

## Honest tally

```
DONE                         :  3   (A1, A3, G tool surface)
BUILT, pending integration   :  0   (everything built is now in the bag)
MASKED, not fixed            :  3   (B1, B2, table read-fallback)
DIAGNOSED only               :  6   (B3, E items, +page 728, +path portability)
PLANNED                      : ~18
```

Three of ~30. Revision 1 said zero. What moved is real and verified; what did not move is unchanged and stated as such.

## The finding that matters most

Five vacuous gates have now been found and fixed across this project: `check33` (R4), `check31` (R2), `check4` (G5 and V3), and the C1 control in my own first draft of `check35`. Every one of them was green. Every one had a real evidence digest. Three of them — G5, V3, R4 — guard the claims the whole artifact rests on: the text was captured, the context is complete.

None was found by reading the check. All were found by mutating its input and watching it not care. That is now a shipped, passing, registered discipline (H10) covering eleven gates — and the eight checks it cannot yet reach are enumerated with the specific path each one needs fixed.

## Immediate next action

**The portability fixes** — eight checks, one path each. They are small, they are mechanical, they convert H1/H4/H5 from unreproducible to reproducible, and they are the precondition for A2. A2 without them would be CI that cannot run the gates it exists to run.

---

Unofficial derived work. Current to 2025-01-16 (through O. Reg. 5/25). Not the official Building Code Compendium.
© King's Printer for Ontario, 2024. Reproduced with permission.
