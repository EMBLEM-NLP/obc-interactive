#!/usr/bin/env python3
"""
schedule.py - what can start now, from tracks.yaml.

    python3 schedule.py                 # ready / blocked / critical path
    python3 schedule.py --graph         # dependency edges, for a DOT tool
    python3 schedule.py --check         # exit 1 if the DAG is inconsistent

The status field in tracks.yaml is authoritative for `done`. Everything else -
ready, blocked, and the reason - is DERIVED here, never typed. A track typed as
`ready` whose dependency is not `done` is reported as a DAG error, because a
status that disagrees with the graph is the same class of defect as a doc that
disagrees with its artifact.
"""
import argparse
import os
import sys

try:
    import yaml
except ImportError:
    sys.exit("pip install pyyaml --break-system-packages")

HERE = os.path.dirname(os.path.abspath(__file__))


def load(path=None):
    path = path or os.path.join(HERE, "tracks.yaml")
    return yaml.safe_load(open(path))


def derive(tracks):
    """Return {id: (derived_status, reason)}."""
    out = {}
    for tid, t in tracks.items():
        typed = t.get("status", "blocked")
        deps = t.get("depends_on", []) or []
        unknown = [d for d in deps if d not in tracks]
        if unknown:
            out[tid] = ("ERROR", f"depends on unknown track(s) {unknown}")
            continue
        not_done = [d for d in deps if tracks[d].get("status") != "done"]
        if typed == "done":
            if not_done:
                out[tid] = ("ERROR", f"typed done but depends on unfinished {not_done}")
            else:
                out[tid] = ("done", "")
        elif typed == "conditional":
            out[tid] = ("conditional", t.get("condition", "").strip().split("\n")[0][:80])
        elif not_done:
            if typed == "ready":
                out[tid] = ("ERROR", f"typed ready but {not_done} not done")
            else:
                out[tid] = ("blocked", f"waiting on {', '.join(not_done)}")
        else:
            out[tid] = ("ready", "")
    return out


def critical_path(tracks):
    """Longest chain by declared effort, in weeks, from any ready track to the
    end. Effort strings like '2 weeks', '3 days', '4 weeks+' are parsed
    loosely; unparseable -> 1 week."""
    def weeks(s):
        s = str(s or "1 week").lower()
        n = float("".join(c for c in s.split()[0] if c.isdigit() or c == ".") or 1)
        return n / 5 if "day" in s else n
    memo = {}
    def longest(tid):
        if tid in memo:
            return memo[tid]
        t = tracks[tid]
        succ = [k for k, v in tracks.items() if tid in (v.get("depends_on") or [])]
        best = (weeks(t.get("effort")), [tid])
        for s in succ:
            w, path = longest(s)
            if weeks(t.get("effort")) + w > best[0]:
                best = (weeks(t.get("effort")) + w, [tid] + path)
        memo[tid] = best
        return best
    starts = [k for k, v in tracks.items() if not (v.get("depends_on") or [])
              or all(tracks[d].get("status") == "done" for d in v["depends_on"])]
    starts = [k for k in starts if tracks[k].get("status") != "done"]
    if not starts:
        return 0, []
    return max((longest(s) for s in starts), key=lambda x: x[0])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--file")
    ap.add_argument("--graph", action="store_true")
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()

    doc = load(a.file)
    tracks = doc["tracks"]
    d = derive(tracks)

    if a.graph:
        print("digraph tracks {")
        for tid, t in tracks.items():
            for dep in t.get("depends_on") or []:
                print(f'  "{dep}" -> "{tid}";')
        print("}")
        return

    errors = {k: v for k, v in d.items() if v[0] == "ERROR"}
    if a.check:
        for k, (_, why) in errors.items():
            print(f"DAG ERROR {k}: {why}")
        print("RESULT:", "PASS" if not errors else f"FAIL {len(errors)} inconsistencies")
        sys.exit(1 if errors else 0)

    order = ["done", "ready", "blocked", "conditional", "ERROR"]
    for st in order:
        rows = [(k, why) for k, (s, why) in d.items() if s == st]
        if not rows:
            continue
        print(f"\n{st.upper()} ({len(rows)})")
        for k, why in rows:
            t = tracks[k]
            eff = t.get("effort", "")
            par = t.get("parallel_with")
            line = f"  {k:<8} {t['title'][:52]:<52} {eff:<10}"
            if why:
                line += f"  [{why}]"
            if st == "ready" and par:
                line += f"  ∥ {','.join(par)}"
            print(line)

    w, path = critical_path(tracks)
    print(f"\nCRITICAL PATH  (~{w:.0f} weeks): {' → '.join(path)}")

    dec = doc.get("decisions_pending") or []
    if dec:
        print(f"\nDECISIONS PENDING ({len(dec)}) — require a human, block by assumption is forbidden")
        for x in dec:
            b = x.get("blocks") or x.get("affects") or []
            print(f"  {x['id']}: {x['question']}  → {', '.join(map(str, b)) or '(none)'}")
    if errors:
        print(f"\n{len(errors)} DAG ERROR(S) — run --check")
        sys.exit(1)


if __name__ == "__main__":
    main()
