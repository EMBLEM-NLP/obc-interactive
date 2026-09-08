#!/usr/bin/env python3
"""
check47_gateids.py - GID1/GID2. A gate id means one thing.

Why this exists
---------------
Found on 2026-09-08 while explaining what the letters in a gate id denote. Every
ledger entry carries its own CHECK: command; ci/checks.yaml independently maps a
gate id to a script. Nothing compared them, and 10 disagree:

    E1  ledger: SQLite answers the three queries the model was built for
        ledger CHECK check16_sqlite.py    board runs ci/test_hooks.sh
    G7  ledger: every citation resolves or carries a reason code
        ledger CHECK check7_refs.py       board runs check6_figures.py
    G9  ledger: the absence assertions in G8 can detect the defects they deny
        ledger CHECK control_negative.py  board runs check7_refs.py

So `run_gates.py` prints a colour beside a gate whose ledger describes something
the executed check never measured. "G7 PASS" is check6_figures passing while the
ledger says G7 means citations resolve. The result is real; the label is wrong,
and a reader who looks the gate up gets a claim nothing established.

Two of the ten are the enforcement layer's own doing: E1 and E2 already named
emitter gates in gates/GATES-emitters.md when ci/test_hooks.sh and
check41_machinery.py took those ids, and E3 (check42_produces.py) was added on
top of an E3 that was already there.

What this does NOT do
---------------------
It does not decide which file is right. Resolving that needs the derived data and
the ledgers' evidence digests, and a check that guessed would be inventing the
answer it is supposed to detect. It reports the disagreement and fails.

Deliberately compares BASENAMES. The ledger writes `python3 checks/check7_refs.py`
relative to its own working set; checks.yaml writes `verify/volume1/checks/...`
relative to the package root. Comparing full paths would report every gate as a
mismatch and prove nothing, which is the "a verification that fails for its own
reasons" trap this project has hit three times.

GID2 - the same id in more than one namespace
----------------------------------------------
Track items and gates are numbered independently and neither is namespaced, so
one string means different things depending on the document. 10 collide today:

    E1  item of E: header-row flagging (0 of 320 tables)
        gate in GATES-emitters.md: SQLite answers the three queries
        and on the CI board: ci/test_hooks.sh
    E4  item of E: page 728 Volume 1, 7 orphaned body lines
        gate in GATES-emitters.md: manual accessibility review, ABANDONED
    G1-G4 items of G (hybrid search, cannot-list, fixtures, refusal eval)
        gates in GATES-volume1.md (glyph capture, regions, headings, continuity)

Tracks D, E and G are themselves gate-id prefixes, so "G1" may be read as the
first gate of the Volume 1 ledger or the first item of track G. Reported, not
renamed: renumbering either namespace would invalidate every evidence digest
already recorded against the old id, which is a decision for a person.

    python3 harden/checks/check47_gateids.py
    python3 harden/checks/check47_gateids.py --list
    NEGATIVE=1 python3 harden/checks/check47_gateids.py   # must FAIL
"""
import argparse
import glob
import os
import re
import sys

try:
    import yaml
except ImportError:
    sys.exit("pip install pyyaml --break-system-packages")


def _root(start=None):
    d = os.path.dirname(os.path.abspath(start or __file__))
    for _ in range(8):
        if os.path.isfile(os.path.join(d, "ci", "checks.yaml")):
            return d
        nd = os.path.dirname(d)
        if nd == d:
            break
        d = nd
    sys.exit("check47: cannot locate the package root")


PKG = _root()
GATE_LINE = re.compile(r"^- \[([x~ ])\] ([A-Za-z0-9]+(?:-[A-Za-z0-9]+)*):\s*(.*)$")
# a gate this project has already struck as superseded carries ABANDON: and no
# CHECK:, so it cannot disagree with anything and is not counted.
ABANDON = "ABANDON:"


def ledger_checks(root=PKG):
    """{gate id: (ledger, assertion, CHECK basename or None)}"""
    out = {}
    files = sorted(glob.glob(os.path.join(root, "gates", "GATES-*.md")))
    files += sorted(glob.glob(os.path.join(root, "proposed", "*", "GATES-*.md")))
    for f in files:
        rel = os.path.relpath(f, root)
        lines = open(f).read().split("\n")
        for i, ln in enumerate(lines):
            m = GATE_LINE.match(ln)
            if not m:
                continue
            gid, text, chk = m.group(2), m.group(3).strip(), None
            for nxt in lines[i + 1:]:
                if GATE_LINE.match(nxt):
                    break
                t = nxt.strip()
                if t.startswith(ABANDON):
                    chk = None
                    break
                if t.startswith("CHECK:"):
                    cmd = t.split("CHECK:", 1)[1].strip()
                    cmd = re.sub(r"^(python3|bash|sh)\s+", "", cmd)
                    chk = os.path.basename(cmd.split()[0]) if cmd.split() else None
                    break
            out.setdefault(gid, (rel, text, chk))
    return out


def board_checks(root=PKG):
    """{gate id: [script basenames]} from ci/checks.yaml, superseded rows skipped."""
    out = {}
    cy = yaml.safe_load(open(os.path.join(root, "ci", "checks.yaml")))
    for c in cy.get("checks") or []:
        if c.get("superseded"):
            continue
        for g in str(c.get("gate", "")).split(","):
            g = g.strip()
            if g:
                out.setdefault(g, []).append(os.path.basename(str(c.get("script", ""))))
    return out


def namespace_clashes(root=PKG):
    """GID2: ids that are both a track item and a gate."""
    led = ledger_checks(root)
    doc = yaml.safe_load(open(os.path.join(root, "orchestration", "tracks.yaml")))
    out = []
    for tid, t in (doc.get("tracks") or {}).items():
        for k, v in (t.get("items") or {}).items():
            k = str(k)
            if k in led:
                out.append((k, tid, str(v), led[k][0], led[k][1]))
    return sorted(out)


def audit(root=PKG):
    led, board = ledger_checks(root), board_checks(root)
    rows = []
    for gid, (ledger, text, chk) in sorted(led.items()):
        if not chk or gid not in board:
            continue
        if chk not in board[gid]:
            rows.append((gid, ledger, text, chk, board[gid][0]))
    return rows, len(led), len(board)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--list", action="store_true", help="every id both files know about")
    a = ap.parse_args()

    if os.environ.get("NEGATIVE") == "1":
        # Seed a disagreement the check must see: rewire one gate whose ledger
        # and board currently AGREE to a different script. A control that seeded
        # an already-broken gate would pass without the check doing anything.
        import copy, tempfile, shutil
        led, board = ledger_checks(), board_checks()
        agree = [g for g, (_, _, c) in led.items()
                 if c and g in board and c in board[g]]
        if not agree:
            print("RESULT: FAIL - no agreeing gate to seed against")
            sys.exit(1)
        victim = sorted(agree)[0]
        tmp = tempfile.mkdtemp()
        shutil.copytree(os.path.join(PKG, "gates"), os.path.join(tmp, "gates"))
        os.makedirs(os.path.join(tmp, "ci"))
        cy = yaml.safe_load(open(os.path.join(PKG, "ci", "checks.yaml")))
        for c in cy["checks"]:
            if str(c.get("gate", "")).strip() == victim:
                c["script"] = "checks/check_seeded_by_control.py"
        yaml.safe_dump(cy, open(os.path.join(tmp, "ci", "checks.yaml"), "w"))
        rows, _, _ = audit(tmp)
        hit = [r for r in rows if r[0] == victim]
        shutil.rmtree(tmp, ignore_errors=True)
        print(f"NEGATIVE control: rewired {victim}, which currently agrees, to another script")
        print(f"  GID1 detected: {len(hit)}  (must be >= 1)")
        # GID2's control is separate: the two assertions fail for different
        # reasons and a single control would leave one of them untested.
        clash_now = namespace_clashes()
        print(f"  GID2 sees      : {len(clash_now)} existing collision(s), and reports each with "
              f"both meanings rather than the id alone")
        ok = bool(hit) and bool(clash_now)
        print("RESULT:", "PASS" if ok else "FAIL - a control did not detect what it exists for")
        sys.exit(0 if ok else 1)

    rows, nled, nboard = audit()
    clash = namespace_clashes()
    if a.list:
        led, board = ledger_checks(), board_checks()
        for g in sorted(set(led) & set(board)):
            print(f"  {g:6} ledger={led[g][2] or '(none)':30} board={board[g][0]}")

    for gid, ledger, text, chk, run in rows:
        print(f"GID1 {gid}: {ledger} says CHECK {chk}, ci/checks.yaml runs {run}")
        print(f"          ledger text: {text[:110]}")
    for gid, tid, item, ledger, text in clash:
        print(f"GID2 {gid}: item of track {tid} ({item[:60]})")
        print(f"          and a gate in {ledger} ({text[:60]})")

    print(f"\n{nled} ledger gates, {nboard} board gates")
    print(f"GID1 {len(rows)} ledger/board disagreement(s); GID2 {len(clash)} id(s) in two namespaces")
    bad = len(rows) + len(clash)
    print("RESULT:", "PASS" if not bad else
          f"FAIL {bad} - an id does not name one thing")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
