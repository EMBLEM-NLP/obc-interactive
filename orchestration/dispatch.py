#!/usr/bin/env python3
"""
dispatch.py - turn the DAG into waves. It PLANS; it never launches.

    python3 orchestration/dispatch.py            # the wave plan, readable
    python3 orchestration/dispatch.py --plan     # write orchestration/wave-plan.json
    python3 orchestration/dispatch.py --check    # exit 1 if the plan contradicts schedule.py
    python3 orchestration/dispatch.py --promote A4   # the exact commands for a human

Why it plans and does not launch
--------------------------------
Launching needs a harness. Planning needs `tracks.yaml`. Keeping them apart is
what lets this file be exercised on a clone with no data, no API key and no
subagent dispatch - which is the state every audit of this project has been
written from, and the state that made `.github/workflows/gates.yml` sit
unexecuted through ten runs. The orchestrator reads this plan and makes the
calls; if it disagrees with the plan, `--check` is the thing that says so.

What a wave is
--------------
A maximal set of tracks that may run concurrently. A track joins the current
wave when:

  1. `schedule.py` DERIVES it as ready - never the typed status (schedule.py's
     own rule: a status that disagrees with the graph is the defect);
  2. it shares no `serialises_on:` entry with a track already in the wave.
     Two tracks writing `emitters/obc.sqlite` in parallel produce a merge no
     one can review;
  3. its `human_gate:` is `none`. A track waiting on DEC1 or on a building
     official does not belong in a wave that is about to be dispatched - it
     belongs in front of the person who can answer.

Waves after the first are SPECULATIVE and marked so. They assume every track in
the wave before them completes, which is exactly the assumption a review gate
exists to test. Only wave 1 is dispatchable.

Human gate per wave
-------------------
Between waves a person reviews. This is not ceremony: worktrees do not isolate
filesystem writes (PROTOCOL R12), the promote step is a human step by
construction (R13), and three facts about how hooks behave under subagent
dispatch are still unverified. A wave boundary is where those get looked at.
"""
import argparse
import importlib.util
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.dirname(HERE)
OUT = os.path.join(HERE, "wave-plan.json")


def _schedule():
    """Import schedule.py rather than reimplementing derive(). One definition."""
    spec = importlib.util.spec_from_file_location(
        "schedule", os.path.join(HERE, "schedule.py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def _agent_for(tid, t):
    """Which agent spec executes this track. embed-track is B's second half and
    is never the first agent on a track (R8: one re-embed per batch, after all
    four items land), so it is named in `then` rather than `agent`."""
    if tid == "B":
        return "build-track", ["embed-track", "integrate-track", "verify-track"]
    return "build-track", ["integrate-track", "verify-track"]


def head_commit():
    """The commit a plan is planned against.

    This is the commit that last touched `tracks.yaml`, NOT HEAD, and the
    difference is the whole point. A plan is a function of the DAG, so it goes
    stale when the DAG moves and only then. Recording HEAD instead made --check
    fail immediately after every commit - including the commit that WROTE the
    plan, which moves HEAD past the value just recorded in it. That is a gate
    that cries wolf, and rev13 named the cost: one ignored just as thoroughly as
    one that never fires.

    A wave dispatched against a stale DAG is the real hazard - see
    proposed/ENFORCE/worktree-base.md, where both agents of wave 1 landed on the
    default branch instead of this one - and this catches exactly that.
    """
    r = subprocess.run(["git", "log", "-1", "--format=%H", "--",
                        "orchestration/tracks.yaml"], cwd=PKG, capture_output=True, text=True)
    return r.stdout.strip() if r.returncode == 0 else ""


def plan(tracks_path=None):
    sch = _schedule()
    doc = sch.load(tracks_path)
    tracks = doc["tracks"]

    waves, assumed_done, wave_no = [], set(), 0
    remaining = {k for k, v in tracks.items() if v.get("status") != "done"}

    while remaining:
        wave_no += 1
        # Re-derive readiness with the previous waves ASSUMED complete.
        view = {k: dict(v) for k, v in tracks.items()}
        for k in assumed_done:
            view[k]["status"] = "done"
        derived = sch.derive(view)

        wave, held, taken = [], [], set()
        for tid in sorted(remaining):
            t = tracks[tid]
            state, why = derived[tid]
            if state != "ready":
                continue
            gate = t.get("human_gate") or "none"
            if gate != "none":
                held.append({"track": tid, "reason": f"human gate — {gate}"})
                continue
            ser = set(t.get("serialises_on") or [])
            clash = sorted(ser & taken)
            if clash:
                held.append({"track": tid,
                             "reason": f"serialises on {', '.join(clash)} with a track already in this wave"})
                continue
            taken |= ser
            agent, then = _agent_for(tid, t)
            wave.append({
                "track": tid,
                "title": t.get("title", ""),
                "agent": agent,
                "then": then,
                "package": f"orchestration/work-packages/{tid}.md",
                "gates": t.get("gates") or [],
                "promotes": t.get("promotes") or [],
                "serialises_on": sorted(ser),
                "agent_effort": t.get("agent_effort", "unmeasured"),
            })

        if not wave:
            # Nothing can start. What is left is held on people, not on
            # capacity - so account for ALL of it here rather than letting
            # tracks fall off the plan silently. --check caught exactly that:
            # FSCOPE, D, FOBJ and FRULES were neither planned nor held, because
            # they depend on G, which is itself held on DEC1 and so never
            # "completes" for the speculative waves to build on.
            for tid in sorted(remaining):
                if any(h["track"] == tid for h in held):
                    continue
                state, why = derived[tid]
                if state == "conditional":
                    reason = f"conditional — {why}"
                elif state == "blocked":
                    reason = f"unreachable — {why}, and that chain ends at a human gate"
                else:
                    reason = f"derived {state}"
                held.append({"track": tid, "reason": reason})
            waves.append({"wave": wave_no, "speculative": wave_no > 1,
                          "tracks": [], "held": held,
                          "note": "no track is dispatchable; every remaining track waits on a human"})
            break

        waves.append({"wave": wave_no, "speculative": wave_no > 1,
                      "tracks": wave, "held": held})
        for e in wave:
            assumed_done.add(e["track"])
            remaining.discard(e["track"])

    return {
        "generated_from": "orchestration/tracks.yaml",
        "base_commit": head_commit(),
        "dispatchable_wave": 1,
        "note": "Waves after 1 are speculative: they assume the previous wave completes. "
                "One human review gate per wave boundary.",
        "waves": waves,
    }


def render(p):
    L = []
    for w in p["waves"]:
        tag = "  (SPECULATIVE — assumes the previous wave completes)" if w["speculative"] else "  (DISPATCHABLE)"
        L.append(f"\nWAVE {w['wave']}{tag}")
        if not w["tracks"]:
            L.append(f"  — {w.get('note', 'empty')}")
        for e in w["tracks"]:
            L.append(f"  {e['track']:<8} {e['title'][:46]:<46} {e['agent']} → {' → '.join(e['then'])}")
            if e["serialises_on"]:
                L.append(f"           serialises on: {', '.join(e['serialises_on'])}")
            if e["promotes"]:
                L.append(f"           promotes {len(e['promotes'])} staged file(s) — human installs")
        for h in w["held"]:
            L.append(f"  HELD {h['track']:<6} {h['reason']}")
    return "\n".join(L)


def check(p, tracks_path=None):
    """The plan must not contradict schedule.py. Same guard class as
    schedule.py --check: a plan that disagrees with the graph is the defect."""
    sch = _schedule()
    doc = sch.load(tracks_path)
    tracks = doc["tracks"]
    derived = sch.derive(tracks)
    errs = []

    w1 = next((w for w in p["waves"] if w["wave"] == 1), {"tracks": [], "held": []})
    for e in w1["tracks"]:
        state, why = derived[e["track"]]
        if state != "ready":
            errs.append(f"wave 1 contains {e['track']} which schedule.py derives as {state} ({why})")
        if (tracks[e["track"]].get("human_gate") or "none") != "none":
            errs.append(f"wave 1 contains {e['track']} which has an open human gate")

    ready_now = {k for k, (s, _) in derived.items() if s == "ready"}
    placed = {e["track"] for e in w1["tracks"]} | {h["track"] for h in w1["held"]}
    for tid in sorted(ready_now - placed):
        errs.append(f"{tid} is ready and appears nowhere in wave 1, neither dispatched nor held")

    for w in p["waves"]:
        seen = {}
        for e in w["tracks"]:
            for f in e["serialises_on"]:
                if f in seen:
                    errs.append(f"wave {w['wave']}: {e['track']} and {seen[f]} both write {f}")
                seen[f] = e["track"]

    # A recorded plan names the commit it was planned against. If HEAD has moved,
    # the plan describes a tree that no longer exists and any agent dispatched
    # from it is executing against different machinery.
    if os.path.exists(OUT):
        try:
            recorded = json.load(open(OUT)).get("base_commit", "")
        except (ValueError, OSError):
            recorded = ""
        now = head_commit()
        if recorded and now and recorded != now:
            errs.append(f"wave-plan.json was planned against tracks.yaml at {recorded[:8]} "
                        f"but it has since moved to {now[:8]}; re-run --plan before dispatching")
        elif not recorded:
            errs.append("wave-plan.json records no base_commit; re-run --plan")

    every = {e["track"] for w in p["waves"] for e in w["tracks"]}
    for tid, t in tracks.items():
        if t.get("status") != "done" and tid not in every:
            held = any(h["track"] == tid for w in p["waves"] for h in w["held"])
            if not held:
                errs.append(f"{tid} is not done, not planned into any wave, and not held")
    return errs


def promote(tid, tracks_path=None):
    sch = _schedule()
    tracks = sch.load(tracks_path)["tracks"]
    if tid not in tracks:
        sys.exit(f"no such track: {tid}")
    entries = tracks[tid].get("promotes") or []
    if not entries:
        print(f"{tid} stages nothing.")
        return 0
    print(f"# PROTOCOL step 4a PROMOTE — {tid}")
    print("# Review each diff, then run the command. This script does NOT run them:")
    print("# installing verification machinery is a human act by construction (R13).\n")
    missing = 0
    for e in entries:
        src, dst = e["from"], e["to"]
        sp, dp = os.path.join(PKG, src), os.path.join(PKG, dst)
        if not os.path.exists(sp):
            print(f"# NOT STAGED YET: {src}  (the track has not produced it)")
            missing += 1
            continue
        if os.path.exists(dp):
            print(f"git diff --no-index -- {dst} {src}   # {dst} EXISTS — this is a merge, not a move")
            print(f"#   review, apply by hand, then: git add {dst}\n")
        else:
            print(f"git diff --no-index -- /dev/null {src}")
            print(f"mkdir -p {os.path.dirname(dst)} && git mv {src} {dst}\n")
    print(f"# {len(entries) - missing} of {len(entries)} staged and ready; {missing} not yet produced.")
    print("# After promoting: python3 harden/checks/check41_machinery.py   # E2 must be green again")
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", help="tracks.yaml to plan from")
    ap.add_argument("--plan", action="store_true", help="write orchestration/wave-plan.json")
    ap.add_argument("--check", action="store_true", help="exit 1 if the plan contradicts schedule.py")
    ap.add_argument("--promote", metavar="TRACK", help="print the promote commands for a track")
    ap.add_argument("--preflight", action="store_true", help="print the base-commit assertion for a dispatch prompt")
    a = ap.parse_args()

    if a.preflight:
        base = head_commit()
        print(f"# Paste into every dispatch prompt for this wave, and require the agent to run it FIRST:")
        print(f"#   git merge-base --is-ancestor {base} HEAD || echo STALE-BASE")
        print(f"# base commit: {base}")
        print(f"# If it prints STALE-BASE the agent's worktree predates this plan. It must stop and")
        print(f"# report, not proceed: wave 1 had two agents briefed to use dispatch.py, check42 and")
        print(f"# PROTOCOL R13/R14, none of which existed in the tree they were given.")
        return

    if a.promote:
        sys.exit(promote(a.promote, a.file))

    p = plan(a.file)

    if a.check:
        errs = check(p, a.file)
        for e in errs:
            print(f"PLAN ERROR {e}")
        print("RESULT:", "PASS" if not errs else f"FAIL {len(errs)} inconsistencies")
        sys.exit(1 if errs else 0)

    print(render(p))
    if a.plan:
        json.dump(p, open(OUT, "w"), indent=2)
        print(f"\n-> {os.path.relpath(OUT, PKG)}")
    print("\nOnly wave 1 is dispatchable. One human review gate per wave boundary.")


if __name__ == "__main__":
    main()
