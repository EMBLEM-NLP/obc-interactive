# 2024 Building Code Compendium, Volume 1 — Interactive Edition

Source: `301880.pdf` (O. Reg. 163/24), Ontario Ministry of Municipal Affairs and Housing.
Deliverable: `301880_built_from_model_protected.pdf` — 1,260 pages, 18.9 MB, AES-256,
`print:yes copy:yes change:no addNotes:yes` (identical to the source file's permission set).

Owner password: **`ObcAdmin-2024`** — change this before distributing.
No open password; the file opens freely, as the original did.

---

## How this build is produced

This file is **generated from a document model**, not patched. The pipeline in
`pipeline/` parses the pristine source into `docgraph.jsonl.gz` (18,494 nodes),
resolves every citation against that model, and emits the PDF, its outline and
its page labels in one pass. Rerunning from the same source reproduces it.

Superseded: `301880_interactive_v9_protected.pdf`, produced by page-by-page
patching. It remains correct but has 7,935 fewer links.

## What changed

### Navigation links

| | Source | Now |
|---|---|---|
| Internal GoTo links | 1,558 | 35,863 |
| Web / mail links | 431 | 445 |
| Broken `Launch` links | 819 | 0 |
| Bookmarks | 832 | 3,907 |

**Table of contents.** 578 section links across the 22 Part contents pages verified
against printed page labels; 18 wrong targets repaired, 2 missing links added.
Master TOC (p.7): 25 links, one per row.

**Cross-references.** The source contained 819 links pointing at ministry Word
sources on an internal network share (`\\CSC.ad.gov.on.ca\...`) and one author's
local drive. All were dead and leaked internal paths. 749 were resolved to real
in-document destinations; 70 whose targets live in Volume 2 were removed.

**Document-wide reference linking.** 16,127 clause references, 334 table and
figure references, and 329 cross-division Index references, resolved against a
division-aware index of 3,453 headings and 331 captions. Includes references
inside tables.

**Defined terms.** 8,096 links, first occurrence of each term per page
(7,168 to Division A 1.4.1.2., 928 to the Building Code Act).

**Building Code Act (pp. 29–74).** The Act carries no "Division – Part" footer,
so it was initially skipped by the reference pass. Now covered: 83 contents
entries on the Act's own CONTENTS pages, 103 internal cross-references
("section 8", "subsection 15.1(3)"), and 18 Code-clause references on the front
matter and Preface pages. References to other statutes (Municipal Act, Fire
Protection and Prevention Act, etc.) are deliberately left unlinked.

**Other.** 519 standards citations to Table 1.3.1.2. (body text cites them
without the year suffix, e.g. `CSA A82.30-M`, while the table lists
`A82.30-M1980`, so matching is by prefix); 12 `C.A.` references; 5 bare URLs.

### Errors found in the source file

- 18 table-of-contents links pointed one page early.
- 67 body cross-references pointed one to three pages off. Example: `Section 9.20.`
  on p.794 pointed to p.836; the section begins on p.837.

Only links where the same-division match disagreed by three pages or fewer, with
no "of Division X" qualifier, were repaired. 81 other disagreements were left
alone as legitimate cross-division references.

### Appearance

- Light-blue bands behind the 906 clickable TOC rows, drawn *beneath* the text.
- Blue underlines under body cross-references and standards citations.
- Defined terms left unmarked — the Code's italics already signal them.

No original text was moved, recoloured or altered. All added marks are new page
content drawn under or beside existing glyphs; the text layer is unchanged and
remains searchable and selectable.

### Document properties

- Page labels: the viewer's page box now shows `Div B Part 9, 276`, `BCA Page 1`,
  `Index I - 14`, roman numerals for the Preface. 23 label ranges.
- Title, subject and keywords set (were empty).
- Opens with the bookmark panel visible.

---

## Known gaps

These need the Volume 2 PDF and cannot be resolved inside this file:

| | Count |
|---|---|
| `See Note A-x` references (Appendix A) | 1,008 |
| Supplementary Standard references (SA-1, SB-1…SB-13, SC-1) | 118 |
| Volume 2 contents entries (p.8) | 20 |

Also unlinked:

- **109 clause references** citing articles this edition does not contain
  (e.g. `5.10.1.1.`, cited 42 times in the Index; Part 5 has no Section 5.10).
  These degrade to the nearest existing parent rather than failing.
- **10,730 repeat defined-term occurrences**, deliberately skipped to keep text
  selection usable.

## Coverage audit

A final audit scanned all 1,260 pages for reference-like tokens without relying
on page classification (the assumption that hid the Building Code Act). Of
23,261 tokens found:

| | |
|---|---|
| linked | 17,167 |
| headings, captions and running headers — correctly plain | 5,736 |
| inside Table 1.3.1.2. itself | 138 |
| cite a clause not present in this edition | 129 |
| target is on the same page — deliberately skipped | 89 |
| front matter with no division context | 2 |
| **unexplained misses** | **0** |

## Verification performed

- 578/578 TOC section links resolve to the page bearing the cited printed number.
- 191/192 randomly sampled reference links land on a page containing the cited
  number; the exception cites a non-existent article and degrades correctly.
- 60/60 sampled article bookmarks land on the right page.
- 0 GoTo targets outside the document.
- 0 remaining `Launch` links.
- 40/40 sampled standards links land on a page listing that designation.
- 0 unexplained gaps in the classification-free coverage audit.

## Licensing note

The ministry's terms (pp. 3–4 of this document) permit non-commercial reuse of
Crown copyright material to create new digital formats, and require this
statement on any product containing the Compendium:

> © King's Printer for Ontario, 2024. Reproduced with permission.

The terms also require that material be reproduced accurately and that the
product not be presented as an official version. This edition adds navigation
and visual cues to the ministry's text; it is not an official version.
Commercial use requires a licence — `buildingtransformation@ontario.ca`.
This note is a pointer to the document's own terms, not legal advice.
