# Gates: MAINT — amendment diff pipeline

OWNS: tools/diff_editions.py, tools/fixtures/**

STAGED, NOT INSTALLED. This ledger belongs at `gates/GATES-MAINT.md`, which is
protected — `check41_machinery.PROTECTED` pattern `gates/GATES-*.md`, and the
`Write(...)`/`Edit(...)` denies in `.claude/settings.json`. Measured in this
worktree, `gates/GATES-MAINT.md` tests `is_protected` True under both the
relative and the absolute spelling. So it is written flat at
`proposed/MAINT/GATES-MAINT.md` and promoted by a human (PROTOCOL step 4a).

The flat layout is not a preference. Measured here with check41:

    proposed/MAINT/GATES-MAINT.md                              rel False  abs False
    proposed/harden/checks/x.py                                rel False  abs True

The mirrored layout is permitted spelled relatively and refused spelled
absolutely, because `check41._candidates()` expands an absolute path into every
suffix of itself. A permission that depends on spelling is not a permission.
`proposed/<TRACK>/<basename>` has no suffix that can match any PROTECTED
pattern.

Scope: re-run the pipeline on an amended source, diff the graph, and review only
what changed. The 144 amendment records and the AmendmentEvent model are the
foundation; the diff was the missing piece.

## The failure mode both gates are aimed at

An edition diff has two symmetric ways to be worthless, and only one of them
looks like a bug:

  - it reports nothing, and the amendment ships unreviewed;
  - it reports everything, and the amendment ships unreviewed, because 27,421
    changed nodes is not a review queue.

The second is the likely one. Between two printings of the Compendium every node
moves on the page: `provenance[].page`, `provenance[].bbox`, and each text
token's `p` and `b` all change under a repagination that changes no law at all.
A diff over raw JSON records reports 100% changed and is discarded on first use.
So `diff_editions.py` diffs a declared *substantive projection* and accounts for
layout drift separately, and M2 gates precision — not only recall — against a
fixture that has been repaginated on purpose.

## SCOPE OF THE EVIDENCE BELOW — read before trusting any result

**M1 and M2 are established on synthetic fixtures, not on the corpus.**

This clone carries no derived data. Measured, not assumed:

    python3 harden/checks/check40_dataintegrity.py --quick
    -> data files declared : 29 (323 MB)
       verified            : 0
       MISSING             : 29
       RESULT: FAIL - the gates would read wrong data      exit 1

So `model/docgraph-merged.jsonl.gz` does not exist here and **no diff of two
real editions has been run.** The fixtures are built from the record shape as it
is defined in code — `pipeline/stage3_tree.py:136` (node constructor) and `:166`
(text token), `pipeline/stage7_refs.py:197,220` (`refs`, `terms`),
`pipeline/stage9_amendments.py:99` (`amendment`),
`pipeline/emitters/stage15_sqlite.py:125` (grid cell),
`pipeline/vol2/stage10_merge.py:30` (`_meta`, `volume`),
`pipeline/emitters/emit_common.py` (`load_graph`, `node_text`), and the closed
NodeType / EdgeKind / AmendmentKind enums in `schema/obc.linkml.yaml` — never
from a guess and never from the graph itself.

**THE CORPUS RUN IS OWED.** Two real editions, diffed, with M1 and M2
re-measured at corpus scale, is a precondition of MAINT reaching `done`. It is
recorded as an `OWED:` exit criterion on MAINT in `orchestration/tracks.yaml`.

Both gates are therefore left **`- [ ]`**. They are not unrun — each ran and
each passed, and the result is recorded verbatim below — but this ledger's
convention for `[x]` is a corpus-mode run from a clean bag under
`ci/run_gates.py`, and that did not happen and could not have. Marking them
`[x]` on 15 constructed nodes would be the "green with a real digest" failure
this project already has a rule about. Green here proves the check ran on
fixtures. It proves nothing else.

Nothing in this ledger is a claim about the Ontario Building Code. It is a
claim about a tool.

- [ ] M1: a diff of a graph against itself is empty, and is byte-identical across two runs
  CHECK: python3 proposed/MAINT/check45_diff.py --gate M1
  EXPECT: RESULT: PASS
  RESULT (fixtures, 2026-09-08): PASS, exit 0
    self-diff base     0 changed, 0 layout-only, 0 amendment events
    self-diff amended  0 changed, 0 layout-only, 0 amendment events
    report digest      055262fd2d3a3247  identical across two runs: True
    fixture digests    base e90559cc17a25714  amended 92229d3870606309  stable: True
  EVIDENCE: fixture-scope only. The `automatic-evidence=v1` digest block is owed
    and must be produced by the promoter from a corpus-mode board run.
  NOT A RATIO: M1 asserts an emptiness and a byte-identity, not a proportion, so
    R1 does not require an H10 mutation for it. It is nonetheless falsifiable,
    and is falsified in practice by both mutations registered under M2 — either
    one leaves the self-diff empty while breaking M2, which is the correct
    asymmetry and is why M1 alone would not be enough.
  NOTE: two assertions, because either alone is weak. Emptiness alone passes a
    tool that outputs nothing; determinism alone passes a tool that reports every
    node identically twice. The digest is over the whole rendered report, not a
    subset of its fields — R5, check20 excluded `meta` from its determinism
    digest and the only nondeterminism in the build was in `meta`. The fixtures
    are digested too (gzip mtime pinned to 0), so an M1 failure cannot be
    misattributed to an unstable fixture.

- [ ] M2: a seeded amendment appears in the diff, and nothing else does
  CHECK: python3 proposed/MAINT/check45_diff.py --gate M2
  EXPECT: RESULT: PASS
  RATIO: precision and recall over the seeded change set
  FLOOR: 1.0 on both. Not 0.95 — the expected set is constructed and therefore
    known exactly, so anything below 1.0 is a defect and not a tolerance.
  RESULT (fixtures, 2026-09-08): PASS, exit 0
    expected  5: APPA/A-9.32.3.8, B/9/9.32.3.8/(1), B/9/9.32.3.8/(1)/(c),
                 B/9/9.32.3.9/(1), B/9/table/9.32.3.1
    reported  5: identical set
    layout-only (correctly excluded): 11 of 15 nodes
    precision 1.0000   recall 1.0000
    derived-only nodes correctly silent: B/9/9.32.3.8, B/9/9.32.3.9
    amendment events 3 of 3 expected
  EVIDENCE: fixture-scope only; `automatic-evidence=v1` digest owed as above.
  CONTROL: proposed/MAINT/check35_MAINT_control.py — both entries read `ok`.
  NOTE: precision is the load-bearing half. The amended fixture is repaginated
    end to end, so 11 of its 15 nodes differ in layout and not in substance. A
    diff that does not project layout away reports all 15, scores recall 1.0,
    and is useless. A gate written on recall alone would have been green for
    exactly the tool this track exists to avoid shipping — and that is not
    hypothetical: the first revision of `substance()` had the sense of
    `LAYOUT_FIELDS` inverted and reported 14 of 15 nodes modified. The fixture
    caught it before the tool ever saw a real edition.
  NOTE: `B/9/9.32.3.9` loses a child when `B/9/9.32.3.9/(1)` is revoked, so its
    `children` list changes. It must not be reported: `children` is derivable
    from `parent`, and diffing both reports one fact two ways (R6). Asserted.

## H10 control (R1, R2)

M2 reports a ratio, so it is void without a mutation that drives it below its
floor. M1 does not report a ratio; that is stated above rather than papered over
with an invented one.

    python3 proposed/MAINT/check35_MAINT_control.py

    control                         untouched   mutated  verdict
    check45_diff M2 precision          exit 0    exit 1  ok
    check45_diff M2 recall             exit 0    exit 1  ok
    RESULT: PASS

Both directions, per the contract: untouched must exit 0, mutated must exit
non-zero. Two mutations, because M2 can be failed from either side.

  m_diff_layout_blind  empties `LAYOUT_FIELDS` and `LAYOUT_TOKEN_KEYS` in a copy
                       of the tool, so the repagination re-enters the projection
                       and all 15 nodes are reported. Precision collapses;
                       recall does not. This is the one that matters.
  m_diff_text_blind    removes `body` from the projection, so the reworded note
                       stops registering. Recall collapses.

Both mutate **the mechanism** — a copy of `tools/diff_editions.py` — and neither
touches `tools/fixtures/make_fixtures.py` or `seed.json`, which are the ground
truth the check scores against (R2). The fixtures are regenerated by the shipped
maker in both runs, so the ground truth is byte-identical between them by
construction. Weakening the seed manifest instead would shrink both sides of the
ratio and leave precision and recall at 1.0 — check33's tautology one level up,
and a mistake this project has already made once.

The control is staged, not installed: `harden/checks/check35_controls.py` is
protected. `python3 proposed/MAINT/check35_MAINT_control.py --promotion` prints
the exact edit, including the `maint` scope branch `run_subprocess_controls()`
needs; without that branch the rows fall through to `_materialise()` and report
NEVER PASSES with exit 2, which is a cwd error and not a check failure.

## Staged, then promoted

    proposed/MAINT/GATES-MAINT.md            -> gates/GATES-MAINT.md
    proposed/MAINT/check45_diff.py           -> harden/checks/check45_diff.py
    proposed/MAINT/check35_MAINT_control.py  -> harden/checks/check35_controls.py   (MERGE, not replace)

At real paths already, because they are not protected:

    tools/diff_editions.py
    tools/fixtures/make_fixtures.py

---
Unofficial derived work. Current to 2025-01-16 (through O. Reg. 5/25). Not the official Building Code Compendium.
© King's Printer for Ontario, 2024. Reproduced with permission.
