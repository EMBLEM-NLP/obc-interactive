#!/usr/bin/env python3
"""
gen_packages.py - one self-contained brief per track, generated from
tracks.yaml so the brief can never disagree with the DAG.

    python3 orchestration/gen_packages.py

Each package is what an executor - person, CI job, subagent - receives. It
carries: the track's position in the graph, exactly what it consumes and
produces, the gates it must declare, the H10 requirement, the exit criteria,
the known traps (each one a defect this project already shipped), and the
completion checklist from PROTOCOL.md. Nothing in a package is typed here;
edit tracks.yaml and regenerate.
"""
import os
import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "work-packages")
doc = yaml.safe_load(open(os.path.join(HERE, "tracks.yaml")))
tracks = doc["tracks"]
decisions = {d["id"]: d for d in doc.get("decisions_pending") or []}

CHECKLIST = """## Completion checklist (PROTOCOL.md — none optional)

- [ ] 1 DECLARE   gates written to gates/GATES-{tid}.md before code
- [ ] 2 BUILD     in a copy of the tree, never in the bag
- [ ] 3 MUTATE    every ratio gate registered in harden/checks/check35_controls.py; check35 PASS
- [ ] 4 INTEGRATE real paths, orchestration wired, superseded files moved not deleted
- [ ] 4a PROMOTE  every protected output STAGED at proposed/{tid}/<basename> and declared
                  under `promotes:` in tracks.yaml — never written at its real path (R13);
                  flat per track, never proposed/harden/checks/... (R14)
- [ ] 5 RE-BAG    bash ci/regenerate.sh; rebuild; provenance regenerated
- [ ] 6 VERIFY    python3 ci/run_gates.py from a CLEAN bag — every touched gate PASS, corpus mode
- [ ] 7 AUDIT     addendum: what moved, what did not, what broke, what was FOUND
- [ ] tracks.yaml updated: own status, and any new item discovered filed under its track

Returning a pack of loose files is step 2. It is not done."""


def render(tid, t):
    deps = t.get("depends_on") or []
    succ = [k for k, v in tracks.items() if tid in (v.get("depends_on") or [])]
    L = [f"# Work package — {tid}: {t['title']}", ""]
    L += [f"**Status in DAG:** `{t.get('status')}`  ·  "
          f"**Human effort (typed):** {t.get('human_effort', '—')}  ·  "
          f"**Agent effort:** {t.get('agent_effort', 'unmeasured')}  ·  "
          f"**Human gate:** {t.get('human_gate', '—')}"]
    L += [f"**Depends on:** {', '.join(deps) or '(none)'}  ·  **Unblocks:** {', '.join(succ) or '(nothing downstream)'}"]
    if t.get("parallel_with"):
        L += [f"**May run in parallel with:** {', '.join(t['parallel_with'])} — on a separate copy of the tree; serialise on shared files."]
    L += [""]
    if t.get("condition"):
        L += ["> **CONDITIONAL.** " + " ".join(t["condition"].split()), ""]
    if t.get("executor_note"):
        L += ["> " + " ".join(t["executor_note"].split()), ""]
    if t.get("trap"):
        L += ["> **Trap.** " + " ".join(t["trap"].split()), ""]
    if t.get("consumes"):
        L += ["## Consumes", ""] + [f"- `{x}`" for x in t["consumes"]] + [""]
    if t.get("produces"):
        L += ["## Produces", ""] + [f"- `{x}`" for x in t["produces"]] + [""]
    if t.get("promotes"):
        L += ["## Staged, then promoted by a human (PROTOCOL step 4a, R13)", "",
              "You write the left column. You may not write the right column — "
              "`.claude/settings.json`, `protect-checks.sh` and `guard-machinery.sh` all refuse it, "
              "and gate E2 catches it however it is produced.", "",
              "| you write | a human installs at |", "|---|---|"]
        L += [f"| `{e['from']}` | `{e['to']}` |" for e in t["promotes"]] + [""]
    if t.get("serialises_on"):
        L += ["## Serialises on", "",
              "Another track writes these too. `dispatch.py` will not place two tracks "
              "sharing one of them in the same wave.", ""]
        L += [f"- `{x}`" for x in t["serialises_on"]] + [""]
    if t.get("items"):
        L += ["## Items", ""] + [f"- **{k}** — {v}" for k, v in t["items"].items()] + [""]
    L += ["## Gates to declare", ""] + [f"- `{g}`" for g in (t.get("gates") or [])]
    L += ["", "Every gate that reports a ratio needs a mutation in `check35_controls.py` that drives it below its floor. "
          "The mutation targets the mechanism, never the ground truth. Untouched must exit 0; mutated must exit non-zero.", ""]
    if t.get("exit_criteria"):
        L += ["## Exit criteria", ""] + [f"- {x}" for x in t["exit_criteria"]] + [""]
    if t.get("exceptions"):
        L += ["## Enumerated exceptions", ""] + [f"- {x}" for x in t["exceptions"]] + [""]
    if t.get("evidence"):
        L += [f"## Evidence of completion", "", str(t["evidence"]), ""]
    rel = [d for d in decisions.values() if tid in (d.get("blocks") or []) or tid in (d.get("affects") or [])]
    if rel:
        L += ["## Decisions this track needs from a human", ""]
        L += [f"- **{d['id']}** — {d['question']}" for d in rel]
        L += ["", "Do not resolve these by assumption. A track that guesses a decision produces confident output with no way to know it is wrong.", ""]
    L += [CHECKLIST.format(tid=tid), ""]
    L += ["---", "Unofficial derived work. Current to 2025-01-16 (through O. Reg. 5/25). Not the official Building Code Compendium.",
          "© King's Printer for Ontario, 2024. Reproduced with permission."]
    return "\n".join(L)


os.makedirs(OUT, exist_ok=True)
for tid, t in tracks.items():
    open(os.path.join(OUT, f"{tid}.md"), "w").write(render(tid, t))
print(f"{len(tracks)} work packages -> {os.path.relpath(OUT)}")
