#!/usr/bin/env python3
"""
check46_dagschema.py - DAG1. The DAG still has the shape the orchestration needs.

Why this exists
---------------
`tracks.yaml` is deliberately NOT in `check41`'s PROTECTED set, because every
track updates its own status there and must be able to. That exemption is
correct and it leaves the file carrying the whole dependency graph as the one
piece of orchestration nothing guards.

On 2026-09-08 that became concrete. `isolation: worktree` branched both agents
of wave 1 from the repository's default branch rather than the working branch,
so each held a `tracks.yaml` predating commit 9380139 - the pre-orchestration
schema, with `effort:` and none of `human_effort`, `agent_effort`, `human_gate`,
`serialises_on` or `promotes:`. Merging either worktree would have reverted
those fields for all fifteen tracks through a clean merge with no conflict, and
`check41` would have reported PASS throughout, correctly, because no protected
file changed.

Why this duplicates schedule.py rather than importing it
---------------------------------------------------------
`orchestration/schedule.py --check` already asserts most of what is below, and
this project's rule is one definition with many consumers - `PROTECTED` in
check41 has four. This file is a deliberate exception, and the reason is the
threat model rather than taste.

`schedule.py` is unprotected too. A stale merge reverts the checker and the
thing it checks IN THE SAME COMMIT, and the reverted checker then passes over
the reverted data. Redundancy is the mechanism here: this file lives under
`harden/checks/`, which is protected and compared to HEAD by gate E2, so a merge
that silently reverts the DAG cannot also silently revert its detector.

It follows that this check must be SELF-CONTAINED. It may not import
`schedule.py`, and it may not read anything from `orchestration/` other than the
YAML it is judging.

    python3 harden/checks/check46_dagschema.py
    python3 harden/checks/check46_dagschema.py --file <tracks.yaml>
    NEGATIVE=1 python3 harden/checks/check46_dagschema.py   # must FAIL
"""
import argparse
import os
import sys

try:
    import yaml
except ImportError:
    sys.exit("pip install pyyaml --break-system-packages")


def _root(start=None):
    d = os.path.dirname(os.path.abspath(start or __file__))
    for _ in range(8):
        if os.path.isfile(os.path.join(d, "orchestration", "tracks.yaml")):
            return d
        nd = os.path.dirname(d)
        if nd == d:
            break
        d = nd
    sys.exit("check46: cannot locate the package root")


PKG = _root()

# Every field the orchestration layer depends on, and the commit that introduced
# it. A track missing one of these is either new and incomplete, or a revert.
REQUIRED_OPEN = ["human_effort", "agent_effort", "human_gate"]
# Fields whose PRESENCE anywhere proves the schema is post-9380139. If not one
# track in the file has them, this is the old shape wholesale, not a partial edit.
SCHEMA_MARKERS = ["human_effort", "agent_effort", "human_gate", "promotes"]
RETIRED = ["effort"]          # renamed to human_effort in 9380139


def audit(path=None):
    doc = yaml.safe_load(open(path or os.path.join(PKG, "orchestration", "tracks.yaml")))
    tracks = doc.get("tracks") or {}
    out = []

    if not tracks:
        return [("S0", "-", "tracks.yaml declares no tracks")], 0

    # S1 - wholesale revert. The loudest case and the one wave 1 would have caused.
    if not any(any(k in t for k in SCHEMA_MARKERS) for t in tracks.values()):
        out.append(("S1", "-", "NO track carries any of "
                    f"{SCHEMA_MARKERS} - this is the pre-9380139 schema wholesale, "
                    "which is what a merge from a stale worktree produces"))

    n = 0
    for tid, t in tracks.items():
        if t.get("status") == "done":
            continue
        n += 1
        for k in REQUIRED_OPEN:
            if k not in t:
                out.append(("S2", tid, f"open track is missing `{k}:`"))
        for k in RETIRED:
            if k in t:
                out.append(("S3", tid, f"carries retired field `{k}:` "
                                       f"(renamed to human_effort in 9380139)"))
        ae = str(t.get("agent_effort", "")).strip()
        if ae and ae != "unmeasured" and "measured" not in ae.lower():
            out.append(("S4", tid, f"agent_effort {ae!r} is typed, not measured (R9)"))

    # S5 - the decisions block is what decision-guard protects; its absence here
    # would mean a revert took the four pending decisions with it.
    if not (doc.get("decisions_pending") or []):
        out.append(("S5", "-", "decisions_pending is absent or empty; DEC1-DEC4 "
                               "require a human and may not vanish through a merge"))
    return out, n


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--file")
    a = ap.parse_args()

    findings, n = audit(a.file)

    # NEGATIVE control (R1/R11). Both halves: the wholesale revert must be seen,
    # and a single missing field must be seen. A control that only tests the
    # loud case would pass over a partial revert, which is the likelier one.
    if os.environ.get("NEGATIVE") == "1":
        import copy, tempfile
        doc = yaml.safe_load(open(a.file or os.path.join(PKG, "orchestration", "tracks.yaml")))

        def probe(mutate, want):
            d = copy.deepcopy(doc)
            mutate(d)
            with tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False) as fh:
                yaml.safe_dump(d, fh); tmp = fh.name
            got, _ = audit(tmp)
            os.unlink(tmp)
            return [f for f in got if f[0] == want]

        def revert_all(d):
            for t in d["tracks"].values():
                for k in SCHEMA_MARKERS + ["serialises_on"]:
                    t.pop(k, None)
                t["effort"] = "2 weeks"

        def drop_one(d):
            victim = next(k for k, v in d["tracks"].items() if v.get("status") != "done")
            d["tracks"][victim].pop("agent_effort", None)

        whole = probe(revert_all, "S1")
        part = probe(drop_one, "S2")
        print(f"NEGATIVE control, wholesale revert to the old schema : {len(whole)} finding(s), need >= 1")
        print(f"NEGATIVE control, one open track loses agent_effort  : {len(part)} finding(s), need >= 1")
        ok = whole and part
        print("RESULT:", "PASS" if ok else "FAIL - this check cannot see a revert it exists to catch")
        sys.exit(0 if ok else 1)

    for code, tid, detail in findings:
        print(f"{code} {tid}: {detail}")
    print(f"\nexamined {n} open track(s); {len(findings)} finding(s)")
    print("RESULT:", "PASS" if not findings else f"FAIL {len(findings)}")
    sys.exit(1 if findings else 0)


if __name__ == "__main__":
    main()
