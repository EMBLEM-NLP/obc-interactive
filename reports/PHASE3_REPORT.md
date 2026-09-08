# Phase 3 — tables. Gate: PASS

```
./run.sh /mnt/user-data/uploads/301880.pdf     # ~45s, six checks
```

## Stage 4 — lattice reconstruction  `out/tables.jsonl.gz` (658 KB)

Row and column boundaries are clustered from the ruling lines stage 1 already
isolated. Minimal cells are merged into spans wherever the interior rule that
would separate them is absent. Text lines are assigned to cells by containment
of their centre point.

| | |
|---|---|
| table regions rebuilt | 421 |
| logical tables after stitching | 326 |
| cells | 21,418 |
| merged spans (rowspan or colspan > 1) | 1,412 |
| text lines placed into cells | 33,472 of 33,500 — **99.92%** |

Continuations are stitched by designator, page adjacency and identical column
count. Nothing relies on the word "Cont'd" alone.

## Stage 5 — binding into the graph

Each table becomes a node with a real grid, attached to the provision named in
its own `Forming Part of …` line rather than inferred from position on the page.

- 320 table nodes added
- **299 bound** to the exact provision the caption names
- 21 attached to their Part, where no binding line was found

The document graph is now 18,494 nodes.

## The test case

Table 11.5.1.1.-F — the one in your screenshots — reconstructs as a **single
logical table across all nine pages**, 3 columns, 175 rows, 522 cells:

```
id              B/11/table/11.5.1.1.-F
forming_part_of B/11/11.5.1.1          (an article node, from the caption)
pages           1104 … 1112
row on p1105    ['F16', '3.2.3.', 'Existing need not comply with Article 3.2.3.18. for …']
merged cells    F157 spans 2 rows
```

That row is the one you photographed. The C.A. number, the Division B
requirement and the compliance alternative are now three addressable cells, not
a run of text — which is what makes the references inside them resolvable in
Phase 4 rather than pattern-matched off the page.

## Gate — check 5

| | |
|---|---|
| text lines placed in a cell | 99.92% |
| overlapping cell pairs | **0** |
| captions declared vs tables rebuilt | 303 / 307, **0 declared but not rebuilt** |
| **RESULT** | **PASS** |

Checks 0–4 all still pass after binding: character coverage clean, 0 numbering
gaps across 4,609 parents, 0.052% text orphaned.

## Informational: 13 designators produce more than one run

Not a defect. `11.2.1.1.-B` has a 4-column table and a separate 2-column block
on the same page — a notes or legend grid sharing the caption. Different column
counts are genuinely different tables, so the stitcher correctly refuses to merge
them. They are emitted as sibling nodes with a `#n` suffix.

## What is still flat

The 21 unbound tables need their `Forming Part of` line read from a continuation
page rather than the first. Cell text is currently a joined string; typed inline
spans (defined terms, references) arrive in Phase 4 with the citation grammar,
which is where they belong — one grammar, applied to body text and cell text
alike.

## Files

| | |
|---|---|
| `stage4_tables.py` | table regions → cell lattice with spans |
| `stage5_bind.py` | tables → graph nodes bound to their provision |
| `checks/check5_tables.py` | placement, overlap, column consistency, two-way captions |
| `out/tables.jsonl.gz` | reconstructed grids |
| `out/docgraph.jsonl.gz` | 18,494 nodes including tables |

## Next: Phase 4 — figures, then the citation grammar

Stage 6 exports figure assets: raster by xref at native resolution, vector by
clipping the region to SVG plus a 300 dpi PNG. `pdfimages` alone misses the
vector figures entirely — most of Part 4 is vector.

Then stage 7, the citation grammar and resolver, which is the stage that ends the
leaking. It runs over node text and cell text through the same code path, so
`Table 11.2.1.1.-A of Division B` and `subsection 34(2.3)` — the two families that
escaped the page-by-page patching — are covered by construction rather than by
having been thought of.
