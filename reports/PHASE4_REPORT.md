# Phase 4 — figures and the citation grammar. Gates: PASS

```
./run.sh /mnt/user-data/uploads/301880.pdf     # ~60s, eight checks
```

## Stage 6 — figures  `out/figures.jsonl.gz`, `out/assets/` (2.5 MB)

55 figure regions exported. **All 55 are raster** — there are no vector figures
in this volume. The vector path (crop a one-page copy, export SVG plus a 300 dpi
PNG) is implemented and correct but never fires here; it will matter for
Volume 2.

**Check 6 — two-way: PASS.** 22 declared Figure captions, 22 exported captioned
assets, **zero** in either direction. The other 33 assets are letterhead,
signatures and Preface artwork, correctly carrying no designator. No zero-byte
files.

I had assumed most of Part 4 was vector, based on p.494 having 335 drawing
primitives. Those primitives are the lattice of Table 4.1.7.6. The figures on
pp. 495–496 are images. The assumption was wrong and the two-way check is what
made that visible.

## Stage 7 — one grammar, one resolver

Indexes built from the graph itself, not from page scans: 3,499 clauses,
307 tables, 85 Act sections, 390 defined terms, 1,242 standard designations —
the last read out of the reconstructed Table 1.3.1.2. grid, which only became
possible after Phase 3.

The grammar covers `code_ref`, `cap_ref`, `act_ref`, `short`, `note`, `supp`,
`form`, `ca`, `std`, plus division qualifiers, and runs over **node text and
table-cell text through the same code path**.

## Check 7 — the gate: PASS

| | |
|---|---|
| citations found | 24,825 |
| **resolved to a node** | **23,305 (93.9%)** |
| external — Volume 2 (Notes, Supplementary Standards, Forms) | 1,054 |
| source — not in Table 1.3.1.2. | 182 |
| source — clause not in this edition | 172 |
| source — figure / compliance-alternative row | 112 |
| **parse failures** | **0** |
| defined-term links | 12,249 |

Spot check: 200 sampled targets, **200/200** carry a number consistent with the
citation.

Every remaining unresolved citation is a fact about the source, not a bug. That
is the whole point of reason codes.

## The two families that escaped the page-by-page work

Both are now covered by construction:

```
subsection 34(2.3)                      -> ACT/34          (act_ref)
Table 11.2.1.1.-A of Division B         -> B/11/table/…    (cap_ref + division qualifier)
```

And inside the compliance-alternatives table you photographed:

```
B/11/table/11.5.1.1.-F   '3.1.4.7.' -> B/3/3.1.4.7
                         '3.1.5.2.' -> B/3/3.1.5.2
B/9/9.10.16.1/(1)  terms 'fire blocks'         -> A/1/1.4.1.2/(1)/(h)
                         'attic or roof spaces'-> A/1/1.4.1.2/(1)/(c)
```

Cell text and provision text go through identical code. There is no separate
"tables pass" to forget.

## Four defects the gate caught

**1. `\b` was missing from the Act pattern.** Without it, `section` matched
*inside* `Subsection 3.2.6.`, turning **502** Code citations into phantom Act
references that then failed to resolve. One word boundary; 500 citations.

**2. Matching per line lost cross-line context.** `section 53 of the Ontario
Water Res…` breaks at the line end, so the "of the … Act" test never saw the
word "Act" and could not exclude the reference. Fixed by joining a node's lines
before matching.

**3. Grammar precedence was wrong.** `Subsection 3.2.6. of Division B` was being
taken as an Act reference. A Code citation always ends the number with a period;
an Act citation never does. Ordering `code_ref` before `act_ref` separates them
cleanly.

**4. Standard designations parsed as clause numbers.** `A112.19.8-2007` yielded
a phantom clause `112.19.` — rejected now when the number is preceded by a
letter. Compound organisation prefixes (`ANSI/ASHRAE`, `CAN/ULC-S114`) also
needed handling, and designators are matched with punctuation normalised, which
absorbs source typos like `Table 9.26.2.1-.B`. Standards resolution went from
635 to 1,639.

## Files

| | |
|---|---|
| `stage6_figures.py` | figure regions → raster/vector assets, caption-bound |
| `stage7_refs.py` | the grammar and resolver |
| `checks/check6_figures.py` | two-way figure caption ↔ asset |
| `checks/check7_refs.py` | resolution rate by reason code — the gate |
| `out/docgraph.jsonl.gz` | 18,494 nodes with `refs` and `terms` |

## Next: Phase 5 — emitters

Everything needed is now in the model. Stage 8 writes:

- `markdown/` — a file per Part, references as links to node IDs, tables as HTML
  where Markdown cannot express spans
- `html/` — full fidelity with figures inline
- `index.sqlite` — nodes, refs, terms, FTS5
- `pdf-links.json` — `{node id → page, bbox}` plus resolved targets

That last file is what rebuilds the interactive PDF **from the model** rather
than by patching. 23,305 resolved citations and 12,249 term links, each with
provenance, regenerated in one pass — and a grammar fix propagates to every
output at once instead of needing another sweep.
