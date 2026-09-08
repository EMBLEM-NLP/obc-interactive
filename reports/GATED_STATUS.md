# Gated status — Volume 1 and Volume 2

Run under `unlazy` (github.com/Leonxlnx/unlazy), cloned and used as intended:
gates written before execution, checks inspected then explicitly approved, every
result carrying a definition digest and an output fingerprint.

```
node <unlazy>/scripts/gate-check.mjs --status  GATES.md    # parse, execute nothing
node <unlazy>/scripts/gate-check.mjs --approve GATES.md    # approve, then run
```

## Volume 1 — 14 of 16 gates met. Not fully complete.

| gate | outcome | |
|---|---|---|
| G1 | glyph capture, two engines | **met** |
| G2 | table/figure regions, two-way | **met** |
| G3 | structure vs printed contents, two-way | **met** |
| G4 | numbering continuity | **met** |
| G5 | text capture into the tree | **met** |
| G6 | table cell integrity | **met** |
| G7 | citation resolution, zero parse failures | **met** |
| G8 | model build ⊇ hand-patched build | **met** |
| G9 | control: the absence checks detect known defects | **met** |
| G10 | amendment markers 149/149 | **met** |
| G11 | Index entries and citations | **met** |
| G12 | shipped file opens, protected, text intact | **met** |
| G13 | figure assets bound to captions | **met** |
| G14 | licence and modification record | **met** (manual) |
| **G15** | **Volume 2 targets resolve** | **UNMET** |
| **G16** | **markdown / html / sqlite emitters** | **UNMET** |

So the honest answer to "is Volume 1 fully complete": **no**. The PDF deliverable
and the document model are complete and verified. Two declared outcomes are not:
1,054 references still point at Volume 2, and the non-PDF emitters do not exist.
Neither is abandoned; both are open work with a gate holding them visible.

### Two changes the gating forced

**Every check now exits non-zero on failure.** They previously printed
`RESULT: FAIL` and exited 0. Under a ledger that requires both a zero exit and an
`EXPECT:` match, that made the exit code decorative. Eleven checks fixed.

**A control gate was added (G9).** G8 asserts absences — zero dead `Launch`
links, zero disagreeing overlaps, zero pages worse than the previous build. A
broken absence check also reports zero. G9 runs the same detectors against a
known positive fixture, the pristine source, and requires them to find its 819
dead links, 18 wrong TOC targets and 2 missing ones. They do.

## Volume 2 — 2 of 8 gates met

`301881.pdf`, 1,001 pages, 26.9 MB, and unlike Volume 1 it carries an AcroForm.

| gate | outcome |
|---|---|
| V1 | glyph capture | **met** |
| V2 | table/figure regions | **met** |
| V3 | node tree | UNMET |
| V4 | Appendix A notes addressable | UNMET |
| V5 | Supplementary Standards addressable | UNMET |
| V6 | graphs merged | UNMET |
| V7 | Volume 1's 1,054 external refs resolve | UNMET |
| V8 | Volume 2 rebuilt as an interactive PDF | UNMET |

### What generalised, and what did not

**Stages 0–2 generalised without a code change.** 113,577 spans, 91,429 lines,
223,139 vector primitives inventoried; header and footer bands learned from
repetition; all 91,429 lines assigned a region with zero unassigned; the font
signature map applied unchanged.

**Check 0 did not generalise, and it was the check that was wrong.** It required
exact character equality with `pdftotext`. Volume 2 failed it on 13 pages. The
inventory reproduces PyMuPDF's own extraction exactly on every one of those
pages; the disagreement is between the two engines. `pdftotext` emits some table
cells repeatedly — `gypsum board` eight times on p599, `Type` eight times — and
a handful of control bytes in the Forms section. Nothing was lost.

The check now makes two assertions instead of one: the inventory must equal the
extractor's own text exactly, which proves the walk is lossless and is a hard
requirement; and an independent engine must agree within 0.05% overall and 200
characters on any page, which keeps a non-circular cross-check without failing on
tokenisation. Volume 1 still passes at zero difference on both parts.

**Stage 3 does not generalise, and that is real work, not a patch.** It is built
around Division/Part contents pages. Volume 2 has no Divisions. Its running
headers show a different shape entirely:

```
Div. B • A-#.#.#.#.(#)        156 pages    Appendix A notes
MMAH Supplementary Standard SB-#   373 pages
MMAH Supplementary Standard SA-#   187 pages
```

580 Appendix A note ids and 15 Supplementary Standards (SA-1, SB-1…SB-13, SC-1)
are already visible in the inventory. What stage 3 needs is a second container
model — `A/<note-id>` and `SB-n/<clause>` — sitting beside the Division walk and
selected per page group. The marker grammar underneath should carry over
unchanged, exactly as it did for the Act.

## Next

1. Volume 2 container model in stage 3 (V3), then V4 and V5 follow from it.
2. Merge the graphs (V6) — the ID scheme already namespaces by division, so
   `SB-3` and `A-3.1.2.` become nodes like any other.
3. V7 then measures itself: rerun check 7 on Volume 1 and watch the 1,054
   `external (Volume 2)` reason codes turn into resolutions.
4. V8 and G15 close together.
5. G16, the emitters, stays open and visible.
