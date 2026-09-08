# 2024 Building Code Compendium — interactive edition and document model

*Every count in this file is measured from the artifacts at package time by
`gen_readme.py`, not typed. `FACTS.json` holds the same numbers as data.*

**Unofficial.** Current to **16 January 2025** (through **O. Reg. 5/25**).
Not the official Compendium. Consult the official edition published by
Publications Ontario for authoritative text.

Built from the pristine source PDFs (Publications Ontario #301880 and #301881)
by the deterministic pipeline in `pipeline/`. Every artefact here is generated
from one document model; nothing was hand-patched.

---

## Completion status — read this first

| ledger | result |
|---|---|
| `gates/GATES-volume1.md` | **ALL MET (16 of 16)** |
| `gates/GATES-volume2.md` | **ALL MET (7 of 7)** |
| `gates/GATES-emitters.md` | **HANDOFF REQUIRED — 1 abandoned (4 of 5 met)** |

**This package is not "complete" without qualification.** Gate **E4** is
abandoned, not met:

> Manual WCAG review — contrast, focus order, alt-text quality, and how a screen
> reader actually reads a merged-cell table — cannot be decided by a command, and
> no screen reader, contrast analyser or human reviewer was available.

The mechanical WCAG 2.2 AA structure checks pass across all 39 HTML files.
Conformance **cannot be claimed** from that alone.

**Required before publishing the HTML:** run axe or WAVE plus an NVDA/VoiceOver
pass over `emitters/html.tar.gz`, concentrating on the merged-cell tables in
Part 11 and Appendix A, and supply long descriptions for figure assets.

---

## Contents

### `pdf/` — the interactive documents

| file | pages | internal | cross-volume | web | dead | bookmarks |
|---|---|---|---|---|---|---|
| `301880_built_from_model_protected.pdf` | 1,260 | 35,932 | 993 | 445 | 0 | 3,928 |
| `301881_built_from_model_protected.pdf` | 1,001 | 0 | 4,382 | 71 | 0 | 927 |

AES-256, owner password `ObcAdmin-2024`, opening freely with the ministry's
original permission set (print yes, copy yes, change no).
`*_built_from_model.pdf` are the unencrypted masters for further work.

**Keep both files in the same folder** — the cross-volume links reference each
other by filename. `See Note A-3.1.2.` in Volume 1 opens Volume 2 at that note.

Volume 2 having no *internal* links is correct: Appendix A is explanatory
material for Division B, so nearly everything it cites lives in Volume 1.

### `emitters/` — the derived formats

| | |
|---|---|
| `obc.sqlite` | 27,421 nodes, 139,967 closure rows, 29,952 citations, 16,075 defined-term links, 144 amendment rows, 21,313 table cells. FTS5 + trigram. |
| `markdown.tar.gz` | 38 files, one per Part / Act / Appendix / Standard. Doubles as the RAG source. |
| `html.tar.gz` | 39 files, WCAG 2.2 AA structure, print CSS. |

Example queries against `obc.sqlite`:

```sql
-- what cites this article
SELECT src FROM ref WHERE dst = 'B/3/3.1.4.7';

-- what did O. Reg. 5/25 change
SELECT n.id, n.designator FROM amendment a
  JOIN node n ON n.id = a.node WHERE a.instrument = '5/25';

-- ranked full-text search with a highlighted snippet
SELECT n.id, snippet(node_fts, 2, '[', ']', '…', 8)
  FROM node_fts JOIN node n ON n.rowid = node_fts.rowid
  WHERE node_fts MATCH 'fire AND separation' ORDER BY bm25(node_fts) LIMIT 10;

-- clause-number search (unicode61 fragments these; the trigram index does not)
SELECT id FROM node_tri WHERE node_tri MATCH '"9.10.16.1"';

-- a whole subtree, no recursive CTE
SELECT descendant FROM closure WHERE ancestor = 'B/9';
```

### `model/` — the document graph

`docgraph-merged.jsonl.gz` is canonical; every other artefact is a function of
it. One JSON object per line. Node ids are namespaced and stable:

```
B/9/9.10.16.1/(2)/(a)   Division B, Part 9, Article 9.10.16.1, Sentence (2), Clause (a)
ACT/15.4.2/(1)          Building Code Act
APPA/A-3.1.2.           Appendix A explanatory note
SB-3/2.1.               MMAH Supplementary Standard
```

Each node carries parent, children, text with page+bbox provenance, resolved
citations with reason codes, defined-term links, amendment metadata, and (for
tables) a real cell grid with rowspan/colspan.

### `pipeline/` — how it was built

```
./run.sh /path/to/301880.pdf        # stages 0-9 plus the checks, ~5 min
```

Stages 0–2 inventory and classify pages by geometry; 3 assembles the tree;
4–5 rebuild tables; 6 exports figures; 7 resolves citations through one grammar;
8 emits and injects links; 9 models amendment markers. `vol2/` adds the second
container model, the merge and the cross-volume resolver. `emitters/` produces
SQLite, Markdown and HTML.

### `verify/` — re-verify every gate from what is shipped

```
GATE_CHECK=/path/to/unlazy/scripts/gate-check.mjs \
  ./verify/verify.sh /path/to/301880.pdf /path/to/301881.pdf
```

Each ledger sits with its own checks and its own working set — inventories,
geometry, roles, the document graph, the built PDFs, the database. No absolute
paths, no dependency on the machine that built it. The only inputs you supply
are the two source PDFs, which are not redistributed here.

`baseline/v9-baseline.json` holds the frozen measurements of the superseded
hand-patched build. `check8` asserts the model build is a strict superset of
those numbers, so the regression baseline is data you can read rather than a
19 MB PDF fixture.

**Amendment counts, reconciled** — 153 markers appear on the page; 4 are the
legend on page 6; **149** attach to a provision; the model stores **144** rows,
because 19 repeat attachments of the same marker to the same node collapse
(Table 1.3.1.2. spans 30 pages and carries `r1` eight times) and 14 rows are
inherited by parent provisions.

### `gates/` and `reports/`

The acceptance ledgers and the phase-by-phase record, including what was found
wrong and when.

---

## What is still open

| | |
|---|---|
| **E4** | manual accessibility review - abandoned, see the handoff above |
| Figures | exported but not embedded in HTML with long descriptions |
| Volume 2 tables | stages 4-5 never run on Volume 2, so its tables are text, not grids |
| Volume 2 page labels | not generated |
| 60 notes | cited in Volume 1 with no Appendix A entry |
| 363 standards | cited but absent from Table 1.3.1.2. |
| 629 references | cite a provision this edition does not contain |
| 21 tables | unbound to a provision (their `Forming Part of` line is on a continuation page) |
| Akoma Ntoso | deliberately deferred; the JSON graph is canonical |

---

## Licence and attribution

© King's Printer for Ontario, 2024. Reproduced with permission.
Contains material copyrighted by the National Research Council of Canada,
reproduced under a licence agreement.

**Permitted for personal use and non-commercial reproduction and distribution
only, and only where this product is made available to the public free of
charge.** Any use that is not free to the public is treated by the Ministry of
Municipal Affairs and Housing as commercial use and requires a licence:
`buildingtransformation@ontario.ca`

Material must be reproduced accurately and must not be presented as an official
version of the Government of Ontario.

Official sources:
- Volume 1 — https://www.publications.gov.on.ca/store/20170501121/Free_Download_Files/301880.pdf
- Volume 2 — https://www.publications.gov.on.ca/store/20170501121/Free_Download_Files/301881.pdf
