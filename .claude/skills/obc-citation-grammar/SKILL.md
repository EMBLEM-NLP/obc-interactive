---
name: obc-citation-grammar
description: Parse, resolve, and format Ontario Building Code references - Division/Part/Section/Subsection/Article/Sentence/Clause/Subclause numbering, relative references that resolve only against their enclosing Article, "Forming Part of Sentences" table captions, Appendix A notes, and the node-id scheme. Use when reading, generating, validating, or citing any OBC provision.
allowed-tools: Read, Grep, mcp__obc__*
---
# OBC citation grammar

Hierarchy and node ids: `B/9/9.32.3.8` = Division B, Part 9, Article 9.32.3.8. Sentence `(1)` → `B/9/9.32.3.8/(1)`; Clause `(a)` → `/(1)/(a)`; Subclause `(i)` → `/(1)/(a)/(i)`. Tables: `B/9/table/9.30.3.1`. Notes: `APPA/A-9.32.3.8`. Definitions: `DEF/secondary-suite`. Act: `ACT/1/(1)/(d)`.

**Relative references are the trap.** "Sentence (1)" or "Clause (3)(c)" resolves only against the enclosing Article of the text it appears in. Never resolve a bare `(n)` without knowing which Article you are in. Absolute forms — `Article 9.32.3.8.`, `Subclause 8.7.2.1.(1)(b)(ii)` — resolve directly.

**Tables declare their own reverse edges:** `Forming Part of Sentences 9.23.2.8.(1), 9.23.4.2.(1)` in the caption. Both the `ref` edge and `node.parent` may carry this binding; follow both (rule R6).

**Italic terms are defined terms** (Division A 1.4.1.2 or the Act s.1). Never reason over a provision that uses a defined term without its definition — the definition changes the meaning. `obc_get_context` assembles them.

**Applicability is not in the graph** until F-scope lands. `obc_capabilities` says so from the database; a confident answer to "does Part 9 apply" is a hallucination by construction.

Full grammar, edge cases, and the four defects it caused: `references/grammar.md`.
