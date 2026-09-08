#!/usr/bin/env python3
"""
check35_controls.py - H10. Every ratio-reporting check must be falsifiable.

The problem this exists to prevent
----------------------------------
Gate H4 requires a negative control for every *absence* assertion: a detector
that reports zero because it is broken looks identical to one that reports zero
because the thing is absent.

`check33_completeness.py` was not an absence assertion. It was a *ratio*, and
it was computed like this:

    dependencies(nid) -> refs | terms
    bundle(nid)       -> {nid} | descendants | ancestors | refs | terms
    carried            = len(dep & bundle(nid)) / len(dep)

`bundle` unions in the very set it is measured against, so the ratio is 1.0 for
every node in the corpus. Measured directly: 11680/11680 = 100.0000%, zero
articles below threshold. The `< 0.99` condition could never fire. It passed
its gate for the same reason a thermometer taped to its own reading passes.

H4 did not catch it because a ratio is not an absence. H5's metamorphic checks
did not catch it because the metric is invariant under every transformation
that leaves the graph consistent - which is exactly what a tautology is.

The rule
--------
Every check that reports a ratio registers a mutation that MUST drive that
ratio below its floor. If the mutation does not break the check, the check is
not measuring what it claims and the gate is void.

This is deliberately cheap. Each mutation below is a few lines. That is the
point: the reason tautological metrics survive is not that controls are
expensive, it is that nobody is required to write one.

    python3 check35_controls.py --db obc-mod.sqlite
"""

import argparse
import gzip
import json
import os
import random
import shutil
import sqlite3
import subprocess
import sys
import tempfile

# This check lives at harden/checks/ but needs retrieval/lib/ (for
# obc_context) and retrieval/checks/ (for check33b_completeness's
# dependencies()/bundle_ids()). Same class of bug as check33b's fix above:
# the original pack was flat, the real repo is not.
_HERE = os.path.dirname(os.path.abspath(__file__))
_PKG = os.path.join(_HERE, "..", "..")
sys.path.insert(0, os.path.join(_PKG, "retrieval", "lib"))
sys.path.insert(0, os.path.join(_PKG, "retrieval", "checks"))
sys.path.insert(0, os.path.join(_PKG, "retrieval"))  # stage18_definitions,
                                                      # stage20_modality live here


# --------------------------------------------------------------------------
# mutations
# --------------------------------------------------------------------------

def mut_no_expansion(_):
    """Parameter mutation: hops=0. C1 must collapse, because nothing is
    expanded - while `dep` is unchanged.

    Deleting the `ref` table would NOT work, and the first version of this
    file made exactly that mistake: `dependencies()` reads `ref`, so deleting
    it shrinks the numerator and denominator together and the ratio stays at
    100%. A mutation must target the MECHANISM under test, never the ground
    truth the mechanism is scored against. That is the same error as check33,
    one level up."""
    return "expansion disabled (hops=0)"


def mut_starve_budget(_):
    """Parameter mutation: budget=200. C2 must collapse."""
    return "budget starved to 200 tokens"


def mut_drop_term_resolved(path):
    """Data mutation on the mechanism, not the truth: remove the split
    definitions and every definition reverts to a ~17 KB blob. C3 must
    collapse. `dep` is untouched, because it is computed from `term`."""
    c = sqlite3.connect(path)
    c.execute("DROP TABLE IF EXISTS term_resolved")
    c.commit(); c.close()
    return "term_resolved dropped (definitions revert to blobs)"


def mut_ablate_prohibition(path):
    """Rule ablation: reclassify with the 'shall not' rule removed. Every
    prohibition should then be absorbed by the 'shall' rule and the
    prohibition share must collapse toward zero."""
    import stage20_modality as st
    c = sqlite3.connect(path)
    c.row_factory = sqlite3.Row
    rules = [r for r in st.RULES if r[0] != "prohibition"]
    for r in c.execute(
            f"""SELECT id, body FROM node WHERE type IN {st.LEAF}
                AND body IS NOT NULL AND TRIM(body) != ''""").fetchall():
        m = "statement"
        for name, rx in rules:
            if rx.search(r["body"]):
                m = name
                break
        c.execute("UPDATE node SET modality=? WHERE id=?", (m, r["id"]))
    c.commit(); c.close()
    return "prohibition rule ablated from the classifier"


# --------------------------------------------------------------------------
# metrics under test
# --------------------------------------------------------------------------

def metric_bundle(path, budget=8000, hops=1):
    """C1/C2/C3 over a fixed sample of articles."""
    from obc_context import connect, build_bundle
    from check33b_completeness import dependencies, bundle_ids
    db = connect(path)
    split = db.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='term_resolved'"
    ).fetchone() is not None
    arts = [r[0] for r in db.execute(
        "SELECT id FROM node WHERE type='article' ORDER BY id LIMIT 400")]
    rn = rd = dn = dd = un = ud = 0
    for nid in arts:
        refs, terms = dependencies(db, nid)
        dep = refs | terms
        if not dep:
            continue
        b = build_bundle(db, nid, hops=hops, budget=None)
        if b["hub"]:
            continue
        resolved = set()
        if split:
            resolved = {r[0] for r in db.execute(
                "SELECT DISTINCT dst FROM term_resolved WHERE src IN "
                "(SELECT descendant FROM closure WHERE ancestor=?)", (nid,))}
        reach = bundle_ids(b)
        got = dep & reach
        if split:
            got |= {d for d in dep if d in terms and resolved & reach}
        rn += len(got); rd += len(dep)
        bt = build_bundle(db, nid, hops=hops, budget=budget)
        deliv = bundle_ids(bt)
        gotd = dep & deliv
        if split:
            gotd |= {d for d in dep if d in terms and resolved & deliv}
        dn += len(gotd); dd += len(dep)
        for t in bt["terms"]:
            ud += 1
            un += len(t.get("text") or "") <= 1500
    return {"C1": rn / max(1, rd), "C2": dn / max(1, dd), "C3": un / max(1, ud)}


def metric_modality(path):
    c = sqlite3.connect(path)
    tot = c.execute("SELECT COUNT(*) FROM node WHERE modality IS NOT NULL").fetchone()[0]
    if not tot:
        return {"prohibition_share": 0.0}
    n = c.execute("SELECT COUNT(*) FROM node WHERE modality='prohibition'").fetchone()[0]
    return {"prohibition_share": n / tot}


# --------------------------------------------------------------------------
# registry
#   gate, metric key, floor, metric fn, mutation fn, kwargs applied ONLY to
#   the mutated run. Parameter mutations pass kwargs; data mutations copy the
#   database. Either way `real` is always measured at defaults.
# --------------------------------------------------------------------------

REGISTRY = [
    ("R4a reachability", "C1", 0.99, metric_bundle, mut_no_expansion, {"hops": 0}),
    ("R4b delivery",     "C2", 0.95, metric_bundle, mut_starve_budget, {"budget": 200}),
    ("R4c usability",    "C3", 0.99, metric_bundle, mut_drop_term_resolved, None),
    ("R8 modality",      "prohibition_share", 0.02, metric_modality,
     mut_ablate_prohibition, None),
]


# ==========================================================================
# Part 2 - the pre-existing ratio checks, controlled as black boxes.
#
# The audit found 9 of 57 checks report a ratio and none had a control.
# Each entry below runs the SHIPPED check script itself - not a reimplementation
# of its metric, which would test my copy rather than the check (check33's
# error, one level up) - twice:
#
#   1. on an untouched copy of its working set  -> must exit 0
#   2. on a copy with ONE input mutated          -> must exit non-zero
#
# Both directions are required. A check that always fails passes a
# mutation-only test; a check that never fails passes an untouched-only test.
#
# Every mutation targets the pipeline output the check scores (the mechanism),
# never the ground truth it scores against. Blanking inventory.jsonl.gz would
# shrink both sides of check4's ratio and leave it green.
#
# Working sets come from verify/data/{v1,v2}, materialised the way
# verify/verify.sh does. No source PDF, no external gate runner needed.
# ==========================================================================

VERIFY = os.path.join(_PKG, "verify")
PDFDIR = os.path.join(_PKG, "pdf")


def _materialise(scope, tmp):
    """Copy verify/<scope>/ into tmp and populate its out/ from verify/data,
    exactly as verify.sh's link() does but with real copies so a mutation
    cannot leak back into the shipped data."""
    dst = os.path.join(tmp, scope)
    shutil.copytree(os.path.join(VERIFY, scope), dst, symlinks=False,
                    ignore=shutil.ignore_patterns("out", "__pycache__", ".unlazy"))
    out = os.path.join(dst, "out")
    os.makedirs(out, exist_ok=True)
    vol = "v1" if scope == "volume1" else "v2"
    for f in os.listdir(os.path.join(VERIFY, "data", vol)):
        shutil.copy(os.path.join(VERIFY, "data", vol, f), os.path.join(out, f))
    if scope == "volume2":
        shutil.copy(os.path.join(VERIFY, "data", "v2", "docgraph-merged.jsonl.gz"),
                    os.path.join(out, "docgraph.jsonl.gz"))
    for name, src in (("301880_built.pdf", "301880_built_from_model.pdf"),
                      ("301881_built.pdf", "301881_built_from_model.pdf")):
        p = os.path.join(PDFDIR, src)
        if os.path.exists(p):
            os.symlink(p, os.path.join(out, name))   # read-only, never mutated
    return dst


def _edit_jsonl_gz(path, fn):
    rows = [json.loads(l) for l in gzip.open(path, "rt")]
    with gzip.open(path, "wt") as f:
        for r in rows:
            f.write(json.dumps(fn(r)) + "\n")


def _exit(cwd, check, args=(), env=None):
    r = subprocess.run([sys.executable, os.path.join("checks", check), *args],
                       cwd=cwd, capture_output=True, text=True, timeout=600,
                       env={**os.environ, **(env or {})})
    return r.returncode, (r.stdout.strip().splitlines() or [""])[-1]


# ---- mutations: each edits one output file inside the copied working set ----

def m_capture(d):
    rng = random.Random(4)
    def f(r):
        if not r.get("_meta") and r.get("type") == "sentence" and r.get("text") and rng.random() < 0.5:
            r["text"] = []
        return r
    _edit_jsonl_gz(os.path.join(d, "out", "docgraph.jsonl.gz"), f)
    return "half the sentences' captured text blanked; inventory untouched"


def m_tables(d):
    rng = random.Random(5)
    def f(r):
        if not r.get("_meta") and rng.random() < 0.6:
            r["parts"] = []          # cells gone, designator kept -> placed ratio falls
        return r
    _edit_jsonl_gz(os.path.join(d, "out", "tables.jsonl.gz"), f)
    return "cell content stripped from 60% of table runs; designators kept"


def m_refs(d):
    """check7 gates on bad <= 4 in a 200-ref spot check of number/citation
    consistency. Point a third of refs at nodes whose number contradicts the
    citation - stage7's OUTPUT, not the citation text it read."""
    path = os.path.join(d, "out", "docgraph.jsonl.gz")
    rows = [json.loads(l) for l in gzip.open(path, "rt")]
    ids = [r["id"] for r in rows if not r.get("_meta") and r.get("type") == "article"]
    rng = random.Random(7)
    for r in rows:
        for ref in r.get("refs", []) or []:
            if ref.get("target") and rng.random() < 0.35:
                ref["target"] = rng.choice(ids)
    with gzip.open(path, "wt") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")
    return "35% of resolved refs re-pointed at unrelated articles"


def m_index(d):
    rng = random.Random(10)
    def f(r):
        if not r.get("_meta") and str(r.get("type", "")).startswith("index"):
            for ref in r.get("refs", []) or []:
                if ref.get("target") and rng.random() < 0.4:
                    ref["target"] = None
        return r
    _edit_jsonl_gz(os.path.join(d, "out", "docgraph.jsonl.gz"), f)
    return "40% of index-entry citation targets nulled"


def m_crossvol(d):
    rng = random.Random(14)
    def f(r):
        if not r.get("_meta"):
            for ref in r.get("refs", []) or []:
                if ref.get("kind") in ("note", "supp") and ref.get("target") and rng.random() < 0.3:
                    ref["target"] = None
        return r
    _edit_jsonl_gz(os.path.join(d, "out", "docgraph-merged.jsonl.gz"), f)
    return "30% of note/supplementary cross-volume targets nulled"


def m_graph_blank(d):
    """check24 MR1, per-page after today's fix. Blank every sentence in a copy
    of the merged graph and point OBC_GRAPH at it."""
    src = os.path.join(_PKG, "model", "docgraph-merged.jsonl.gz")
    dst = os.path.join(d, "graph.jsonl.gz")
    with gzip.open(dst, "wt") as out:
        for l in gzip.open(src, "rt"):
            r = json.loads(l)
            if not r.get("_meta") and r.get("type") == "sentence":
                r["text"] = []
            out.write(json.dumps(r) + "\n")
    return "all sentences blanked in a copy of the merged graph (OBC_GRAPH)"


def m_evalset(d):
    """check31 gates on lexical share >= 0.5 and size >= 40. Replace the text
    of 70% of questions with words that overlap nothing; targets and count
    are preserved so only the ratio can be what fails."""
    p = os.path.join(d, "evalset.json")
    es = json.load(open(p))
    rng = random.Random(31)
    for q in es["questions"]:
        if rng.random() < 0.7:
            q["q"] = "zyxqv wvutsr qpnmlk jhgfdcb"
    json.dump(es, open(p, "w"), indent=1)
    return "70% of question texts replaced with non-overlapping tokens"


# ---- registry ----
#   name, scope dir under verify/ (or 'retrieval'), check script, mutation, args, env
SUBPROCESS_CONTROLS = [
    ("check4b_capture",  "volume1",   "check4b_capture.py",  m_capture,  (), {}),
    ("check4b_capture v2","volume2",   "check4b_capture.py",  m_capture,  (), {}),
    ("check5_tables",    "volume1",   "check5_tables.py",    m_tables,   (), {}),
    ("check7_refs",      "volume1",   "check7_refs.py",      m_refs,     (), {}),
    ("check10_index",    "volume1",   "check10_index.py",    m_index,    (), {}),
    ("check14_crossvol", "volume2",   "check14_crossvol.py", m_crossvol, (), {}),
    ("check24_metamorph", "harden",    "check24_metamorphic.py", m_graph_blank, (), {}),
    ("check31_evalset",  "retrieval", "check31_evalset.py",  m_evalset,  (),
        {"OBC_DB": os.path.join(_PKG, "emitters", "obc-vec.sqlite")}),
]

# Ratio checks that CANNOT be controlled from the bag, and why. Enumerated so
# the set cannot grow silently; each needs a portability fix, not a control.
# Ratio checks proven vacuous by this registry and superseded. Kept so the
# record of WHY they were replaced travels with the replacement.
SUPERSEDED = {
    "check4_capture":  "corpus-wide character multiset; 71% surplus from non-body nodes. "
                       "Blanking 100% of sentence text left orphaned at 0.140% < 0.5%. "
                       "Replaced by check4b_capture (per-page).",
    "check31_evalset (original gate)": "ratio computed from the hand-written `kind` label, not the "
                       "overlap the check itself measured. Replacing 70% of question text "
                       "left it at 82%. Fixed in place to gate on measured overlap.",
    "check33_completeness": "bundle() unioned in the set it was scored against; 100.0000% "
                       "identically. Replaced by check33b.",
}

UNCONTROLLABLE = {
    "check0_coverage":    "reads the Crown-copyright source PDF, which is fetch-only by design",
}


def run_subprocess_controls():
    print()
    print(f"{'check':<20}{'untouched':>11}{'mutated':>10}  verdict")
    print("-" * 62)
    fails = []
    for name, scope, check, mutate, args, env in SUBPROCESS_CONTROLS:
        tmp = tempfile.mkdtemp()
        try:
            if scope == "harden":
                # run the real check in place; only the graph it reads changes
                d = os.path.join(_PKG, "harden")   # _exit prepends checks/
                rc_ok, _ = _exit(d, check, args, env)
                gdir = os.path.join(tmp, "g"); os.makedirs(gdir)
                note = mutate(gdir)
                rc_mut, last = _exit(d, check, args,
                                     {**env, "OBC_GRAPH": os.path.join(gdir, "graph.jsonl.gz")})
            elif scope == "retrieval":
                d = os.path.join(tmp, "retrieval")
                shutil.copytree(os.path.join(_PKG, "retrieval"), d,
                                ignore=shutil.ignore_patterns("__pycache__"))
                env = {**env, "OBC_EVAL": os.path.join(d, "evalset.json")}
            else:
                d = _materialise(scope, tmp)
            if scope != "harden":
                rc_ok, _ = _exit(d, check, args, env)
                note = mutate(d)
                rc_mut, last = _exit(d, check, args, env)
        except Exception as e:
            rc_ok, rc_mut, note, last = -1, -1, f"raised {type(e).__name__}: {e}", ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
        ok = rc_ok == 0 and rc_mut != 0
        verdict = ("ok" if ok else
                   "NEVER PASSES" if rc_ok != 0 else "NEVER FAILS")
        print(f"{name:<20}{('exit '+str(rc_ok)):>11}{('exit '+str(rc_mut)):>10}  {verdict}")
        print(f"{'':<20}mutation: {note}")
        if not ok:
            fails.append(f"{name}: untouched exit {rc_ok}, mutated exit {rc_mut}")
    print()
    print("proven vacuous and superseded (enumerated):")
    for k, why in SUPERSEDED.items():
        print(f"   {k:<20} {why[:88]}")
    print()
    print("uncontrollable from the bag (need a portability fix, enumerated):")
    for k, why in UNCONTROLLABLE.items():
        print(f"   {k:<20} {why}")
    return fails


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default="obc-mod.sqlite")
    a = ap.parse_args()

    print(f"{'gate':<20}{'floor':>7}{'real':>9}{'mutated':>10}  verdict")
    print("-" * 62)
    fails = []
    for gate, key, floor, metric, mutate, kw in REGISTRY:
        real = metric(a.db)[key]          # always at defaults
        if kw is not None:                # parameter mutation
            note = mutate(None)
            bad = metric(a.db, **kw)[key]
        else:                             # data mutation on a copy
            tmp = tempfile.mkdtemp()
            path = os.path.join(tmp, "mutated.sqlite")
            shutil.copy(a.db, path)
            note = mutate(path)
            bad = metric(path)[key]
            shutil.rmtree(tmp, ignore_errors=True)

        ok = bad < floor <= real
        verdict = ("ok" if ok else
                   "METRIC NEVER FAILS" if bad >= floor else "real below floor")
        print(f"{gate:<20}{floor:>7.0%}{real:>9.1%}{bad:>10.1%}  {verdict}")
        print(f"{'':<20}mutation: {note}")
        if not ok:
            fails.append(f"{gate}: real {real:.1%}, mutated {bad:.1%}, floor {floor:.0%}")

    fails += run_subprocess_controls()
    print("\nEvery ratio above must drop below its floor under mutation.")
    print("A gate whose metric survives its own mutation is void, however green.")
    print("\nRESULT:", "PASS" if not fails else "FAIL " + "; ".join(fails))
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
