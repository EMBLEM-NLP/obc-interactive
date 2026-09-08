# Volume 2 ingested and merged — and how unlazy was used

## Result

**Volume 1: 15 of 16 gates met** (was 14). G15 closed.
**Volume 2: 6 of 7 gates met.**

| | |
|---|---|
| merged nodes | **27,421** (25,721 vol 1 + 1,700 vol 2) |
| roots | 23 — `A B C ACT APPA SA-1 SB-1…SB-13 SC-1 FRONT INDEX` |
| nodes with a missing parent | 0 |
| id collisions across volumes | 0 |
| Note + Supplementary citations resolved | **1,020 of 1,052 (97.0%)** |
| targets of the wrong kind or volume | 0 |

`Note A-3.1.2.` now points at `APPA/A-3.1.2.`; `SB-3` at the standard itself.
The 32 that remain are notes cited in Volume 1 that Appendix A does not contain,
and 2 Form references — the Forms section is not yet keyed.

## What generalised, and what did not

**Stages 0–2 needed no change.** 113,577 spans, 91,429 lines, 223,139 vector
primitives; bands learned from repetition; every line assigned a region; the
font-signature map applied as-is.

**Stage 3 needed a second container model, as predicted.** Volume 1's walk is
built on Division/Part contents pages and Volume 2 has no Divisions. It is
Appendix A (680 notes) plus 15 Supplementary Standards. `stage3v2_tree.py` adds
those containers; **the marker grammar underneath is unchanged** — sentences,
clauses, subclauses and the `(i)`-is-both-clause-and-roman rule all carried over,
exactly as they did for the Building Code Act.

Containers come from the running header, which names the standard each page
belongs to. That is the document stating its own structure, not an inference
about page type — and check12 validates it both ways: 16 declared, 16 built, and
all 16 container start pages carry a title naming the standard.

## Two checks that were wrong, not two defects

**Check 0 demanded exact equality with `pdftotext`** and failed Volume 2 on 13
pages. The inventory matches PyMuPDF's own extraction exactly on every one;
`pdftotext` emits some table cells repeatedly (`gypsum board` ×8 on p599). It now
asserts inventory-equals-extractor exactly — the hard, walk-proving part — plus
independent-engine agreement within 0.05%. Volume 1 still passes at zero on both.

**Check 4 reported 1.548% of Volume 2 as lost text.** It reconstructed markers
from a hard-coded list of node types, and Volume 2 introduced `note`. Every note
number and heading looked like dropped text. Rewritten generically, it reports
0.022% for Volume 2 — **and 0.000% for Volume 1**, which is better than the
0.083% it had been reporting all along. The blind spot had been hiding real
coverage.

Third time this check has flagged its own gap as a document defect.

---

# How unlazy was used

Cloned from `github.com/Leonxlnx/unlazy` and used as the skill specifies, not as
a formality.

### 1. Gates written before the work

Two ledgers, from `templates/gates-leaf.md`: `GATES.md` for Volume 1
completion, `vol2/GATES.md` for Volume 2. Each gate states one observable
outcome, and every runnable one carries a `CHECK:` and an `EXPECT:`.

### 2. Checks inspected before execution

```text
node <unlazy>/scripts/gate-check.mjs --status  GATES.md   # parses, runs nothing
node <unlazy>/scripts/gate-check.mjs --approve GATES.md   # approve, then run
```

`--status` prints the ledger without executing a single `CHECK:`. Approval binds
the command, expectation, working directory, shell, timeout and inherited `PATH`;
changing any of them requires approving again. Every commit of evidence carries a
SHA-256 of the parsed definition plus a fingerprint of the output, so a passing
gate cannot silently drift.

### 3. Two things the discipline caught immediately

**Every check exited 0 even when it printed `RESULT: FAIL`.** A gate requires
*both* a zero exit and an `EXPECT:` match, which made the exit code decorative
across all eleven checks. Fixed.

**The absence assertions had no control.** G8 claims zero dead `Launch` links,
zero disagreeing overlaps, zero pages worse than the previous build — and a
broken detector reports zero just as loudly. The skill's guidance is explicit:
test an absence check against a known positive fixture. **G9** runs the same
detectors against the pristine source and requires them to find its 819 dead
links, 18 wrong TOC targets and 2 missing ones. They do.

### 4. The unmet gates stayed visible

Nothing was quietly dropped. G15 sat unmet through several turns and only closed
when Volume 2 actually resolved. **G16** — markdown, html and sqlite emitters —
is still unmet and is not abandoned. `--status` reports `UNMET: 1 (met: 15)`, so
"Volume 1 is complete" remains false until it is written or explicitly handed off
with `ABANDON:`.

### 5. What it changed about the work

Before this, "done" was my summary of my own checks. Now it is a ledger that
fails on its own terms. The honest finding is that the discipline caught defects
in the *checks* three times over — exit codes, missing control, two type-blind
reconstructions — and each of those had been quietly weakening every "PASS" I had
reported earlier.

## Remaining

| | |
|---|---|
| G16 | markdown / html / sqlite emitters — unmet, not abandoned |
| V7 | Volume 2 rebuilt as an interactive PDF from the merged model |
| — | 32 Volume 1 notes with no Appendix A entry; 2 Form references unkeyed |
| — | 21 tables unbound; 182 standards absent from Table 1.3.1.2.; table header rows |
