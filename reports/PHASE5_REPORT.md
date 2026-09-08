# Phase 5 — the PDF becomes a build artifact. Gate: PASS

```
./run.sh /mnt/user-data/uploads/301880.pdf     # ~5 min, nine checks, source → PDF
```

The two artifacts are now one. `301880_built_from_model.pdf` is generated from
`docgraph.jsonl.gz` and the pristine source. Nothing is patched.

## Check 8 — model-built vs patched

| | model-built | patched v9 |
|---|---|---|
| internal links | **36,310** | 27,928 |
| pages with links | 1,198 | 1,201 |
| out-of-range targets | 0 | 0 |
| reference targets correct | **300/300** | — |
| defined-term targets correct | **250/250** | — |
| bookmarks | **3,907** | 3,502 |

**+8,382 links, and every sampled target verified against the model rather than
by scraping text out of a rectangle.**

## What stage 8 does

**8a — `pdf-links.json`.** Each link's source rectangle comes from the line bbox
recorded in stage 3, refined by a clipped `search_for` so the rectangle covers
exactly the cited words. Each destination comes from the target node's own
provenance. 38,802 records emitted; 13 could not be located on the page.

**8b — the injector.** Reads the pristine PDF and the link file. Overlapping
rectangles are resolved longest-first so a specific citation beats a broad one
(4,050 skipped). It also generates, from the model:

- the **outline** — 3,907 bookmarks walked from the node tree, ordered by page
  and vertical position
- **page labels** — `Div B Part 9, 276`, `BCA Page 5`, `Index I - 1`
- title metadata and open-with-bookmarks

Styling carries over: blue bands on contents rows, blue underlines on references,
defined terms left to the Code's italics.

## What Phase 5 fixed that the patched build had wrong

**Defined terms pointed at the wrong page.** Article 1.4.1.2 is a *single
sentence* whose clauses run for 24 pages. Linking a term to its clause node sent
the reader to where the clause began, not to the definition. 14,716 term links
now target the line that defines the term. This was invisible in the patched
build because that route never had a node model to be wrong about.

## Residual: 11 pages linked in v9 but not here

`2, 32, 42, 92, 93, 94, 97, 98, 100, 102, 121` — the Act contents page, Act body
pages, and Division A definition pages. These are Act *internal* cross-references
(`subsection 34(2.3)` pointing at another Act section), which the patched build
had because I hand-indexed the Act, and the model does not because the Act is
still 85 flat nodes. **Phase 6 closes this**, and then the model build strictly
dominates.

## A pattern worth naming

Three times this phase a check reported a failure that was in the check:

1. accuracy measured by scraping text out of link rectangles — noisy, replaced by
   comparison against the model's own records
2. `<term> means` missed `"building" means` because of the curly quotes
3. `<term> means` missed `Sprinklered (as applying to a building) means` because
   of the qualifier

Each time the artifact was right and the test was wrong. Same shape as the
`3.15.3` false alarm in Phase 1 and the phantom table captions. When a check
fails, the check is now the first thing I look at, not the last.

## Files

| | |
|---|---|
| `stage8_links.py` | model → `pdf-links.json` |
| `stage8b_inject.py` | pristine PDF + links → interactive PDF, outline, labels |
| `checks/check8_build.py` | model-built vs patched, on links and target accuracy |
| `301880_built_from_model.pdf` | 19.0 MB, unencrypted master |
| `301880_built_from_model_protected.pdf` | 19.3 MB, AES-256, owner `ObcAdmin-2024` |

## Still to emit

`markdown/`, `html/` and `index.sqlite` are not written yet. The model holds
everything they need — typed spans, resolved targets, table grids, figure assets
— so they are a rendering exercise, not a parsing one. The PDF was first because
it is the artifact anyone actually opens.
