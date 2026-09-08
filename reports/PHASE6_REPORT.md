# Phase 6 — the Building Code Act as a real tree. Gates: PASS

The Act held **3,896 lines of flat text** under 85 section nodes. It is now
parsed to the same depth as a Division.

| | before | after |
|---|---|---|
| act_section | 85 | 85 |
| act_subsection | — | **430** |
| act_clause | — | **230** |
| act_subclause | — | **27** |
| flat text left on section nodes | 3,896 lines | **50 lines** |
| graph nodes | 18,494 | **19,181** |

No new grammar was needed. The Act uses the same marker forms as the Code —
`(1)` subsections, `(a)` clauses, `(i)` subclauses — so the sequence rules from
the Division walk applied unchanged, including the `(i)`-is-both-clause-and-roman
disambiguation.

**Marginal notes are now headings.** The Arial-Black lines in the Act's margin
(`Responsibility`, `Certificate`, `Debt`) title the subsection that follows them.
356 subsections carry one:

```
ACT/15.4.2   heading "Debt"   children [ACT/15.4.2/(1), ACT/15.4.2/(2)]
ACT/34       subsections 0.1, 1, 1.1, 2, 2.1, 2.2, 2.3, 3 …
```

## References now land inside the Act

`subsection 34(2.3)` — the citation from the screenshot that started this whole
line of work — previously resolved to the *section*. It now resolves to the
subsection itself:

```
subsection 15.11(5)  ->  ACT/15.11/(5)
subsection 1(1)      ->  ACT/1/(1)
```

**198 of 350 resolved Act references now land on a subsection or clause** rather
than the top of a section.

## Gates

| check | result |
|---|---|
| 3 numbering continuity | **PASS — 4,765 parents, 0 unexplained gaps** (was 4,609; the Act now participates) |
| 4 text capture | **PASS — 0.083% orphaned** |
| 8 model build vs patched | **PASS — 35,862 links, 578/0/0 TOC, 0 pages lost** |

Continuity is the meaningful one: the Act's subsection numbering — which includes
insertions like `0.1`, `1.1`, `2.1`, `2.2`, `2.3` — runs clean across all 85
sections with no unexplained holes.

## Two check bugs, again in the checks

Check 4 dropped to 0.339% orphaned when the Act tree landed, then to 0.260%,
before returning to 0.083%. Neither drop was the parser:

1. Its marker reconstruction listed `sentence, clause, subclause` but not the
   three new `act_*` types, so every Act marker looked like lost text.
2. It never added a node's `heading` back, so 356 marginal notes looked lost too.

Fourth and fifth time this has happened. The check is now the first suspect.

## Deliverable

`301880_built_from_model_protected.pdf` — regenerated, 19.3 MB, AES-256,
owner `ObcAdmin-2024`. 35,862 internal links, 445 web, 0 dead, 3,907 bookmarks.

## Remaining

- **Phase 7** — the Index is still one flat node of 7,088 lines
- **Phase 8** — Volume 2, and the 1,054 references that need it
- **153 amendment markers** (`e1`, `r1`, `e2`, `r2`) still unmodelled — these
  flag provisions changed by O. Reg. 5/25 and carry effective dates
- 21 tables unbound, 182 standards absent from Table 1.3.1.2., table header rows
  not identified
