# Track audit — revision 11

A4 executed as step 2 by a subagent, Claude Code on the web, 2026-09-08. Revisions 1–10 preserved unedited.

**Headline: A4 was authored as far as it can be authored without the graph, and handed back unfinished on purpose. The executor refused to fake DATA1, touched nothing tracked, and returned two things worth more than the schema: a guard of mine that blocked *reading about* a check as though it were running one, and evidence that the SQLite emitter silently drops the table binding that `stage5_bind.py` computes. Track A4 remains `ready`. Nothing here is done.**

---

## WHAT MOVED

| item | evidence |
|---|---|
| A4 step 2, authored | `schema/obc.linkml.yaml`, 315 lines. `yaml.safe_load` parses it: 10 classes, 5 enums, `NodeType` 23 values, `EdgeKind` 10 values. Recovered from the executor's worktree into the branch before the container reclaimed it. |
| Its check and control | `schema/proposed/check36_schema.py` → `node types declared: 23`, `edge kinds declared: 10`, `RESULT: PASS`. `NEGATIVE=1` strips the `reverse` annotation from one `EdgeKind` and 0 failures become 1, `RESULT: PASS`. Both re-run here, not taken on report. |
| Guard bug found and fixed | The corpus rule grepped the whole command string, so `grep -rn 'check33b_completeness' .` **and `cat` on the file** were refused as though the check were being run in eval mode. It now lexes and asks whether check33b is in command position. 3 regression cases; suite 68 → **71**, `RESULT: PASS`. |
| The counts the work package assumed are wrong | A4's sanity threshold speaks of "22 node types and 8 edge kinds". Measured from source: **23** types (21 from `stage3_tree.py` and `stage3v2_tree.py`, `table` from `stage5_bind.py:82`, `defined_term` from `stage18_definitions.py:267` — the last postdates the work package) and **10** edge kinds (the nine of the stage7 grammar at `stage7_refs.py:70-79`, plus `term`). |

---

## WHAT DID NOT

**A4 is not done and its status is unchanged: `ready`.** Steps 3 (MUTATE against real data), 4, 5, 6 and 7 were not performed. `tracks.yaml` was not edited by the executor or by me on its behalf. Every other track unchanged. **7 of ~31.**

- The board still reports `E1 PASS, E2 PASS, DATA1 FAIL`. Gate S0 was never run: it needs the graph.
- `check35_controls.py` carries **no S0 entry**, so S0 is a void ratio gate until the proposed patch is installed. The executor could not install it — `harden/checks/**` is protected, and it stopped rather than routing around the guard.
- Three files are staged at `schema/proposed/` because their real paths are protected: `check36_schema.py` → `harden/checks/`, `GATES-A4.md` → `gates/`, and a patch for `check35_controls.py`. **A human must install all three.** This is finding 3 of revision 10 in practice, not in theory.
- Unestablished without data, and listed by the executor rather than glossed: the actual distinct `node.type` values across 27,421 rows; the actual distinct `ref.kind` values; the declared-type and declared-kind shares; violation counts for its three defect predicates; whether the H10 control's `real` measures 1.00 on real data; whether every `term_resolved.dst` is a `defined_term`; the SHACL projection, since `linkml` is not installed.

---

## WHAT BROKE

1. **My corpus guard blocked reading.** Reproduced before fixing: `grep -rn 'check33b_completeness' .` → exit 2, and `cat retrieval/checks/check33b_completeness.py` → exit 2. Substring matching cannot tell data from code — the same defect as the commit verb matching inside a heredoc, which I fixed this morning **and left standing in the rule two lines below it**. Fixing one instance of a defect class and not looking for its siblings is how the class survives.
2. **The line budget was exceeded and said so.** 315 lines against the work package's ~300. The executor reported the overage rather than padding it away, and noted ~46 lines are `defect:` annotations carrying file-and-line evidence, so the structural schema is ~250.

---

## WHAT WAS FOUND

### 1. The emitter drops the table binding, so the dual encoding is not symmetric
`pipeline/stage5_bind.py:84` writes both `parent = target or pid` and `forming_part_of: target` on a table node. `pipeline/emitters/stage15_sqlite.py`'s `node` table has thirteen columns — `rowid, id, permalink, volume, type, number, designator, heading, body, parent, depth, page, bbox` — and `forming_part_of` is not one of them. The string appears **nowhere** in the emitter. `pipeline/stage6_figures.py:73` sets the same field for figures, and it is dropped too.

Verified here directly, not taken on report.

So in `obc-mod.sqlite` — the artifact every retrieval path, `obc_context.py` and the MCP server actually read — the binding survives **only** inside the overloaded `parent`, which is the bound provision when the caption parsed and the containing Part when it did not. No consumer can distinguish *"Table 9.23.2.8. forms part of Sentence 9.23.2.8.(1)"* from *"this table sits in Part 9"*.

Track B item **B2** already says "forming_part_of as explicit ref edge in the emitter, schema-enforced", so the work is anticipated. What is new is the evidence that the field is computed and silently discarded rather than merely encoded twice, that the defect is therefore **worse in the shipped database than in the JSONL**, and that figures are affected as well — which B2's description does not mention. Owner: Track B. A4 can only declare it.

### 2. An executor that cannot verify is more useful when it says so
The Stop hook blocked the executor on missing data. It did not write stub files to turn DATA1 green — and said why: DATA1 exists to catch pointer stubs, so satisfying it with fabricated data converts "I could not verify" into a false green. That is the protocol's central rule, applied by an agent under pressure to finish, without being told in the moment. Its audit addendum opens **"WHAT MOVED. Nothing."**

Worth recording because the opposite is what this project keeps finding, and because the session that dispatched it has twice this week accepted a report that the tree contradicted.

### 3. Two more harness observations
`python3 harden/checks/check41_machinery.py` invoked directly was refused by the permission classifier, while the same check ran fine through `ci/run_gates.py` (E2 PASS). And three Bash calls were refused by worktree isolation for heredoc or variable complexity. Neither is a project defect; both shape what an executor in a worktree can actually do, and neither is documented anywhere.

---

## Tally and next action

**7 of ~31 done.** A4 is `ready`, not `done`, and this revision exists partly so that nobody reads a 315-line schema as progress on it.

1. Publish the data tarball; set `OBC_DATA_URL`, `OBC_PDF_URL_V1`, `OBC_PDF_URL_V2`, `ANTHROPIC_API_KEY`. Item 1, unchanged for four revisions.
2. Install the three staged files at their real paths, or settle finding 3 of revision 10 — the staging convention — so a track can produce the checks it is specified to produce.
3. Re-run A4 steps 3–7 with data. Only then can S0 be declared or A4 closed.
4. File the emitter finding against Track B, B2.

---

Unofficial derived work. Current to 2025-01-16 (through O. Reg. 5/25). Not the official Building Code Compendium.
© King's Printer for Ontario, 2024. Reproduced with permission.
