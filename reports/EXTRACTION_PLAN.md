# Building an accurate processing model for the Building Code Compendium

## Why the current approach keeps leaking

Everything so far has been **pattern-matching on rendered output, page by page**.
Each new citation form has to be *discovered* before it can be matched, so the
audit can only ever confirm "no misses among the patterns I thought of." Three
families were found after the audit reported zero gaps:

| Family | Count | Cause |
|---|---|---|
| `subsection 34(2.3)` — number and parenthetical in one token | 241 | Act matcher required a bare `34` token |
| `Table 11.2.1.1.-A of Division B` cited from a Division A page | 394 | "of Division X" override was wired into the clause path, not the caption path |
| `s. 224`, `ss. 15.1` short-form statute cites | 609 | never matched; most point at *amending* statutes, not this document |
| `(1.2)`, `(4.1)` bare subsection cites | 128 | indistinguishable from subsection markers without a parse tree |

The fix is not more patterns. It is to **parse once into a document model, resolve
references once against that model, and generate every output from it** — including
the linked PDF. Then "did I think of this pattern?" becomes "does the citation
grammar cover this form?", which is a testable question with a finite answer.

---

## Recommendation: do not make Markdown the source of truth

Markdown is the right *output*. It is the wrong *model* for this document:

- **Tables carry normative text.** Table 11.5.1.1.-F runs 20+ pages with merged
  cells and lettered sub-lists inside single cells. Markdown tables cannot express
  rowspan, colspan, or block content in a cell.
- **Italic is semantic, not stylistic.** In this Code italic means *defined term*.
  Markdown `*x*` conflates that with ordinary emphasis, so the definition links
  cannot be regenerated from the Markdown.
- **Identifiers collide.** `1.1.1.1.` exists in Divisions A, B and C. Markdown
  headings give no stable, namespaced anchor.
- **Provenance is required.** To re-inject links into the PDF you need page and
  bounding box for every span. Markdown discards both.
- **Metadata is not prose.** Amendment symbols, effective dates, the French
  equivalents in the Act, "Forming Part of…" bindings, and Reserved/Repealed
  status all need fields, not asterisks.

### Ranked options

| # | Model | Fit | Cost | When to choose |
|---|---|---|---|---|
| 1 | **JSON document graph** + generated MD/HTML + SQLite index | Best | Medium | Recommended. Full fidelity, diffable, drives PDF link injection |
| 2 | Akoma Ntoso / LegalDocML XML | Very good | High | If this will be published or exchanged with other jurisdictions |
| 3 | Markdown + sidecar JSON for tables, spans, provenance | Adequate | Low | If the only consumer is an LLM or full-text search |
| 4 | SQLite only | Poor for review | Low | Good as a derived index, bad as source of truth |

**Choose option 1.** Emit Markdown *from* it — you get the Markdown you asked for
without paying its losses.

---

## Target schema

One node per provision. Stable, namespaced IDs.

```jsonc
{
  "id": "B/9/9.10/9.10.16/9.10.16.1/(2)/(a)",   // division/part/section/subsection/article/sentence/clause
  "type": "clause",            // division|part|section|subsection|article|sentence|clause|table|figure|note|form
  "number": "(a)",
  "heading": null,
  "text": "the exposing building face …",
  "spans": [                   // typed inline runs — this is what italics become
    {"role": "defined-term", "text": "building", "target": "A/1/1.4/1.4.1/1.4.1.2/building"},
    {"role": "reference",    "text": "Table 9.10.14.4.-A", "target": "B/9/table/9.10.14.4.-A"},
    {"role": "emphasis",     "text": "et seq."}
  ],
  "refs": ["B/9/table/9.10.14.4.-A"],           // resolved, deduplicated
  "status": null,                               // reserved | repealed | amended
  "amendment": {"symbol": "e1", "effective": "2025-01-01"},
  "provenance": [{"page": 794, "bbox": [36, 593.5, 278, 606.2]}]
}
```

Tables get a real grid, not a rendering:

```jsonc
{
  "id": "B/11/table/11.5.1.1.-F",
  "type": "table",
  "caption": "Compliance Alternatives for Industrial Occupancies",
  "forming_part_of": "B/11/11.5/11.5.1/11.5.1.1",
  "continues_across": [1104, 1105, 1106, 1107, 1108, 1109, 1110, 1111, 1112],
  "header_rows": 1,
  "grid": [[{"row": 0, "col": 0, "rowspan": 1, "colspan": 1, "blocks": [...]}]]
}
```

---

## Pipeline

### Stage 0 — Page inventory
PyMuPDF `get_text("rawdict")` for glyph-level text with font, size, colour, bbox;
`get_drawings()` for ruling lines and fills; `get_images()` and `get_links()`.
Emit one JSONL record per page. **Nothing is interpreted yet.**

Verify: every glyph in the PDF appears exactly once in the inventory.

### Stage 1 — Geometric page classification
Derive, from geometry alone, never from footer strings — that assumption is what
hid the Building Code Act for the whole first pass:

- header/footer bands (y < 45, y > 735)
- column count and gutter x-positions (cluster text-block x0)
- table regions (from ruling-line density in `get_drawings()`)
- figure regions (image xrefs + dense vector clusters)
- body region = remainder

Verify: classified area accounts for 100% of text blocks on every page.

### Stage 2 — Font signature → structural role
Build the map empirically rather than assuming it:

| Signature | Role |
|---|---|
| Arial-Black 13 | Section heading |
| Arial-Black 11 | Article heading |
| Arial-Black 10, left gutter | Subsection heading / Act marginal note |
| TimesNewRomanPS-Bold, line-initial `N(1)` | Act section start |
| TimesNewRomanPS-Italic inline | defined term |
| ArialNarrow inside a table region | table body |

Verify: every heading in the printed contents pages resolves to exactly one
detected heading, and vice versa. This is a two-way check the current tooling
never had.

### Stage 3 — Tree assembly
Walk pages in order, push/pop by structural role, attach body text to the open
node. Sentence `(1)`, clause `(a)`, subclause `(i)` come from line-initial
markers plus indent x-position.

Verify: numbering continuity — no gaps within a parent unless the node is marked
Reserved or Repealed. This catches both parse errors and genuine source gaps
(it is how you would have found that Section 5.10 does not exist while the Index
cites `5.10.1.1.` 42 times).

### Stage 4 — Tables
Reconstruct the grid from ruling lines: cluster horizontal and vertical segments,
build the cell lattice, assign text blocks to cells by containment, infer
rowspan/colspan from missing interior segments. Stitch continuations by matching
`Table X (Cont'd)` captions and identical column geometry.

Verify: cell count matches the lattice; no text block unassigned; column count
constant across continuation pages.

### Stage 5 — Figures
- Raster: extract by xref at native resolution.
- Vector: clip the figure region and export as SVG (`page.get_svg_image(clip=…)`),
  plus a PNG at 300 dpi for previews. `pdfimages` alone misses these entirely —
  most figures in Part 4 are vector.
- Bind each asset to its caption node and `Forming Part of` target.

Verify: every `Figure X` caption has an asset; every asset has a caption.

### Stage 6 — Citation grammar
**One grammar, one resolver.** This is the stage that ends the leaks.

```
code_ref     := ("Article"|"Subsection"|"Section"|"Sentence"|"Clause")? number
                (division_qualifier)?
number       := digit+ ("." digit+){1,4} "."? ("(" digit+ ")")? ("(" alpha ")")?
table_ref    := ("Table"|"Figure") number ("-" [A-Z0-9/]+)?
act_ref      := ("section"|"subsection"|"clause") digit+ ("." digit+)?
                ("(" digit+ ("." digit+)? ")")* ("(" alpha ")")?
short_cite   := ("s."|"ss.") digit+ …          -- resolve ONLY when the enclosing
                                                  sentence names this Act
range        := ref ("to"|"through") ref        -- expand to endpoints
series       := ref (("," | ";" | "and") ref)+  -- link each member
std_ref      := org designation                 -- prefix match into Table 1.3.1.2.
note_ref     := "A-" number                     -- external: Volume 2
supp_ref     := ("SA"|"SB"|"SC") "-" digit+     -- external: Volume 2
form_ref     := "Form" number "-" [A-Z]         -- external: Volume 2
ca_ref       := "C.A." [A-F] digit+
term_ref     := italic run matching the definitions index
```

Resolution rules, applied in order:
1. Explicit `of Division X` qualifier wins — **for every reference type**, not
   just clauses. That omission caused the 394 table misses.
2. Otherwise the enclosing node's own division.
3. Otherwise the unique exact match across divisions.
4. Otherwise truncate to the nearest existing ancestor and mark
   `resolution: "ancestor"`.
5. Otherwise mark `resolution: "unresolved"` with a reason code.

Every reference carries its reason code. The output is a resolution report, not
a silent best guess.

Verify: resolution rate by category, with every unresolved item classified as
`external-volume-2`, `not-in-this-edition`, `other-statute`, or `parse-failure`.
Only the last is a defect.

### Stage 7 — Emitters
- `markdown/` — one file per Part, defined terms as `[building](#A/1/1.4.1.2/building)`,
  tables as HTML blocks where Markdown cannot express them
- `html/` — full fidelity, one page per Part, figures inline
- `docgraph.json` / `.jsonl` — the model
- `index.sqlite` — nodes, refs, terms, full-text search
- `pdf-links.json` — `{node_id → [page, bbox]}` plus resolved targets, consumed by
  a thin injector that rebuilds the interactive PDF from scratch each run

The PDF becomes a *build artifact*, not something patched in place. Every link is
regenerated from the model, so a grammar fix propagates everywhere at once.

### Stage 8 — Validation harness
Run on every build, fail the build on regression:

1. **Character coverage** — concatenated node text vs `pdftotext -layout` per page,
   normalised. Target 100%; anything below means text was dropped.
2. **Structure round-trip** — printed contents pages vs detected headings, both directions.
3. **Numbering continuity** — per parent, gaps only where Reserved/Repealed.
4. **Reference resolution** — rate by category; `parse-failure` must be zero.
5. **Table integrity** — cell/lattice match, constant column count across continuations.
6. **Asset binding** — captions ↔ figures, 1:1.
7. **Link injection** — every emitted PDF link target in range and landing on a page
   whose text contains the cited identifier.

---

## Tooling

| Job | Tool | Note |
|---|---|---|
| Glyphs, fonts, bboxes, drawings, links, SVG export | **PyMuPDF** | Primary. Already proven on this file |
| Ruling-line cross-check | pdfplumber | Second opinion on table lattices |
| Raster extraction | PyMuPDF xref / `pdfimages -all` | Native resolution |
| Text ground truth | `pdftotext -layout` | Independent source for coverage diffs |
| Model | Python dataclasses → JSON, `pydantic` for validation | |
| Index | SQLite + FTS5 | |
| Harness | pytest, golden files per Part | |

**On ML-based converters** (Docling, Marker, LlamaParse, vision models): do not
put them in the critical path. They reorder content, silently drop table cells,
and paraphrase. For a normative legal document you need every output traceable to
a glyph. They are useful as a *third* opinion in the harness — flag pages where
their reading order disagrees with the deterministic parse — but never as the
source of truth.

---

## Sequencing

| Phase | Work | Output |
|---|---|---|
| 1 | Stages 0–2 + the two-way heading check | Proof the structure detector is complete before anything is built on it |
| 2 | Stage 3 tree + numbering continuity | `docgraph.json` for Divisions A and C (small, exercises the edge cases) |
| 3 | Stage 4 tables | Part 11 first — it is the hardest, so it de-risks the rest |
| 4 | Stage 5 figures | Part 4 first — heaviest vector content |
| 5 | Stage 6 grammar + resolver | Resolution report replaces ad-hoc audits |
| 6 | Stage 7 emitters + Stage 8 harness | Markdown, HTML, SQLite, and a regenerated PDF |
| 7 | Volume 2 ingested through the same pipeline | Closes the 1,146 external references |

Phases 1–2 are where you find out whether the whole approach holds. If the
two-way heading check does not reach 100%, stop and fix the detector rather than
building on it.

## Risks

| Risk | Mitigation |
|---|---|
| Table lattice fails on borderless or shaded tables | pdfplumber cross-check; fall back to x-position clustering; harness flags disagreement |
| Vector figures clip incorrectly | Render both clipped SVG and full-page PNG; visual diff against the source page |
| Grammar over-links (e.g. `s. 224` of an amending statute) | Require an explicit anchor to *this* Act; default to unresolved rather than guessing |
| Model drifts from the PDF after a Code amendment | Pipeline is deterministic and re-runnable; treat the PDF as input, never edit outputs by hand |
| Effort exceeds value | Phases 1–2 are cheap and answer the feasibility question before the expensive stages |

## Interim

Two defects are already isolated and can be patched in the current PDF today,
independent of this plan:

- `subsection 34(2.3)` and 240 like it — Act matcher tokenisation
- `Table 11.2.1.1.-A of Division B` and 393 like it — division qualifier missing
  from the caption resolution path

They are worth doing if you need the current file in service, but they are exactly
the kind of one-off patch this plan exists to stop needing.
