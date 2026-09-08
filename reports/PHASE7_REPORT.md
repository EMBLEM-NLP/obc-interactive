# Phase 7 — the Index, and amendment markers made visible. Gates: PASS

## The Index is structured

7,088 flat lines are now **1,464 entries and 5,076 subentries**. Exactly one line
remains unattached.

The Index is set at three indents per column — term, subterm, wrapped
continuation — at roughly 10.8pt steps, and the column geometry alternates
between facing pages. Levels are derived per page from the column starts rather
than from fixed x values, which is the lesson the amendment markers taught.

**10,593 citations now sit inside a named entry**, 10,534 of them resolved
(99.4%). Before this the Index was one node holding a tenth of the document's
citations with nothing to hang them on. You can now ask which provisions the
Index files under *Backflow preventers* and get an answer from the model.

### One informational finding

110 adjacent entry pairs differ from strict A–Z collation. I checked p1198
against the page: the parse follows the printed order exactly. The differences
are the Index's own collation — word-by-word ordering, hyphen and space
handling — not a parsing error. The check reports it and does not fail on it,
because it would be testing the source rather than the pipeline.

## Amendment markers are now reachable

Modelling them was not enough — a reader still saw a bare `r2` in the margin with
no way to find out what it meant. **149 marker links** now go to the legend on
page 6, each tinted so it reads as clickable:

```
r1  →  O. Reg. 447/24, in force 1 January 2025
r2  →  O. Reg. 5/25,   in force 16 January 2025
e1  →  editorial correction, 1 January 2025
e2  →  editorial correction, 16 January 2025
```

## Graph and build

| | |
|---|---|
| nodes | **25,721** (was 19,181) |
| internal links | **36,009** |
| web / mail links | 445 |
| dead `Launch` links | 0 |
| bookmarks | 3,907 |
| deliverable | 19.3 MB, AES-256, owner `ObcAdmin-2024` |

## Gate suite — all nine PASS

| check | |
|---|---|
| 0 character coverage | PASS |
| 1 table / figure regions | PASS |
| 3 numbering continuity | PASS |
| 4 text capture | PASS — 0.083% |
| 5 table integrity | PASS |
| 7 reference resolution | PASS |
| 8 model build vs patched | PASS — 0 pages lost |
| 9 amendment markers | PASS — 149/149 |
| 10 index structure | PASS |

## Volume 2

Direct download, confirmed from the Publications Ontario product page:

**https://www.publications.gov.on.ca/store/20170501121/Free_Download_Files/301881.pdf**

Publication #301881, free, non-commercial use. Volume 1 is the same path with
`301880.pdf` — the file this pipeline was built against.

Volume 2 runs through stages 0–9 unchanged. Merging the graphs closes the 1,054
references that currently resolve to nothing: 898 `Note A-x` into Appendix A,
140 Supplementary Standards, 2 Forms, and page 8's contents listing. It is also
the first real test of whether any of the thresholds generalise, since every one
of them was calibrated on Volume 1 alone.

## Remaining

- 21 tables unbound (their `Forming Part of` line sits on a continuation page)
- 182 standards cited but absent from Table 1.3.1.2.
- table header rows not identified
- `markdown/`, `html/`, `index.sqlite` still unwritten — a rendering exercise now,
  not a parsing one
