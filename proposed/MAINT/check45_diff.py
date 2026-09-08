#!/usr/bin/env python3
"""
check45_diff.py - M1 and M2 for the amendment diff pipeline.

STAGED, NOT INSTALLED. Its real path is `harden/checks/check45_diff.py`, which
matches `check41_machinery.PROTECTED` pattern `harden/checks/*` and the
`Write(harden/checks/**)` deny in `.claude/settings.json`. A track executor is
refused there by design, so it is written flat at `proposed/MAINT/` and promoted
by a human (PROTOCOL step 4a). `proposed/MAINT/check45_diff.py` tests
unprotected under BOTH the relative and the absolute spelling; the mirrored
layout `proposed/harden/checks/...` does not, because check41._candidates()
expands an absolute path into every suffix of itself.

M1  a diff of a graph against itself is empty, and is byte-identical run twice.
M2  a seeded amendment appears in the diff, and NOTHING ELSE DOES.

What these are measured on, and what they are not
-------------------------------------------------
On the synthetic fixtures built by tools/fixtures/make_fixtures.py. NOT on the
corpus. This clone has no derived data - check40_dataintegrity.py --quick
reports 29 of 29 declared files MISSING and exits 1 - so
model/docgraph-merged.jsonl.gz does not exist and two real editions cannot be
diffed here. **The corpus run is owed.** Passing this check says the tool
behaves correctly on 15 constructed nodes. It says nothing about 27,421 real
ones, and no reader of a green M1/M2 should infer otherwise.

Why M2 gates precision and not only recall
------------------------------------------
The amended fixture is repaginated end to end: every provenance page and bbox
and every text token's `p`/`b` differs, while four nodes and only four differ
in substance. A diff that does not project layout away reports all 15 nodes. It
scores recall 1.0 - it did find the amendment - and it is useless, because a
review queue containing everything is not a review queue. So M2 requires

    recall = 1.0   AND   precision = 1.0

The floor is 1.0 on both, not 0.95, because the expected set is constructed and
therefore known exactly. Anything below 1.0 is a defect, not a tolerance.

This is not hypothetical. The first revision of tools/diff_editions.py had the
sense of LAYOUT_FIELDS inverted - it added the layout fields into the projection
instead of excluding them - and reported 14 of 15 nodes modified. The fixture
caught it before the tool was ever run on a real edition.

The tool under test is named by OBC_DIFF_TOOL (R7), so the H10 control can point
this check at a mutated copy without touching the shipped one.

    python3 harden/checks/check45_diff.py
    python3 harden/checks/check45_diff.py --gate M1
    python3 harden/checks/check45_diff.py --gate M2
"""
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile


def _root(start=None):
    """Walk up to the package root, so this file works both staged at
    proposed/MAINT/ and promoted to harden/checks/."""
    d = os.path.dirname(os.path.abspath(start or __file__))
    for _ in range(8):
        if os.path.isfile(os.path.join(d, "orchestration", "tracks.yaml")):
            return d
        nd = os.path.dirname(d)
        if nd == d:
            break
        d = nd
    sys.exit("check45: cannot locate the package root "
             "(no orchestration/tracks.yaml above me)")


PKG = _root()
TOOL = os.environ.get("OBC_DIFF_TOOL", os.path.join(PKG, "tools", "diff_editions.py"))
MAKER = os.environ.get("OBC_FIXTURE_MAKER",
                       os.path.join(PKG, "tools", "fixtures", "make_fixtures.py"))


def _run(args):
    r = subprocess.run([sys.executable, *args], capture_output=True, text=True,
                       timeout=600)
    if r.returncode != 0:
        raise SystemExit(f"check45: {' '.join(map(str, args))} exited "
                         f"{r.returncode}\n{r.stderr.strip()}")
    return r.stdout


def build_fixtures(dst):
    _run([MAKER, "--out", dst])
    return (os.path.join(dst, "base.jsonl.gz"),
            os.path.join(dst, "amended.jsonl.gz"),
            json.load(open(os.path.join(dst, "seed.json"), encoding="utf-8")))


def diff(old, new, workdir, tag):
    out = os.path.join(workdir, f"diff-{tag}.json")
    _run([TOOL, old, new, "-o", out])
    with open(out, "rb") as fh:
        raw = fh.read()
    return json.loads(raw.decode("utf-8")), hashlib.sha256(raw).hexdigest()


def _sha(path):
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def gate_m1(work, fixtures):
    """A diff of a graph against itself is empty, and deterministic."""
    base, amended, _ = fixtures
    fails, notes = [], []

    for name, path in (("base", base), ("amended", amended)):
        r, _ = diff(path, path, work, f"self-{name}")
        s = r["summary"]
        nonzero = {k: v for k, v in s.items() if v}
        if nonzero:
            fails.append(f"M1: {name} diffed against itself is not empty: {nonzero}")
        if r["meta_changed"]:
            fails.append(f"M1: {name} self-diff reports meta keys changed: "
                         f"{r['meta_changed']}")
        notes.append(f"self-diff {name:<8} {s['changed_nodes']} changed, "
                     f"{s['layout_only']} layout-only, "
                     f"{s['amendment_events']} amendment events")

    # Determinism over the WHOLE report artifact, not a subset of its fields.
    # check20 excluded `meta` from its determinism digest and the only
    # nondeterminism in the build was in `meta` (R5).
    _, d1 = diff(base, amended, work, "det-1")
    _, d2 = diff(base, amended, work, "det-2")
    if d1 != d2:
        fails.append(f"M1: two runs of the same diff differ: {d1[:12]} vs {d2[:12]}")
    notes.append(f"report digest    {d1[:16]}  identical across two runs: {d1 == d2}")

    # The fixtures themselves must be byte-stable, or an M1 failure could not be
    # attributed to the tool.
    second = os.path.join(work, "fx2")
    b2, a2, _ = build_fixtures(second)
    for label, p, q in (("base", base, b2), ("amended", amended, a2)):
        if _sha(p) != _sha(q):
            fails.append(f"M1: fixture {label} is not byte-deterministic")
    notes.append(f"fixture digests  base {_sha(base)[:16]}  "
                 f"amended {_sha(amended)[:16]}  stable: "
                 f"{_sha(base) == _sha(b2) and _sha(amended) == _sha(a2)}")
    return fails, notes


def gate_m2(work, fixtures):
    """The seeded amendment appears, and nothing else does."""
    base, amended, seed = fixtures
    fails, notes = [], []

    r, _ = diff(base, amended, work, "seeded")
    reported = set(r["changed_nodes"])
    expected = set(seed["expected_changed"])

    tp = len(reported & expected)
    precision = tp / len(reported) if reported else (1.0 if not expected else 0.0)
    recall = tp / len(expected) if expected else 1.0

    notes.append(f"expected  {len(expected)}: {', '.join(sorted(expected))}")
    notes.append(f"reported  {len(reported)}: {', '.join(sorted(reported))}")
    notes.append(f"layout-only (correctly excluded): {r['summary']['layout_only']}")
    notes.append(f"precision {precision:.4f}   recall {recall:.4f}   floor 1.0 on both")

    if recall < 1.0:
        fails.append(f"M2: recall {recall:.4f} < 1.0; missed "
                     f"{sorted(expected - reported)}")
    if precision < 1.0:
        fails.append(f"M2: precision {precision:.4f} < 1.0; {len(reported - expected)} "
                     f"node(s) reported that did not change in substance: "
                     f"{sorted(reported - expected)[:8]}")

    # The three classes must match exactly, not merely in aggregate. An
    # aggregate that is right while its parts are wrong is R4's defect.
    for key, want in (("added", "expected_added"), ("removed", "expected_removed")):
        got = sorted(r[key])
        if got != sorted(seed[want]):
            fails.append(f"M2: {key} = {got}, expected {sorted(seed[want])}")
    got_mod = sorted(m["id"] for m in r["modified"])
    if got_mod != sorted(seed["expected_modified"]):
        fails.append(f"M2: modified = {got_mod}, "
                     f"expected {sorted(seed['expected_modified'])}")

    # Nodes whose only change is a derived one (a parent whose `children` list
    # changed because a child was revoked) must not surface.
    leaked = sorted(set(seed["must_not_be_reported"]) & reported)
    if leaked:
        fails.append(f"M2: derived-only change reported as substantive: {leaked}")
    notes.append(f"derived-only nodes correctly silent: "
                 f"{sorted(seed['must_not_be_reported'])}")

    n_ev = r["summary"]["amendment_events"]
    if n_ev != seed["expected_amendment_events"]:
        fails.append(f"M2: {n_ev} amendment events, expected "
                     f"{seed['expected_amendment_events']}")
    notes.append(f"amendment events {n_ev} of {seed['expected_amendment_events']} expected")
    return fails, notes


def main(argv=None):
    ap = argparse.ArgumentParser(description="M1/M2 for tools/diff_editions.py")
    ap.add_argument("--gate", choices=("M1", "M2", "all"), default="all")
    a = ap.parse_args(argv)

    for p in (TOOL, MAKER):
        if not os.path.isfile(p):
            sys.exit(f"check45: missing {p}")

    print(f"tool    {os.path.relpath(TOOL, PKG) if TOOL.startswith(PKG) else TOOL}")
    print(f"scope   synthetic fixtures, NOT the corpus; the corpus run is owed")
    print()

    work = tempfile.mkdtemp(prefix="check45-")
    fails = []
    try:
        fixtures = build_fixtures(os.path.join(work, "fx"))
        for gate, fn in (("M1", gate_m1), ("M2", gate_m2)):
            if a.gate not in (gate, "all"):
                continue
            f, notes = fn(work, fixtures)
            print(f"--- {gate} ---")
            for n in notes:
                print(f"   {n}")
            print(f"   {gate}: {'PASS' if not f else 'FAIL'}")
            print()
            fails += f
    finally:
        shutil.rmtree(work, ignore_errors=True)

    for f in fails:
        print(f"FAIL {f}")
    print(f"RESULT: {'PASS' if not fails else 'FAIL'}")
    return 0 if not fails else 1


if __name__ == "__main__":
    sys.exit(main())
