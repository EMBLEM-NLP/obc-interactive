# Roadmap and gap register

## Where things stand

Two separate artifacts exist, and they are **not** derived from each other:

| | |
|---|---|
| `301880_interactive_v9_protected.pdf` | 27,928 links. Built by **patching** the PDF page by page. Shipped, works. |
| `pipeline/out/docgraph.jsonl.gz` | 18,494 nodes, 24,825 citations (23,305 resolved), 12,249 term links. Built by **parsing**. Emits nothing yet. |

The whole point of Phase 5 is to collapse those two into one: the PDF becomes a
build artifact of the model. Until that happens, a grammar fix improves the model
and does nothing for the file anyone actually opens.

---

## Roadmap

### Phase 5 — emitters (next)

| stage | output |
|---|---|
| 8a | `pdf-links.json` — `{node id → page, bbox}` + resolved targets |
| 8b | link injector — rebuild the interactive PDF **from the model**, from the pristine source, every run |
| 8c | `markdown/` — one file per Part; references as links to node IDs; tables as HTML blocks where Markdown cannot express spans |
| 8d | `html/` — full fidelity, figures inline |
| 8e | `index.sqlite` — nodes, refs, terms, FTS5 |

**Gate:** the regenerated PDF must match or beat v9 on every measure — link count,
target accuracy, TOC coverage — and be reproducible byte-for-byte from source.
If it does not beat 27,928 links, find out why before switching over.

### Phase 6 — the Act as a real tree

85 `act_section` nodes currently hold **3,896 lines of flat text**. Subsections
`(1)`, clauses `(a)`, and the marginal notes that title each section are not
parsed. Sequence-driven marker parsing from stage 3 applies directly; the Act
just was not run through it.

**Gate:** numbering continuity across Act subsections, same as check 3.

### Phase 7 — the Index as structured entries

One flat node holding **7,088 lines**. Each entry is `term, clause, clause, …`
with `[A]`/`[C]` division markers — highly regular and worth parsing into
`{term, subterm, refs[]}`. This turns the Index into a queryable concept map
and lets the emitters render it as a real index rather than a wall of text.

### Phase 8 — Volume 2

1,054 citations resolve to nothing because their targets are not in this file:
898 `Note A-x`, 140 Supplementary Standards, 2 Forms, plus page 8's contents.
Run Volume 2 through stages 0–7 and merge the graphs. Nothing new needs
inventing — the ID scheme already namespaces by division, so `SB-3` and
`A-3.1.2.` become nodes like any other.

### Phase 9 — hardening

- Golden-file regression tests per Part; every check becomes a pytest case
- Round-trip: emitted Markdown re-parsed must equal the model
- CI on a fresh Code amendment: rerun, diff the graph, review only what changed

---

## Gap register — what is still missed

### Modelled but incomplete

| gap | size | note |
|---|---|---|
| Act internal structure | 3,896 flat lines under 85 sections | Phase 6 |
| Index structure | 7,088 flat lines | Phase 7 |
| Amendment markers `e1`, `r1`, `e2`, `r2` | **153 occurrences, none modelled** | These mark provisions changed by O. Reg. 5/25 and carry effective dates. Legally significant and currently invisible. |
| Act definitions in the term index | 3 sections define terms; only Division A 1.4.1.x is indexed | `"building" means…` is in the Act, not Division A |
| Table header rows | 0 of 320 tables flag them | Needed for correct HTML and for reading a cell in context |
| Tables unbound to a provision | 21 of 320 | Their `Forming Part of` line sits on a continuation page |
| Notes-to-table blocks | not linked to their parent table | The 13 "designator split" cases |
| Standards not in Table 1.3.1.2. | 182 citations | May be genuine source gaps; unverified |
| Clauses not in this edition | 172 citations | Includes `5.10.1.1.`, cited 42 times, confirmed absent |
| Orphaned characters | 1,437 (0.052%) | Hyphenation artefacts, stray table glyphs |

### Not yet examined at all

- **Vector figure path is untested.** Implemented, but this volume has zero vector
  figures, so the code has never run. It will run first on Volume 2.
- **Act reading order is ungated.** The Act is two-column; 85 sections were found
  and that matched an independent count, but no check confirms the *text* reads in
  the right order within a section.
- **Figure region ↔ asset correctness is positional.** Check 6 confirms every
  caption has an asset and every asset a caption. It does not confirm the exported
  image is the region that caption describes.
- **Table cell reading order within a cell.** Lines are joined in y-order; a cell
  containing a two-column sub-list would join wrongly. Not observed, not tested.
- **No French text handling.** The Act's bilingual equivalents did not appear in
  this scan, but the front matter is bilingual and the emitters have no policy.

### Process gaps

- Every check is a script run by hand. There is no single pass/fail, no history,
  and nothing stops a regression.
- The pipeline has never been run against a *different* PDF. Every threshold —
  header band, gutter width, lattice tolerances — is calibrated on one document.
  Volume 2 is the first real test of whether any of it generalises.

---

## The honest summary

The parsing side is in good shape and, more importantly, it now tells you when it
is wrong: eight checks, seven of them two-way, and every unresolved citation
carries a reason code instead of vanishing.

What has **not** happened is the part that matters to a user opening the file. The
shipped PDF is still the patched one. Every defect the pipeline found — the 502
phantom Act references, `7.6.2.5A.`, the letter-suffixed articles — is fixed in
the model and **not** in the document anyone reads.

Phase 5 is not the next nice-to-have. It is the step that makes the previous four
phases count.
