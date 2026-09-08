# OBC remediation pack

Drop-in for the `obc-interactive-bag` pipeline. Closes the two retrieval gates that do not hold as stated, restores definition granularity, persists modality, and adds the control discipline that would have caught every defect found so far.

Runs against the shipped `obc.sqlite` or `obc-vec.sqlite` with no other inputs. Every stage writes a new database and never mutates its input.

```sh
sh run.sh obc.sqlite          # -> obc-defs.sqlite -> obc-mod.sqlite
```

## Contents

| file | goes to | what it is |
|---|---|---|
| `stage18_definitions.py` | `pipeline/` | splits definition blobs into individual terms, rewires term edges |
| `stage20_modality.py` | `pipeline/` | persists deontic modality on text-bearing leaves |
| `check29_definitions.py` | `pipeline/checks/` | D1 — definition granularity, with `NEGATIVE=1` control |
| `check33b_completeness.py` | `retrieval/checks/` | R4a/b/c — **replaces** `check33_completeness.py` |
| `check35_controls.py` | `pipeline/checks/` | H10 — every ratio gate must be falsifiable |
| `obc_context.py` | `retrieval/lib/` | context-bundle assembler (library + CLI) |
| `obc_agent_tools.py` | `retrieval/lib/` | agent tool surface: 6 JSON-schema tools, optional MCP server (`--mcp`) |
| `tool-schemas.json` | — | the six tool definitions, for any tool-calling framework |
| `GATES-remediation.md` | `gates/` | gate declarations with evidence digests |
| `run.sh` | pack root | end-to-end orchestration |

## What each fix was for

**`stage18` — definition granularity.** 570 defined terms resolved to 6 blob nodes, the largest 31,199 characters. Every edge was valid, so no existing check had anything to find; but retrieving *secondary suite* returned 16 KB beginning with sanitary sewers, and truncation silently substituted a different term's definition.

```
distinct definition targets   6  ->  383
defined_term nodes            0  ->  403
mean definition length   16,930  ->  215 chars
term edges resolved           0% ->  98.12%
```

Residual is enumerated in `check29`, not tolerated by a threshold: 11 terms whose surface form contains a comma or slash, and `DEF/cavity-wall`, whose next term is a fifteen-word phrase containing an internal citation.

**`check33b` — R4 replaced.** The original computes `carried = len(dep & bundle(nid)) / len(dep)` where `bundle()` unions in `refs | terms`, which *is* `dep`. The ratio is 1.0 for every node in the corpus; the `< 0.99` condition cannot fire. It splits into three claims that fail for different reasons:

| | measures | fails when |
|---|---|---|
| C1 reachability | expansion reaches each dependency at *n* hops | traversal misses an edge |
| C2 delivery | the rendered, budget-trimmed bundle contains it | hop limits or budget drop it |
| C3 usability | the definition delivered is that term's own | granularity is wrong |

Against the shipped `obc-vec.sqlite`, **C3 was 1.89%** — 52 of 53 definitions delivered were blobs, scored 100% by the original.

**`obc_context.py` — two assembler bugs and a policy.**

*Own tables were silently dropped.* A table belonging to the anchor is a descendant, so it enters `seen` before expansion, is skipped by both the outbound and inbound paths, and renders as nothing because table text lives in `cell`, not `body`. The table that *is* the requirement disappeared while the bundle looked complete.

```
table reachability   40/320  ->  298/320  ->  320/320
```

*The trim path dropped the protected table.* A size-ordered trim removes the largest object first, which for a hub is the very table the by-reference notice promises. Own tables are now never dropped; rows are capped instead.

*Hub policy.* Corpus delivery was 90.06%, and two articles were 90.5% of the shortfall — `B/1/1.3.1.2` (677 dependencies) and `B/11/11.5.1.1` (382). Not a budget problem: 8k → 32k tokens moved it only to 92.52%. The median article has 3 dependencies and the 95th percentile 11. Articles above 50 are now delivered by reference — own tables plus a count and a pointer, never a truncated expansion — and enumerated in the check.

*Flattened tables in article bodies.* An article that owns a table repeats the entire table as run-on prose in its own `body`, alongside the structured grid in `cell`. `B/11/11.5.1.1` carries 126,177 characters this way; `B/1/1.3.1.2` carries 56,202. Across the corpus, **179 of 1,640 body-bearing articles** do it, and their mean body is **1,693 characters against 91** for articles without a table — 303,204 characters of duplicated grid.

The assembler now suppresses the tail and renders the grid. `B/1/1.3.1.2` fell from 15,458 to **4,442 tokens**, inside budget for the first time.

**This also affects the vectors.** Embeddings are article-level over article text, so those 179 vectors are dominated by run-on flattened table content rather than the provision's meaning. Suppressing the flattened tail before embedding is a cheap change to `stage19_embed.py` and should be made before the model experiment, not after — otherwise the experiment measures noise.

**`check35` — H10, the change that matters most.** Gate H4 requires a control for every *absence* assertion. `check33` was a **ratio**, and a ratio computed from its own source is indistinguishable from a healthy one. H10 requires every ratio-reporting gate to register a mutation that drives it below its floor.

Writing it immediately caught three void controls, one of them in this pack's own C1 metric: deleting the `ref` table shrinks numerator and denominator together and leaves the ratio at 100%. **A mutation must target the mechanism under test, never the ground truth the mechanism is scored against** — the same error as `check33`, one level up. The registry now uses parameter mutations (`hops=0`, `budget=200`) and mechanism-only data mutations.

## Current numbers

```
D1  definitions        403 nodes, 98.12% edges resolved, mean 215 chars   PASS
R4a reachability       10486/10486 = 100.00%   (floor 99%)                PASS
R4b delivery           10445/10486 =  99.61%   (floor 95%)                PASS
R4c usability            8742/8750 =  99.91%   (floor 99%)                PASS
R8  modality           15,960 leaves; 6,562 normative (41.1%)             PASS
H10 controls           all 4 ratios fall below floor under mutation       PASS

hubs delivered by reference: 4  (B/1/1.3.1.2, B/11/11.5.1.1,
                                 B/9/9.41.2.2, B/3/3.2.2.18)
```

Modality distribution over 15,960 text-bearing leaves: 48.7% statement, 38.0% obligation, 6.6% permission, 3.6% exemption, 3.2% prohibition.

## Two findings this pack does not fix

**44 of 64 nodes whose heading says "See Note" have no `note` edge.** Stage 7 scans body text but not headings, so `9.32.3.8` — whose heading reads *Protection Against Depressurization (See Note A-9.32.3.8.)* — carries no link to its own explanatory note. Phase 12.

**Table row boundaries.** With `9.30.3.1` now visible, `Matched hardwood (interior use only) 400 7.9 19.0 600 7.9 33.3` renders as a single cell — an entire logical row collapsed. This is the header/row-boundary defect from the gap register, with a reproducible example. Phase 12.

## Still open from earlier reviews

`ROADMAP.md` and `GATED_STATUS.md` describe Phases 5–9 as future and G15/G16 as UNMET; the artifacts contradict this. `check22_docs.py` passes over both files, so H3 overstates what it guarantees. Extend its scope to `reports/*.md`.

## Agent surface

`obc_agent_tools.py` turns the library into a contract an agent can call: `obc_capabilities`, `obc_search`, `obc_get_provision`, `obc_get_context`, `obc_neighbors`, `obc_what_cites`. Every result carries node ids and verbatim text. `obc_capabilities` is a tool rather than documentation, so an agent can discover what the graph *cannot* answer — applicability, occupancy, objectives, in-force dates, compliance — instead of reasoning its way to a confident wrong answer.

```sh
python3 obc_agent_tools.py --demo --db obc-mod.sqlite
python3 obc_agent_tools.py --schemas            # JSON tool definitions
OBC_DB=obc-mod.sqlite python3 obc_agent_tools.py --mcp   # MCP server (mcp>=2)
```

## Usage

```sh
python3 obc_context.py 9.32.3.8 --db obc-mod.sqlite
python3 obc_context.py "secondary suite ventilation" --hops 2 --budget 6000
python3 obc_context.py B/1/1.3.1.2 --db obc-mod.sqlite     # hub, by reference
python3 obc_context.py --search "makeup air" --limit 10
python3 obc_context.py --modality-report

python3 check33b_completeness.py --db obc-mod.sqlite --all-articles
python3 check35_controls.py --db obc-mod.sqlite
NEGATIVE=1 python3 check29_definitions.py --db obc-mod.sqlite   # must FAIL
```

---

Unofficial derived work. Current to 2025-01-16 (through O. Reg. 5/25). Not the official Building Code Compendium.
© King's Printer for Ontario, 2024. Reproduced with permission.
