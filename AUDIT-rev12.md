# Track audit — revision 12

Gate-ledger repair, Claude Code on the web, 2026-09-08. Revisions 1–11 preserved unedited.

**Headline: three ledgers carried a marker no tool defines, and repairing them was the smaller half. The larger half is that the README's completion table — the first thing under a heading reading "read this first" — has claimed ALL MET for two ledgers since 2026-09-07 while `FACTS.json`, written by the same script from the same files, recorded 15 of 16 and 6 of 7. The two sat beside each other in the repository, disagreeing, and no gate could see it.**

---

## WHAT MOVED

| item | evidence |
|---|---|
| Three ledgers repaired | `- [~]` appeared 3 times: `GATES-retrieval.md:24` (R4), `GATES-volume1.md:29` (G5), `GATES-volume2.md:19` (V3). Now 0. Each gate is `- [ ]` with an `ABANDON:` line and **no `CHECK:`** — no command can decide a superseded outcome. Marker census after: 45 `- [x]`, 4 `- [ ]`, 0 `- [~]`; one `ABANDON:` in each of four ledgers. |
| The live pointer at the vacuous check is gone | R4 carried `CHECK: python3 checks/check33_completeness.py` with `exit=0; EXPECT=matched` — the ledger that supersedes `check33` still ran it. Removed. |
| Evidence digests preserved rather than deleted | Each `ABANDON:` now quotes the removed `CHECK:` line and its `definition-sha256`. G5's own prose says the digest "is real — the check ran and exited 0 — and proves nothing about capture." That sentence is the most useful one in the ledger; deleting the digest would have removed the record of a vacuous pass while keeping the claim that it happened. |
| README's completion table corrected | All four rows now match their ledgers exactly, verified by recomputing `gen_readme.py`'s own expressions and comparing against the table's result cell: volume1 `1 abandoned, 15 of 16`; volume2 `1, 6 of 7`; emitters `1, 4 of 5`; retrieval `1, 4 of 5` — the last row added, since the ledger existed and the table omitted it. |
| The correction is stated in the README, not silently applied | The paragraph beneath the table records what it used to say, when it became false, and why nothing caught it. A completion table that quietly changes its numbers is the same defect in a new coat. |

---

## WHAT DID NOT

Every track unchanged. **7 of ~31.** `schedule.py --check` PASS; DEC1–DEC4 present.

- **`FACTS.json` is now stale on one field.** It records `abandoned: 0` for volume1 and volume2; the repair makes both 1. `ci/regenerate.sh` needs the derived data and refuses without it, so this cannot be corrected here. H3 (`check22_docs.py`) compares `facts_before == facts_after` across a regeneration and will **correctly flag the drift** on the first run with data. That is the gate working, and it is why the field was not hand-edited.
- **The durable fix is proposed, not applied.** `gen_readme.py` computes `led` and writes it only into `FACTS.json`; the README table is hand-maintained and outside the span the script regenerates. The repair is to generate that table from `led`, and to lower `check22`'s figure threshold. Both were left alone because neither can be exercised here — `gen_readme.py` reads `emitters/obc.sqlite` — and shipping an untested change to the document generator is the mistake revision 9 named.
- **`GATES-remediation.md` untouched.** Its six gates report unmet against a hand-rolled `automatic-evidence=v1` writer. The repair is to run the ledger under the tool that owns the format, with data. Not a hand-edited digest.
- The board still reports `E1 PASS, E2 PASS, DATA1 FAIL`.

---

## WHAT BROKE

1. **I introduced a dangling referent while repairing one.** Reflowing G5's and V3's prose onto the `ABANDON:` line left the sentence "The evidence digest **below** is real" pointing at nothing, since the digest now appears later in the same sentence and the `EVIDENCE:` line is gone. Caught by reading the repaired block rather than trusting the script that wrote it. Fixed in both files.
2. **My first verification of the README rows reported MISMATCH and was wrong.** The regex counted digits in the whole table row, so `volume1` and `volume2` contributed a `1` and a `2` from their filenames. The ledgers were correct and the checker was not. A verification that fails for its own reasons is worse than none, because the instinct is to go and "fix" the thing it accused.

---

## WHAT WAS FOUND

### 1. A completion claim no gate could contradict
`harden/gen_readme.py:54` counts `total=t.count("\n- [")` and `met=t.count("\n- [x]")`. A `- [~]` therefore counts toward total and not toward met, so from 2026-09-07 the script computed volume1 at 15 of 16 and volume2 at 6 of 7 — and wrote exactly that into `FACTS.json`, where it has sat ever since. The README table beside it said **ALL MET (16 of 16)** and **ALL MET (7 of 7)**.

Two things kept it alive:

- `gen_readme.py` rewrites only the span between `## What is still open` and `## Licence and attribution`. The completion table is outside it, hand-maintained, and was never regenerated.
- `check22_docs.py` requires every README figure to appear in the measured facts, but matches `\b\d[\d,]{2,}\b` and filters to `len(norm(n)) > 2`. Ledger counts are one and two digits, so `16`, `15`, `7` and `6` were never tested. **H3's guarantee has a floor at three digits**, and every number that matters here sits below it.

This is R9 — documentation is measured, not typed — in the one table a reader is told to read first, contradicted by the measured facts file in the same directory. The project has found this defect class six times in its data. This instance was in its own front matter.

### 2. The proposal that prompted this overstated one of its two supporting details
The handoff document claimed G5's and V3's evidence digests were "from the old `check4_capture` run", offering their identical `definition-sha256=fb69210e…` as the sign. That does not follow. G2 and V2 — an untouched, healthy pair — also share a digest (`105df8249507…`) across different `cwd` values, so the definition hash plainly does not cover `cwd`, and two gates with the same `CHECK` text are expected to match. The claim may be true; nothing in this repository can establish it, because no code here writes or reads `definition-sha256`, and `gate-check.mjs` is not on this machine.

Recorded because the proposal was otherwise accurate, and because a correct document with one unsupported inference is harder to audit than a wrong one.

### 3. What could not be verified about the repair itself
`gate-check.mjs` is absent, `GATE_CHECK` is unset, and the `/tmp/fixdemo` the proposal cites no longer exists. So the placement of `ABANDON:` **immediately after its gate line**, rather than at end of file where the one known-parsing example (E4) sits, is unverified here. It follows the proposal, which reports having run the tool. If the tool rejects inline placement, moving the three lines to end of file is the whole remedy — each names its gate id, as E4's does.

---

## Tally and next action

**7 of ~31 done.** No track moved. Four gates are now honestly abandoned rather than three abandoned and one malformed.

1. Publish the data tarball; set `OBC_DATA_URL`, `OBC_PDF_URL_V1`, `OBC_PDF_URL_V2`, `ANTHROPIC_API_KEY`.
2. First run with data: `ci/regenerate.sh` to clear the `FACTS.json` drift this commit creates, then `gate-check.mjs --status` over all six ledgers to confirm the repair parses.
3. Apply the durable fix — generate the completion table from `led`, lower `check22`'s threshold — with the generator exercisable.
4. `GATES-remediation.md` under `gate-check.mjs --approve`, with data.

---

Unofficial derived work. Current to 2025-01-16 (through O. Reg. 5/25). Not the official Building Code Compendium.
© King's Printer for Ontario, 2024. Reproduced with permission.
