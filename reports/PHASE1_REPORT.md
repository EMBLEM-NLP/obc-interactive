# Phase 1 — inventory, geometry, structure. Feasibility gate: PASS

Input is the **pristine source PDF**, not any of the linked builds. Every stage
reads the previous stage's file, never the PDF again, so the interpretation
layers are cheap to rerun and reproducible from source.

```
./run.sh /mnt/user-data/uploads/301880.pdf      # ~35s end to end
```

## Stage 0 — page inventory  `out/inventory.jsonl.gz` (4.8 MB)

165,960 text spans with font, size, colour and bbox; 108,037 lines;
105,106 vector primitives; 1,312 images; 2,808 existing link annotations.
Nothing is interpreted at this stage.

**Check 0 — character coverage: PASS.** 2,807,272 characters in the inventory
against 2,807,035 from an independent `pdftotext` extraction. **Zero pages** have
a glyph that `pdftotext` renders and the inventory lacks. Nothing downstream can
silently lose text.

## Stage 1 — geometric classification  `out/geometry.jsonl.gz` (101 KB)

Header and footer bands are **learned from corpus repetition**, not hardcoded:
text keyed with digits masked, keys appearing on ≥5% of pages and sitting in the
top 10% or bottom 12% of the page are running furniture. Learned bands: y ≤ 43
and y ≥ 746. Six running keys. The repeated 300×91 logo is identified the same
way and excluded from figure detection.

Regions come from connected components of vector primitives:

- **table** — rules aligned on ≥3 distinct y levels and ≥2 distinct x levels
- **figure** — ≥25 primitives, >80×60pt, not a lattice — plus non-logo raster images

Every one of the 108,037 lines is assigned a region. **Zero unassigned.**

| role | lines |
|---|---|
| body | 63,520 |
| table | 35,044 |
| header | 4,895 |
| footer | 4,578 |

**Check 1 — two-way region validation: PASS.** 362 pages declare a Table,
370 have a detected table region; 22 declare a Figure, 33 have a figure region.
**Zero declared regions went undetected** in either direction. The surplus is
legitimate: uncaptioned tables in the Preface (pp. 11, 24–27), second tables
sharing a page with another caption (pp. 382, 477, 479), and uncaptioned
graphics (letterhead p. 1, signature p. 2).

## Stage 2 — structural roles  `out/roles.jsonl.gz` (124 KB)

The signature map was **profiled from the corpus first** (`stage2_profile.py`),
then applied — not assumed:

| signature | role | count |
|---|---|---|
| Arial-Black 16, `Section N.N` | section | 325 |
| Arial-Black 13, `N.N.N.` | subsection | 670 |
| Arial-Black 11, `N.N.N.N.` | article | 2,673 |
| Arial-Black 10, no number | label / Act marginal note | 2,767 |
| Times-Bold 10, line-initial `N(1)` | act_section | 85 |
| `(1)` | sentence | 8,047 |
| `(a)` | clause | 6,916 |
| `(i)` | subclause | 878 |

2,673 detected articles against 2,670 counted independently in the earlier work —
agreement to within 3.

## Check 2 — the feasibility gate: PASS

Reconciles what the printed contents pages **declare** against what the detector
**found**, per contents block, with page ranges derived from where the contents
pages fall — **no footer parsing anywhere**.

```
total declared 785 | detected at the same depths 785
detected deeper than the contents lists 2,674 (Articles — expected)
declared but NOT detected : 0
detected but NOT declared : 0
```

Both directions clean across all 18 contents blocks.

## What the gate caught

Three defects and two false alarms, all found by the checks rather than by
reading output:

1. **Dense span tables were classified as figures.** Requiring rules to be
   ≥40pt long missed tables whose cell rules are shorter than that. Fixed by
   testing *alignment* — repeated y and x levels — instead of length. Recovered
   pp. 610, 994, 995 and ~27,000 table lines.
2. **`Section 1.1 General` and `Section 5.5  Vapour Diffusion` have no period
   after the number** in the source. The pattern required one. Two real headings
   were invisible. Trailing period is now optional.
3. **`Section 4.1 of the Act` was detected as a heading.** It is a citation.
   Excluded when followed by `of`.
4. *False alarm:* 23 pages "declared a Table but had none" — the test was
   matching body sentences that merely begin with `Table 3.2.3.7. shall be met.`
   A caption is the designator alone, bound by a following `Forming Part of` line.
5. *False alarm:* `3.15.3`, `3.15.5`, `9.10.4`, `9.1` looked like headings absent
   from the printed contents. They are in the contents — written without trailing
   periods, which the check's own extraction required.

Point 5 is worth dwelling on. My first instinct was to report those as gaps in
the ministry's contents pages. They were gaps in my test. Two-way checks are only
as good as both sides of the comparison, and the loose side is usually the one
you wrote most recently.

## Files

| | |
|---|---|
| `stage0_inventory.py` | PDF → span/primitive inventory |
| `stage1_geometry.py` | inventory → regions, columns, header/footer bands |
| `stage2_profile.py` | font-signature profiler (run before changing the role map) |
| `stage2_roles.py` | inventory + geometry → per-line structural role |
| `checks/check0_coverage.py` | character coverage vs pdftotext |
| `checks/check1_regions.py` | two-way table/figure region validation |
| `checks/check2_headings.py` | two-way heading reconciliation — the gate |
| `run.sh` | full pipeline + all checks |

## Next: Phase 2 — tree assembly

Stage 3 walks pages in order, pushing and popping on section/subsection/article
roles and attaching sentences, clauses and subclauses by marker and indent.
Output is `docgraph.json` with stable namespaced IDs.

The gate for Phase 2 is **numbering continuity**: within every parent, numbers
must run consecutively with gaps only where the node is Reserved or Repealed.
That check will independently confirm or refute the earlier finding that the
Index cites `5.10.1.1.` 42 times while Division B Part 5 has no Section 5.10.

Division A and Division C should be built first — small, and they carry the
cross-division reference cases that break naive resolvers.
