# Track audit — revision 3

Audited after the portability pass. Revisions 1 and 2 preserved unedited. Every status below is from live execution against the rebuilt bag.

**Headline: the three hardening gates that could not be re-run by anyone receiving the bag — H1, H4, H5 — now run from it and pass. Doing that found a sixth vacuous gate and pinned the build's only nondeterminism to a single date string. A2 is now unblocked. Every other track is unchanged.**

---

## What was wrong with "one line each"

The previous audit said the portability fixes were "one line each." They were not. Nine files carried **31 build-session literals** (my scan had under-counted by two), and four of the nine needed more than a path swap. Recorded here because the summary overstated the simplicity and the correction should travel with the work.

| file | literals | what it actually needed |
|---|---|---|
| `check23_controls.py` (H4) | 6 | path swaps only — the big win |
| `check24_metamorphic.py` (H5) | 5 | path swaps, **then MR1 was found vacuous and rewritten** |
| `check20_determinism.py` (H1) | 3 | path swaps, **plus `emit_common.py` hardcoded its own input**, plus a build-order fix |
| `check25_normalisation.py` | 3 | path swaps |
| `check28_byteidentical.py` | 4 | needs the source PDF — clear failure added |
| `check11_deliverable.py` | 2 | path swaps |
| `check8_build.py` | 4 | needs the source PDF *and* the v9 baseline PDF, never packaged |
| `check15_vol2build.py` | 2 | needs the source PDF |
| `check0_coverage.py` | 1 | needs the source PDF |
| `emit_common.py` | 1 | the shipped emitters could not rebuild from the bag |

All 31 now resolve from the package root with env-var overrides, using the names `verify/verify.sh` already exports. Bare literals remaining across all 60 check and emitter files: **0**.

---

## Findings from running what was previously unrunnable

### The emitters themselves could not rebuild from the bag

`emit_common.py` hardcoded `GRAPH = "/home/claude/obc2/out/docgraph-merged.jsonl.gz"`. The three emitter stages that produced the shipped `obc.sqlite`, Markdown, and HTML read that one constant. A recipient could not have regenerated any of the derived formats. Fixed to default to `model/docgraph-merged.jsonl.gz`. After the fix, `stage15_sqlite.py` rebuilds from the bag with identical counts — 27,421 nodes, 139,967 closure rows, 29,952 refs, 16,075 terms, 144 amendments, 21,313 cells, 62,369,792 bytes.

### The build's only nondeterminism, pinned to one field

The rebuilt database was **not byte-identical** to the shipped one. Same row content, same page count, same freelist, same SQLite version. Per-table digests identified the whole difference:

```
meta.generated:  '2026-09-06'  vs  '2026-09-07'
```

`stage15` wrote `time.strftime("%Y-%m-%d")` — the wall clock — into `meta`. Every other table, every index, and the file header were byte-identical. `check20`'s docstring claims "byte-identical outputs" and cites `SOURCE_DATE_EPOCH` as the fix for timestamps; its actual SQLite test was a content digest over six tables that **excludes `meta`** — precisely where the clock read lived. The gate passed while the claim was false by exactly one string.

Fixed at both ends: `stage15` derives `generated` from `SOURCE_DATE_EPOCH` when set (as the PDF builders already did), and `check20` now hashes the whole file across two fresh builds. Result: `sqlite whole-file sha256: byte-identical`, and `meta.generated = 2025-01-17` from the epoch.

The shipped `emitters/obc.sqlite` still carries `2026-09-06` and will not match a recipient's rebuild until the next emitter run — Track B's re-embed batch. Not replaced in this pass, deliberately; doing so cascades into `obc-vec` and `obc-mod`.

### H1 crashed from a clean bag

`check20` digested `out/obc.sqlite` *before* building it, assuming a prior session had left one there. From a clean checkout: `no such table: node`. Worse, as written it compared "whatever was there" against one fresh build, which would pass if the stale file came from the same code. Now builds twice and compares the two.

### MR1 — the sixth vacuous gate

`check24`'s text-conservation relation used the same corpus-wide character multiset as `check4`, against an even larger tree (the merged graph). Proven the same way:

```
all 7,667 sentences blanked  →  MR1: 0.141% unaccounted  →  PASS
```

A metamorphic relation that holds under total destruction of its input is not a relation. Replaced with the per-page method from `check4b`. Now reports **0.040% untouched** — 976 characters, exactly `check4b`'s Volume 1 figure — and **43.956% FAIL** under the same mutation.

### H4's capture control never touched `check4`

`control_orphan` in `check23` blanks a node's text and asserts `before - after > 100`. It tests that deleting characters reduces a character count. It never invokes `check4`, which is why H4 was green over a capture gate that could not fail. `check35`'s black-box entry for `check4b` now does what this control only appeared to.

### Four checks that need the source PDF now say so

`check0`, `check8`, `check15`, `check28` cannot run without the fetch-only source PDFs — correctly, by design. They now exit with `RESULT: FAIL - set OBC_SRC_V1 to the path of the source PDF; it is fetch-only (see fetch.txt)` instead of a traceback. Anyone with the PDFs runs them through `verify.sh`'s existing variables. `check8` additionally needs the hand-patched v9 PDF, which was never packaged and is enumerated as such.

---

## Bugs in my own patch, caught by running it

Four, none of which survived to the bag:

1. `for _v in ("OBC_SRC_V1"):` — a one-element tuple without its comma iterates over characters. The guard printed "set O". Fixed.
2. `check8` and `emit_common` lacked `import os` after the rewrite. Fixed.
3. `check28` never names the source PDF syntactically — it runs a stage that needs it — so the literal-driven guard missed it. Added explicitly.
4. The `check24` registry entry set its cwd one level too deep; `_exit` prepends `checks/`, so it looked for `harden/checks/checks/` and reported NEVER PASSES with exit 2. Exit 2 is "file not found," not "the check failed" — I distinguished them before concluding anything. Fixed.

---

## The registry as it now stands

```
in-process                              floor    real   mutated
  R4a reachability                       99%   100.0%    54.5%   ok
  R4b delivery                           95%    98.6%    49.4%   ok
  R4c usability                          99%    99.9%     0.1%   ok
  R8  modality                            2%     3.2%     0.0%   ok

black-box                            untouched  mutated
  check4b_capture  (G5)                  exit 0   exit 1   ok
  check4b_capture  (V3)                  exit 0   exit 1   ok
  check5_tables                          exit 0   exit 1   ok
  check7_refs                            exit 0   exit 1   ok
  check10_index                          exit 0   exit 1   ok
  check14_crossvol                       exit 0   exit 1   ok
  check24_metamorphic (H5, MR1 fixed)    exit 0   exit 1   ok   ← new today
  check31_evalset  (R2, fixed)           exit 0   exit 1   ok

proven vacuous, superseded, enumerated
  check4, check31 original gate, check33, check24 MR1 original, check23 control_orphan

uncontrollable from the bag
  check0_coverage — reads the fetch-only source PDF; legitimate, permanent
```

Twelve ratio gates falsifiable. One remains uncontrollable and is uncontrollable for the right reason.

---

## Gates, re-run from the rebuilt bag with the user's own unmodified scripts

```
H1  check20_determinism    PASS   (first time reproducible; now whole-file byte-identical)
H2  check21_bagit          PASS
H4  check23_controls       PASS   (first time reproducible; 5/5 seeded defects detected)
H5  check24_metamorphic    PASS   (first time reproducible; MR1 now real)
H8  check26_provenance     PASS   (5/5 in-toto subjects match)
H10 check35_controls       PASS   (12 ratio gates)
```

---

## Track status

| track | item | status | change |
|---|---|---|---|
| A | A1 integrate | **DONE** | — |
| A | A2 CI | **PLANNED, now unblocked** | the precondition — gates that run from the bag — exists |
| A | A3 mutation controls | **DONE** | 12 controlled; the one exception is permanent by design |
| A | A4 declared schema | **PLANNED** | — |
| A | *portability* (new) | **DONE** | 31 literals, 60 files, 0 remaining; H1/H4/H5 reproducible |
| B | B1, B2, B3 | unchanged | shipped `obc.sqlite` still carries the clock date; fixes at next emitter run |
| C | C1, C2 | PLANNED | — |
| D | D1–D4 | PLANNED | `check31` now enforces the property, not the label |
| E | all | PLANNED / DIAGNOSED | — |
| F-scope | F1–F4 | PLANNED | — |
| G | surface | DONE; G1–G4 PLANNED | — |

**Honest tally: 4 of ~30 done** (A1, A3, portability, G surface). Revision 1 said zero; revision 2 said three.

---

## What this pass established

Six vacuous gates have now been found across this project, and the pattern is exact enough to state as a rule:

**Every corpus-wide aggregate over a structure with surplus is vacuous.** `check4`, `check24` MR1, and `check23`'s orphan control all compared totals where the "captured" side was 71% larger than the "source" side. Nothing removed from the smaller side could register. The per-page comparison works because it removes the surplus from the denominator.

**Every gate that excludes something from its digest is blind to exactly that thing.** `check20` excluded `meta`; the nondeterminism was in `meta`. `check33` excluded nothing but scored a set against itself.

**Green with a real digest proves the check ran. It proves nothing else.** Every one of the six had one.

## Immediate next action

**A2 — CI.** For the first time, the gates it would run can actually run: 52 of 60 check files from the bag alone, 4 more with the source PDFs, 1 needing an unpackaged artifact. A runner that executes `retrieval/run.sh`, the H-series, and `check35` on every commit is now a build task, not a hope.

---

Unofficial derived work. Current to 2025-01-16 (through O. Reg. 5/25). Not the official Building Code Compendium.
© King's Printer for Ontario, 2024. Reproduced with permission.
