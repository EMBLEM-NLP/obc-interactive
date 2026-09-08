#!/usr/bin/env python3
"""
schedule.py - what can start now, from tracks.yaml.

    python3 schedule.py                 # ready / blocked / critical path
    python3 schedule.py --graph         # dependency edges, for a DOT tool
    python3 schedule.py --check         # exit 1 if the DAG is inconsistent

Two effort fields, and only one of them is allowed to be a number:

  human_effort:  typed, and always was. What a person was guessed to need.
  agent_effort:  `unmeasured` until a completed dispatch says otherwise. R9 -
                 documentation is measured, not typed - applied to this
                 project's own schedule, which is the one number nobody had
                 applied it to. --check refuses any agent_effort that does not
                 carry the word "measured".

The status field in tracks.yaml is authoritative for `done`. Everything else -
ready, blocked, and the reason - is DERIVED here, never typed. A track typed as
`ready` whose dependency is not `done` is reported as a DAG error, because a
status that disagrees with the graph is the same class of defect as a doc that
disagrees with its artifact.
"""
import argparse
import os
import re
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


def weeks(s):
    """'3 days' -> 0.6; '2 weeks' -> 2; '4 weeks+' -> 4; '3-5 days' -> 1.0.

    A range takes its UPPER bound. The previous version stripped every
    non-digit from the first token, so "3-5 days" became the string "35" and
    then 35 days = 7.0 weeks. That one hyphen contributed 6.4 of the "~17
    weeks" this function reported for the critical path, against a declared
    total of 10.2 - and the 17 was quoted in the README, the audits and the
    handoff as if it measured something.

    An unparseable string now raises. Silently defaulting to one week is how a
    typo becomes a schedule.
    """
    raw = str(s).strip().lower()
    nums = [float(x) for x in re.findall(r"\d+(?:\.\d+)?", raw)]
    if not nums:
        raise ValueError(f"effort {s!r} carries no number")
    n = max(nums)
    if "day" in raw:
        return n / 5
    if "week" in raw:
        return n
    if "month" in raw:
        return n * 4.33
    raise ValueError(f"effort {s!r} names no unit (day/week/month)")


def critical_path(tracks, field="human_effort"):
    """Longest chain by declared effort, in weeks, from any ready track to the
    end."""
    def w(tid):
        return weeks(tracks[tid].get(field) or "1 week")
    memo = {}
    def longest(tid):
        if tid in memo:
            return memo[tid]
        t = tracks[tid]
        succ = [k for k, v in tracks.items() if tid in (v.get("depends_on") or [])]
        best = (w(tid), [tid])
        for s in succ:
            ww, path = longest(s)
            if w(tid) + ww > best[0]:
                best = (w(tid) + ww, [tid] + path)
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

    # R9 applied to the schedule itself. `agent_effort` may read `unmeasured`,
    # or a duration that says where the measurement came from. It may never be
    # a bare guess, because a bare guess is exactly what "~17 weeks" was.
    effort_errors = []
    for tid, t in tracks.items():
        if t.get("status") == "done":
            continue
        ae = str(t.get("agent_effort", "")).strip()
        if not ae:
            effort_errors.append(f"{tid}: no agent_effort field")
        elif ae != "unmeasured" and "measured" not in ae.lower():
            effort_errors.append(
                f"{tid}: agent_effort {ae!r} is typed, not measured — say "
                f"'unmeasured', or cite the dispatch it was measured from (R9)")
        try:
            weeks(t.get("human_effort") or "1 week")
        except ValueError as e:
            effort_errors.append(f"{tid}: {e}")

    if a.check:
        for k, (_, why) in errors.items():
            print(f"DAG ERROR {k}: {why}")
        for e in effort_errors:
            print(f"EFFORT ERROR {e}")
        bad = len(errors) + len(effort_errors)
        print("RESULT:", "PASS" if not bad else f"FAIL {bad} inconsistencies")
        sys.exit(1 if bad else 0)

    order = ["done", "ready", "blocked", "conditional", "ERROR"]
    for st in order:
        rows = [(k, why) for k, (s, why) in d.items() if s == st]
        if not rows:
            continue
        print(f"\n{st.upper()} ({len(rows)})")
        for k, why in rows:
            t = tracks[k]
            eff = t.get("human_effort", "")
            par = t.get("parallel_with")
            line = f"  {k:<8} {t['title'][:52]:<52} {eff:<10}"
            if why:
                line += f"  [{why}]"
            if st == "ready" and par:
                line += f"  ∥ {','.join(par)}"
            if t.get("human_gate") and t["human_gate"] != "none":
                line += f"\n           ↳ human gate: {t['human_gate']}"
            print(line)

    w, path = critical_path(tracks, "human_effort")
    print(f"\nCRITICAL PATH, human_effort (TYPED, never measured)  ~{w:.0f} weeks:"
          f"\n  {' → '.join(path)}")

    # The agent path is refused rather than guessed. Printing a smaller made-up
    # number in place of a larger made-up number is not an improvement.
    unmeasured = [t for t in path if str(tracks[t].get("agent_effort")) == "unmeasured"]
    if unmeasured:
        print(f"\nCRITICAL PATH, agent_effort  UNMEASURED"
              f"\n  {len(unmeasured)} of {len(path)} tracks on this path have never been dispatched:"
              f" {', '.join(unmeasured)}."
              f"\n  Measure one track end to end, write its wall-clock into agent_effort,"
              f"\n  then this line reports a number. R9: measured, not typed.")
    else:
        aw, apath = critical_path(tracks, "agent_effort")
        print(f"\nCRITICAL PATH, agent_effort (MEASURED)  ~{aw:.1f} weeks:"
              f"\n  {' → '.join(apath)}")

    gates = [(k, tracks[k]["human_gate"]) for k in tracks
             if tracks[k].get("status") != "done"
             and tracks[k].get("human_gate") not in (None, "none")]
    if gates:
        print(f"\nHUMAN GATES ({len(gates)}) — no agent shortens these")
        for k, g in gates:
            print(f"  {k:<8} {g}")

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
