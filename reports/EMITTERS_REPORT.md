# G16 — emitters built. Volume 1 ledger: ALL MET (16 met).

```
GATES.md            ALL MET (16 met)
vol2/GATES.md       ALL MET (7 met)
emitters/GATES.md   HANDOFF REQUIRED: 1 abandoned (met: 3)
```

The last one is deliberate and is explained below.

## What was built

| emitter | output | size |
|---|---|---|
| SQLite + FTS5 | `obc.sqlite` — 27,421 nodes, 139,967 closure rows, 29,952 refs, 16,075 term links, 144 amendments, 21,313 table cells | 62 MB |
| Markdown | 38 files, one per Part / Act / Appendix / Standard | 6.5 MB |
| HTML | 39 files including an index | 8.7 MB |

## Design decisions taken from the research, and why

**One identity layer, imported by all three** (`emit_common.py`). The review's
first recommendation was that a stable permalink, a currency stamp and the
licence are expensive to retrofit. So they are defined once:

```
B/9/9.10.16.1/(2)/(a)  ->  B/9/9.10.16.1/s2/c-a
ACT/15.4.2/(1)         ->  ACT/15.4.2/s1
```

27,421 unique permalinks, zero collisions, zero non-URL-safe characters. The
designator is preserved rather than positional, so the 41 letter-suffixed
insertions (`A/1/1.3.3.1A`, `7.6.2.5A`) address cleanly without renumbering
siblings — the legislation.gov.uk stability property. Every output carries
`current to 2025-01-16 (through O. Reg. 5/25)`.

**SQLite: external-content FTS5 plus a trigram index.** The review flagged that
`unicode61` fragments clause numbers. Both indexes are built, and the gate proves
the difference matters:

```
FTS  'fire AND separation'   3 ranked hits with bm25 + highlighted snippet
trigram '9.10.16.1'          21 rows      <- unicode61 cannot do this
trigram 'SB-3'               25 rows
```

**Closure table, not recursive CTEs**, as recommended for a read-heavy
near-static corpus: 139,967 rows makes "all 5,558 descendants of Part 9" an
indexed join.

The three queries the model was built for all run:

```
citations of B/3/3.1.4.7                26
provisions changed by O. Reg. 5/25       6   B/9/9.9.4.4/(1), C/1/1.7.1.1/(1), …
defined terms in B/9/9.10.16.1/(1)       fire blocks, attic or roof spaces
dangling foreign keys                    0
```

**Markdown: designators as literal text, never list markers.** The review warned
that Markdown auto-numbering silently renumbers provisions across renderers. The
check counts lines a renderer could renumber: **0**. Complex tables drop to HTML
blocks — 320 of them — because GFM cannot express rowspan/colspan.

**HTML: built to WCAG 2.2 AA**, since AODA (O. Reg. 191/11 s.14) mandates 2.0 AA
for Ontario government content and 2.2 is a superset. Mechanically verified
across all 39 files: `lang`, `<title>`, skip link, `<main>`/`<nav>` landmarks,
non-skipping heading order, a `<caption>` on every table, `id`/`headers` on every
merged-cell table, and no bare "click here". **0 failures.**

## The gate caught two emitter defects and one more check defect

**`v2_SB-10.html` skipped from `h3` to `h5`.** I had mapped heading level from
node *type*, and a Supplementary Standard puts an article directly under a
section with no subsection between. Fixed by deriving the level from tree
position instead of a static map — which is the general fix, not a patch for
SB-10.

**Part files opened with the entire contents page dumped as a wall of text**,
because `contents` nodes fell through to a generic "print the body" branch. They
are navigation; the emitters generate their own ToC, so they are skipped.

**And check 17 tested for the literal string `King's Printer`** in HTML that
correctly escapes the apostrophe to `&#x27;`. The page was right; the test was
comparing against unescaped text. **Ninth time.**

## E4 is abandoned, not met — and that is the honest outcome

```
ABANDON: E4 No screen reader, contrast analyser or human reviewer is available
in this environment.
```

The mechanical WCAG structure checks pass, but **conformance cannot be claimed
from them**. Contrast ratios, focus order, alt-text quality and how a screen
reader actually reads a merged-cell table are not decidable by command. unlazy
treats an abandoned gate as a required handoff, not a pass, so the emitters
ledger reports `HANDOFF REQUIRED` rather than green.

**Handoff:** run axe or WAVE plus an NVDA/VoiceOver pass over `out/html`,
concentrating on the merged-cell tables in Part 11 and Appendix A, and supply
long descriptions for the figure assets before publication. Figures are exported
but not yet embedded with two-part text alternatives.

## Licensing — the binding constraint

The research confirmed this is a publication constraint, not a technical one, so
it is carried in every artefact: front matter in all 38 Markdown files, the
footer of all 39 HTML files, and the `meta` table in SQLite.

> Permitted for personal use and non-commercial reproduction and distribution
> only, **and only where this product is made available to the public free of
> charge**. Any use that is not free to the public is treated by the Ministry as
> commercial use and requires a licence: buildingtransformation@ontario.ca

Plus, on every page: the unofficial-version notice, © King's Printer for Ontario
2024, and the NRC licence acknowledgement.

## Deliverables

| | |
|---|---|
| `obc.sqlite` | the queryable model |
| `markdown.tar.gz` | 38 files, doubles as the RAG source |
| `html.tar.gz` | 39 files, WCAG 2.2 AA structure |
| `sample_v1_B_9.html` / `.md` | Part 9 alone, to inspect without unpacking |
| `emit_common.py`, `stage15/16/17` | the emitters |
| `checks/check16-18` | the gates |

## Still open

- **E4** — manual accessibility review (handoff above)
- Figure assets are exported but not embedded in HTML with long descriptions
- Akoma Ntoso export — deliberately deferred per the review; the JSON graph stays
  canonical and AKN can be generated from it if interoperability is ever needed
- Volume 2 has no page labels, and its tables are not reconstructed (stages 4–5
  were never run on it), so Volume 2 tables appear as text rather than grids
- 21 Volume 1 tables unbound; 182 standards absent from Table 1.3.1.2.
