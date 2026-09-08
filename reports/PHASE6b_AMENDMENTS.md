# Amendment markers — the legally consequential gap. Gate: PASS

The Compendium flags every changed provision with a marker in the margin. There
are **153 of them** and the model did not see any. They carry which regulation
changed a provision and when it came into force, so a reader working from the
model had no way to know whether a clause was current.

## The legend was on page 6 all along

Page 6 pairs each marker with the statement it refers to:

| marker | kind | instrument | in force |
|---|---|---|---|
| `r1` | regulation | **O. Reg. 447/24** | 1 January 2025 |
| `r2` | regulation | **O. Reg. 5/25** | 16 January 2025 |
| `e1` | editorial correction | — | 1 January 2025 |
| `e2` | editorial correction | — | 16 January 2025 |

Stage 9 parses that page rather than hard-coding it, so a future edition with new
markers is read, not patched.

## Attachment

**149 of 149** non-legend markers now attach to the provision they annotate.
138 nodes carry an amendment; markers also propagate up to the enclosing article
so a search at article level finds a change made to one of its sentences.

| flagged node type | count |
|---|---|
| sentence | 113 |
| clause | 11 |
| article | 7 |
| contents / subsection / part / index | 7 |

```json
"amendment": [{"marker": "r2", "kind": "regulation",
               "instrument": "5/25", "effective": "16 January 2025"}]
```

You can now ask the model a question it could not answer before — *what did
O. Reg. 5/25 change?*

```
B/9/9.9.4.4/(1)      C/1/1.7.1.1/(1)     C/3/3.1.2.2/(1.1)
C/3/3.1.3.2/(1.1)    C/3/3.1.4.2/(1.1)   C/3/3.5.2.1
```

## The bug that cost half the markers

The first pass attached only 80 of 149. I had matched the marker by absolute
position — `x < 32`, the left margin — because that is where every marker on
page 6 sits.

The Compendium **flips the margin on facing pages**, and on two-column pages the
marker sits in the gutter before the second column. 66 markers live at x≈54.

The fix identifies a marker by being the left-most thing on its baseline rather
than by an absolute x. Same class of error as the header-band assumption that hid
the Building Code Act: calibrating a rule on one sample of the page geometry and
assuming the document is consistent. It is not.

A second, smaller case: the `e1` on p681 flags the whole *Part 8* title block and
sits 11pt below the title, outside a same-baseline window. Markers now also look
up to 30pt above.

## Gates

| check | result |
|---|---|
| 9 amendment markers | **PASS — legend 4/4, 149/149 attached, 0 orphans** |
| 3 numbering continuity | PASS — 4,765 parents, 0 gaps |
| 4 text capture | PASS — 0.083% |
| 8 model build vs patched | PASS — 35,862 links, 578/0/0 TOC, 0 pages lost |

## Deliverable

`301880_built_from_model_protected.pdf` — 19.3 MB, AES-256, owner `ObcAdmin-2024`.

## Remaining

- **Phase 7** — the Index is still one flat node of 7,088 lines
- **Phase 8** — Volume 2 and its 1,054 references
- 21 tables unbound, 182 standards absent from Table 1.3.1.2., table header rows
  not identified
- Amendment markers are modelled but not yet *surfaced* in the PDF: a reader
  still sees the bare `r2` in the margin with no way to reach the legend. A link
  from every marker to page 6 is a small addition to stage 8.
