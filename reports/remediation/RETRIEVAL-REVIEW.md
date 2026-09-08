# Review: updated bag — Phase 10 retrieval

Reviewed 2026-09-07. Diffed against the 2026-09-07 02:01 bag.

---

## 1. What changed

Bag revalidates: tag manifest 5/5, payload **154/156** (the 2 failures are exactly the `fetch.txt` entries), `Payload-Oxum: 265311548.154` exact. Ten files added, one changed (`MANIFEST.sha256`), none removed.

```
data/emitters/obc-vec.sqlite          2,749 article vectors, 384-dim
data/retrieval/stage19_embed.py
data/retrieval/lib/hybrid.py          fts / vec / RRF fusion
data/retrieval/evalset.json           50 questions
data/retrieval/checks/check30..34.py
data/gates/GATES-retrieval.md         R1–R5, all [x]
```

## 2. What is right

**Model pinning is done properly.** `embed_meta` carries `model`, `dim`, `count`, `context`, and a `vectors_sha256`. That closes the risk I ranked second in the phase plan — a silent model swap is now detectable. This is better than what I asked for.

**The eval set is honestly constructed**, and its own metadata says so:
- Hand-written by reading the provision, *not* generated from the provision text by a model.
- Deterministic 50/50 dev/test split by SHA-256 of the question; **fusion weight tuned on `dev` only**, reported and gated on `test`.
- The `paraphrase` subset is mechanically constrained to share no content word with the target, which is the only condition under which lexical retrieval is guaranteed to fail and the vector layer must earn its place.
- Limitations stated plainly: 50 questions, Part 9 weighted, not reviewed by a building official.

That is the discipline the rest of the pipeline already has, applied to evaluation. **R5 (`check34`) is a genuine negative control** — it scrambles every embedding onto the wrong node and requires the harness to notice.

## 3. R4 does not measure anything

`check33_completeness.py` computes:

```python
def dependencies(nid):  return refs, terms
def bundle(nid):        got = {nid} | descendants | ancestors | refs | terms
carried = len(dep & bundle(nid)) / len(dep)      # dep == refs | terms
```

`bundle` unions in `refs | terms`, which **is** `dep`. So `dep & bundle(nid) == dep` identically, and the ratio is `1.0` for every node. The `< 0.99` condition cannot fire.

Measured directly over the corpus, not the 27 test questions:

```
articles with dependencies : 2449
mandatory context carried  : 11680/11680 = 100.0000%
articles scoring below 100%: 0
```

The check re-derives the dependency set and compares it to itself. The assembler it claims to measure is never called — no hop limit, no budget, no edge-kind selection.

**R5 does not cover this.** Scrambling the vector index changes *which* targets are retrieved; for whatever targets are retrieved, completeness stays identically `1.0`. R5 protects R3. R4 has no control, which is precisely the condition gate H4 exists to forbid.

## 4. The vectors were built on the unfixed model

`obc-vec.sqlite` has **0 `defined_term` nodes** and 10 distinct term targets — `stage18_definitions.py` was not folded in, so every definition the retriever hands back is still a blob averaging 16,930 characters.

This compounds with §3: R4 counts "carried the definition" as satisfied when the bundle carries a 31,199-character clause holding 136 unrelated definitions. It scores 100% while delivering the wrong rule.

## 5. Replacement check, and what it actually measures

`check33b_completeness.py` calls the real `obc_context.build_bundle` and reports three things separately, because they fail for different reasons:

| | measures | fails when |
|---|---|---|
| **C1 reachability** | can expansion reach each dependency at *n* hops | the graph or the traversal misses an edge |
| **C2 delivery** | does the *rendered, budget-trimmed* bundle contain it | hop limits or the token budget drop it |
| **C3 usability** | is the delivered definition that term's own, or a blob | granularity is wrong — invisible to the original |

Run against the shipped `obc-vec.sqlite`, on the same 26 test targets:

```
C1 reachable at 1 hop        : 85/88 = 96.59%   (floor 99%)   FAIL
C2 delivered under 8k budget : 85/88 = 96.59%   (floor 95%)
C3 definitions usable        :  1/53 =  1.89%   (floor 99%)   FAIL
```

**C3 was 1.89%.** Fifty-two of fifty-three definitions delivered were blobs. The original check scored the same corpus 100%.

## 6. A third bug, in my assembler

C1's 96.59% was not a definition problem. Three targets were missing a dependency, and all three were **the article's own table**:

```
B/9/9.30.3.1   missing B/9/table/9.30.3.1    (cap_ref)
B/3/3.13.4.5   missing B/3/table/3.13.4.5    (cap_ref)
B/4/4.1.6.10   missing B/4/table/4.1.6.10    (cap_ref)
```

A table belonging to the anchor is a *descendant*, so `scope_ids` puts it in `seen` before expansion begins; the outbound path then skips it as already-seen, the inbound path skips it too, and `subtree_text` renders nothing because a table's text lives in `cell`, not `body`. The table that **is** the requirement disappears, and the bundle still looks complete.

Fixed by emitting the anchor's own tables explicitly, before expansion.

| Table reachability | tables |
|---|---|
| As shipped (`ref` edges only) | 40 / 320 |
| After the parent-binding fix | 298 / 320 |
| After the own-table fix | **320 / 320** |

688 of 2,749 articles now surface at least one table.

After both fixes, on the eval targets:

```
C1 reachable at 1 hop        : 88/88 = 100.00%   PASS
C2 delivered under 8k budget : 88/88 = 100.00%   PASS
C3 definitions usable        : 53/53 = 100.00%   PASS
```

## 7. The finding the eval set could not have caught

Run over **all 2,449 articles** rather than 26 test targets:

```
C2 delivered under 8k budget : 10519/11680 = 90.06%   (floor 95%)   FAIL
C3 definitions usable        :  8836/8844  = 99.91%              PASS
```

Eight articles fall short, and two of them are 90.5% of the entire shortfall:

| article | delivered | heading |
|---|---|---|
| `B/1/1.3.1.2` | 1 / 677 | Applicable Editions — the referenced-standards table |
| `B/11/11.5.1.1` | 7 / 382 | Compliance Alternatives |
| `B/9/9.41.2.2` | 3 / 71 | Performance Level Evaluation |
| `A/1/1.4.1.2` | 8 / 35 | Definitions |

This is **not** a budget-tuning problem. Quadrupling the budget moves the number barely at all:

```
8,000 tokens  -> 90.06%
16,000 tokens -> 90.29%
32,000 tokens -> 92.52%
```

The median article has **3** dependencies and the 95th percentile has **11**, so the ordinary case is nowhere near the limit. Two hub articles are structurally unbundleable — no context window holds 677 expanded standards. They need a policy, not a bigger budget: for the standards table, the useful bundle is the *table plus a pointer*, not 677 expanded nodes.

The 26 test targets contain no hub article, which is why 50 questions could not surface this.

---

## Recommendations

**REMOVE — `check33_completeness.py`.** It cannot fail. Replace with `check33b_completeness.py` and restate gate R4 as three separate claims (reachability, delivery, usability) rather than one blended number.

**ADD — `stage18_definitions.py` + `check29` to the pipeline, before the emitters.** The vector index itself does not need rebuilding — article embeddings are unaffected by the definition split — but `term_resolved` must exist at retrieval time or C3 stays at 1.89%.

**ADD — a hub-article policy.** Enumerate `B/1/1.3.1.2` and `B/11/11.5.1.1` (and any article above ~50 dependencies) as bundle-by-reference: deliver the table and a count, not the expansion. Enumerate them the way `check29` enumerates its residual, so the set cannot grow silently.

**UPDATE — the eval set, in two directions.** The `test` split is 27 questions of which only **5** are `paraphrase`, so R3's central claim — that the vector layer earns its place where lexical retrieval fails — currently rests on five questions. And no hub article appears at all. Add paraphrase questions and deliberately include high-dependency targets.

**UPDATE — `check34` should also control R4**, not only R3. A completeness metric with no control is the exact failure H4 was written to prevent, and it recurred here in a new phase.

**Note for Phase 12.** The now-visible `9.30.3.1` grid shows a concrete instance of the table-header gap: `Matched hardwood (interior use only) 400 7.9 19.0 600 7.9 33.3` is a whole logical row collapsed into one cell. That is the header/row-boundary defect from the gap register, with a reproducible example.

**Unchanged from the previous review.** `ROADMAP.md` and `GATED_STATUS.md` are still stale, and `check22_docs.py` still passes over them.

---

Unofficial derived work. Current to 2025-01-16 (through O. Reg. 5/25). Not the official Building Code Compendium.
© King's Printer for Ontario, 2024. Reproduced with permission.
