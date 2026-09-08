# Phase 2 — tree assembly. Gate: PASS

```
./run.sh /mnt/user-data/uploads/301880.pdf     # ~40s, all five checks
```

## Stage 3 — `out/docgraph.jsonl.gz` (1.4 MB, 18,174 nodes)

| type | count |
|---|---|
| sentence | 7,177 |
| clause | 5,973 |
| article | 2,702 |
| subclause | 1,398 |
| subsection | 647 |
| section | 150 |
| act_section | 85 |
| part / contents | 18 / 18 |
| division | 3 |
| act, front_matter, index | 1 each |

Every node carries a namespaced ID, a parent, children, text and page+bbox
provenance:

```json
{"id": "B/9/9.10.16.1", "type": "article", "number": "9.10.16.1",
 "parent": "B/9/9.10.16",
 "children": ["B/9/9.10.16.1/(1)", "…/(2)", "…/(3)", "…/(4)", "…/(5)", "…/(6)", "…/(7)"],
 "provenance": [{"page": 794, "bbox": [36.0, 624.9, 98.4, 639.4]}]}
```

Division and Part come from the title text on each contents page. All 18 Parts
and their page ranges were derived correctly. The Building Code Act (pp. 33–74)
and the Index (pp. 1197–1260) were located **structurally** — the Act by its
`N(1)` bold section starts, the Index as the trailing run of pages carrying no
structural heading at all. No footer string is read anywhere in the pipeline.

## Gates

| check | result |
|---|---|
| 0 character coverage vs pdftotext | PASS — 0 pages missing a glyph |
| 1 two-way table/figure regions | PASS — 0 declared regions undetected |
| 2 two-way heading reconciliation | PASS — 785 / 785, 0 either direction |
| **3 numbering continuity** | **PASS — 4,609 parents, 0 unexplained gaps** |
| **4 text capture into the tree** | **PASS — 0.052% orphaned** |

## What the continuity gate caught

It started at **2,460 unexplained gaps** and ended at zero. Four distinct defects,
each invisible to eyeballing:

**1. `(i)` is both clause letter *i* and roman subclause *i*.** 2,181 gaps.
Pattern order alone always got one case wrong. Indent helped but broke across
column boundaries. What actually works is sequence: `(i)` is a clause only when
*i* is the letter the clause list expects next — after `(h)` it is a clause,
after `(b)` it is a subclause. No geometry required.

**2. Wrapped lines read as new markers.** `(4), (5) or (7) are met.` is the tail
of sentence (1), not sentence (4). Fixed by the same rule: a marker is accepted
only if it is the next in sequence, or a decimal insertion like `(1.1)`.

**3. Numbers that do not belong to their Part.** `3.2.2.60.` was being adopted as
a child of Division C subsection `1.3.3` — it is a reference inside a table.
A heading whose first component is not the current Part number is now rejected.

**4. Letter-suffixed articles were invisible.** `7.6.2.5A. Backflow from Buildings
with a Solar Domestic Hot Water System` did not match the number pattern at all,
so it was missing from the tree entirely and showed as a hole at position 5.
32 more articles were recovered by allowing the suffix — the article count moved
from 2,670 to 2,702.

That fourth one is worth noting: the continuity gate found a *missing article*,
not a numbering quirk. Nothing in the earlier link-patching work could have
surfaced it, because a heading that is never detected is never missed.

## On the earlier `5.10.1.1.` finding

The gate confirms it. Division B Part 5 ends at Section 5.9; there is no Section
5.10 anywhere in the volume, and the tree has no node for it. The Index cites
`5.10.1.1.` 42 times. That is a defect in the source document, now independently
established by structure rather than by a failed lookup.

## Residual

0.052% of content characters (1,437 of 2.74 million) sit in no node, spread
across 881 pages at roughly one line each — mostly hyphenation artefacts and
stray glyphs in table cells. Nothing structural.

Region text (tables, figures) is currently attached to its host node as flat
lines. Stage 4 replaces that with a real cell grid.

## Files

| | |
|---|---|
| `stage3_tree.py` | roles → node tree with stable IDs |
| `checks/check3_continuity.py` | numbering continuity — the Phase 2 gate |
| `checks/check4_capture.py` | every content character lands in exactly one node |
| `out/docgraph.jsonl.gz` | the model |

## Next: Phase 3 — tables

Stage 4 reconstructs the cell lattice from the ruling lines already isolated in
stage 1, assigns text blocks to cells by containment, infers rowspan/colspan from
missing interior segments, and stitches continuations by matching
`Table X (Cont'd)` captions with identical column geometry.

Start with Part 11. Table 11.5.1.1.-F spans nine pages with merged cells and
lettered sub-lists inside single cells — if the lattice reconstruction holds
there, it holds everywhere.

The gate: cell count matches the lattice, no text block unassigned, column count
constant across continuation pages.
