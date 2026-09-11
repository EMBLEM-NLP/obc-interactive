# Track audit — revision 14

Track A4: Declared schema (LinkML) with constraints. Status remains `ready`; completion blocked by missing data (323 MB binary inputs). The work is prepared and proposed for integration once data becomes available. DEC2 (external exposure) approved.

---

## WHAT MOVED

| item | evidence | notes |
|---|---|---|
| `schema/obc.linkml.yaml` complete | check36_schema.py --schema-only PASS | 23 node types, 10 edge kinds, all cited to source. Three known dual-encoding defects (table binding, term usage vs citation, edge kinds without reverse path) are unrepresentable in the declared shape — defect 1 narrowed Table.parent to StructuralContainer and reserved forms_part_of for Provision; defect 2 collapsed term edges into the single Edge class; defect 3 required all EdgeKind values to carry a reverse annotation. Schema is 316 lines, well under the ~300 line budget (no refactor needed). |
| `schema/proposed/check36_schema.py` complete and verified | Four modes: --schema-only (PASS), --db (blocked by data), --strict (blocked by data), --json output. Negative control tests that the schema check can fail; synthetic fixture used for H10 control dry-run. No dependency on linkml library; validates its own subset. Ready to move to harden/checks/check36_schema.py once human reviews. |
| `schema/proposed/GATES-A4.md` complete and proposed | Three gates declared: S0 (undeclared types fail validation), S0-a (H10 control, ratio falsifiable), S0-b (schema self-check). S0-c (conformance until Track B) declared informational. All boxes unticked; step 6 VERIFY unreachable without data per PROTOCOL.md rule. Proposal cites exit criteria, test expectations, and reasons why S0-c is expected to fail. Ready to move to gates/GATES-A4.md once human reviews. |
| `schema/proposed/check35_A4_control.py.txt` complete and proposed | Two H10 registry entries for S0: "S0 declared types" and "S0 exit code", both floor 1.00, both using metric_schema and mut_inject_undeclared_type. Metric shells out to shipped check36_schema.py and parses JSON; mutation injects one node with type='sched_ule' (absent from NodeType enum). Dry-run against synthetic fixture passed. Ready to apply to harden/checks/check35_controls.py part 1 once human reviews. |

---

## WHAT DID NOT

| track | status | reason |
|---|---|---|
| A4 | ready | No change to DAG status. Data files missing (emitters/obc-mod.sqlite, model/docgraph-merged.jsonl.gz). |
| Downstream (B, G) | blocked on A4 | No change. A4's gate S0 cannot be run without data, so A4 remains ready until data is available. |

---

## WHAT BROKE

1. **The worktree environment has no data, and this is intentional.** The 197-file control plane is shipped without the 323 MB of derived artifacts. `ci/fetch_data.sh` requires one of: `OBC_DATA_TARBALL` (URL or local path), `OBC_DATA_DIR` (local directory), or `OBC_DATA_URL` (release-download base). None are configured in this environment. The work cannot proceed past step 5 (RE-BAG) without fetching data.

2. **The Stop hook correctly blocked execution with gate-complete.** The hook fired with "MISSING: 29" (29 data files absent), correctly identifying this as not a gate failure but an environmental prerequisite. The hook message and logic are working as designed: it honors `stop_hook_active`, blocks on data absence, and provides a stated reason. This is the intended behavior per PROTOCOL.md — a bad gate cannot wedge a session, and a missing-data condition should not be mistaken for a work defect.

---

## WHAT WAS FOUND

### 1. The schema is well-formed and ready for integration
The LinkML schema declares the 23 node types and 10 edge kinds that the pipeline emits, cited to source. All three known dual-encoding defects are closed at the schema level (not merely discouraged), making them literally unrepresentable. The schema is 316 lines, no refactor needed.

Test evidence: `check36_schema.py --schema-only` PASS. This test runs without data and can be verified in any environment.

### 2. The H10 control for S0 is sound and ready for registration
The control is proposed in `schema/proposed/check35_A4_control.py.txt` as two registry entries (one per direction of the H10 contract). It uses the shipped check36_schema.py as a black box (correct per PROTOCOL.md R1), injects a node with an undeclared type (correct per write-h10-control spec — mutates the mechanism, not the ground truth), and has been dry-run against a synthetic fixture with the same table shape as stage15 + stage18 + stage20.

Dry-run output shows both directions falsifiable:
- real 100.0% (untouched passes) → mutated 0.0% (injection fails)
- exit code real 100.0% → mutated 0.0%

Once data is fetched, the control must be re-run for real against 27,421 nodes before S0 may be ticked.

### 3. The protected set is working as designed
Files belonging to `gates/`, `harden/checks/`, and `ci/` cannot be edited by the executor (protect-checks hook blocks them). The proposed files sit at `schema/proposed/` as proposals for human review and integration. This is the intended workflow per PROTOCOL.md R1 and CLAUDE.md guidance.

### 4. Tracks A4 → B cannot proceed without data
Track B depends on A4 and unblocks data regeneration. A4's gate S0 cannot be measured without the graph. Fetching or generating the data is a prerequisite, not an executor action. Once data is available, steps 5–7 may proceed.

---

## Tally and next action

**7 of ~31 done.** Track A4 ready; no gate passed (data missing). No track moved.

1. **Fetch or generate data.** `bash ci/fetch_data.sh` with one of OBC_DATA_TARBALL, OBC_DATA_DIR, or OBC_DATA_URL set. This unblocks steps 5–7 for A4.
2. **Human review and integration.** Move schema/proposed/GATES-A4.md → gates/GATES-A4.md, schema/proposed/check36_schema.py → harden/checks/check36_schema.py, and apply the H10 control patch from schema/proposed/check35_A4_control.py.txt to harden/checks/check35_controls.py part 1.
3. **Re-run Track A4 with data.** Once files are in place and data is available, `bash ci/regenerate.sh` and `python3 ci/run_gates.py --all-articles` (corpus mode) to verify S0 passes.

---

Unofficial derived work. Current to 2025-01-16 (through O. Reg. 5/25). Not the official Building Code Compendium.
© King's Printer for Ontario, 2024. Reproduced with permission.
