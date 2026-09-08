#!/usr/bin/env python3
"""
check42_produces.py - E3. No track is specified to produce what every executor
is forbidden to write.

Why this exists
---------------
`tracks.yaml` told A4 to produce `harden/checks/check36_schema.py`, G to produce
`retrieval/checks/check38_capabilities.py` and `check39_tools.py`, D to produce
`retrieval/checks/check36_modality.py`, and FSCOPE to produce
`gates/GATES-scope.md`. Every one of those matches `PROTECTED` in
check41_machinery.py and the deny array in `.claude/settings.json`.

PROTOCOL.md step 1 is worse: "DECLARE gates in gates/GATES-<track>.md BEFORE
writing code". The first action of every track is a write the guard refuses.

So the DAG and the enforcement layer contradicted each other, and the
contradiction was invisible because nothing compared them. Four tracks were
`ready` and none of them could take step 1. It was recorded as an open item in
ENFORCE's evidence block in AUDIT-rev10 and stayed open through revisions 11-13,
because a note in an audit is not a mechanism (R11).

This is the mechanism. It reads the same PROTECTED list check41 uses - a fourth
consumer of one definition, not a fifth copy - and fails if any track that is
not yet done names a protected path in `produces`.

The staging convention it enforces
----------------------------------
A track that must end up writing verification machinery stages it instead:

    proposed/<TRACK>/<basename>        the file the executor writes
    promotes: [{from: ..., to: ...}]   the real destination, declared in tracks.yaml

and a human installs it (PROTOCOL step 4a PROMOTE). The guard stays absolute.

Why the staging tree is FLAT per track and does not mirror the real tree
------------------------------------------------------------------------
The obvious layout, `proposed/harden/checks/check36_schema.py`, is broken, and
measurably so. check41's `_candidates()` expands an ABSOLUTE path into every
suffix of itself, so that a worktree naming the main checkout absolutely is
still caught (R12). That expansion does not know what staging is:

    proposed/harden/checks/check36_schema.py                    -> not protected
    /home/user/obc/proposed/harden/checks/check36_schema.py     -> PROTECTED
                          ^ suffix "harden/checks/check36_schema.py" matches

The same staged file is permitted or refused depending on how the executor spells
its path. That is precisely the defect R12 was written for, running the other
way, and a permission that depends on spelling is not a permission.

`proposed/<TRACK>/<basename>` has no suffix that can match any PROTECTED
pattern, because every pattern needs a directory segment (`harden/checks/`,
`gates/GATES-`, `ci/`) that a flat per-track directory never produces. Verified
for both spellings by `--layout` below.

    python3 harden/checks/check42_produces.py
    python3 harden/checks/check42_produces.py --layout
    NEGATIVE=1 python3 harden/checks/check42_produces.py   # must FAIL
"""
import argparse
import importlib.util
import os
import sys

try:
    import yaml
except ImportError:
    sys.exit("pip install pyyaml --break-system-packages")


def _root(start=None):
    """Walk up until orchestration/tracks.yaml is found, so this file works
    both staged at proposed/ENFORCE/ and promoted to harden/checks/."""
    d = os.path.dirname(os.path.abspath(start or __file__))
    for _ in range(8):
        if os.path.isfile(os.path.join(d, "orchestration", "tracks.yaml")):
            return d
        nd = os.path.dirname(d)
        if nd == d:
            break
        d = nd
    sys.exit("check42: cannot locate the package root (no orchestration/tracks.yaml above me)")


PKG = _root()
STAGE = "proposed"


def _check41():
    p = os.path.join(PKG, "harden", "checks", "check41_machinery.py")
    if not os.path.isfile(p):
        sys.exit(f"check42: {os.path.relpath(p, PKG)} is missing; PROTECTED has no other definition")
    spec = importlib.util.spec_from_file_location("check41_machinery", p)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def _audit_promote(c41, tid, entry):
    """P2 (shape and destination) and P4 (layout collision) for one entry."""
    out = []
    if not isinstance(entry, dict) or "from" not in entry or "to" not in entry:
        return [("P2", tid, f"promotes entry is not {{from, to}}: {entry!r}")]
    src, dst = str(entry["from"]), str(entry["to"])
    want = f"{STAGE}/{tid}/"
    if not src.startswith(want):
        out.append(("P2", tid, f"staged `{src}` must live under `{want}`"))
    elif "/" in src[len(want):]:
        out.append(("P2", tid, f"staged `{src}` must be flat under `{want}` (see the layout note)"))
    if not c41.is_protected(dst):
        out.append(("P2", tid, f"`{dst}` is not protected — stage only what the guard refuses"))
    # The layout guard: a staged path must be unprotected under BOTH spellings,
    # or an executor naming it absolutely is refused and the same file naming it
    # relatively is not. A permission that depends on spelling is not one.
    for spelling in (src, os.path.join(PKG, src)):
        if c41.is_protected(spelling):
            out.append(("P4", tid, f"staged `{spelling}` IS protected — layout collision, see the module docstring"))
    return out


def audit(tracks_path=None):
    """Return (findings, n_tracks_examined). A finding is (code, track, detail)."""
    c41 = _check41()
    doc = yaml.safe_load(open(tracks_path or os.path.join(PKG, "orchestration", "tracks.yaml")))
    tracks = doc["tracks"]
    out = []
    n = 0

    for tid, t in tracks.items():
        promotes = t.get("promotes") or []
        # P2/P4 - the staging MECHANISM - are checked on every track, done or
        # not: a malformed or colliding staged path is broken now, whenever it
        # was written. P1/P3 are checked only on open tracks, because a done
        # track's `produces` records what already happened under the rules in
        # force then, and rewriting history to satisfy a later check is the
        # opposite of an audit trail (R10).
        for entry in promotes:
            out += _audit_promote(c41, tid, entry)

        if t.get("status") == "done":
            continue
        n += 1

        for p in t.get("produces") or []:
            path = str(p).split()[0]           # strip "(generated)" style notes
            if c41.is_protected(path):
                out.append(("P1", tid, f"produces protected path `{path}`"))

        # PROTOCOL step 1: gates are declared in a ledger before code, and every
        # ledger path is protected, so every open track needs one staged.
        if not (t.get("gates") or []):
            out.append(("P3", tid, "declares no gates; PROTOCOL step 1 has nothing to write"))
        ledger = f"gates/GATES-{tid}.md"
        if not any(isinstance(e, dict) and str(e.get("to")) == ledger for e in promotes):
            out.append(("P3", tid, f"does not promote its gate ledger `{ledger}`"))

    return out, n


def layout_report():
    """Print the two spellings for a representative staged path under both the
    flat and the mirrored layout. This is the evidence for the docstring."""
    c41 = _check41()
    rows = [
        ("flat     ", "proposed/A4/check36_schema.py"),
        ("mirrored ", "proposed/harden/checks/check36_schema.py"),
        ("flat     ", "proposed/FSCOPE/GATES-scope.md"),
        ("mirrored ", "proposed/gates/GATES-scope.md"),
    ]
    print("layout            relative              absolute")
    bad = 0
    for kind, rel in rows:
        a = c41.is_protected(rel)
        b = c41.is_protected(os.path.join(PKG, rel))
        if kind.strip() == "flat" and (a or b):
            bad += 1
        print(f"  {kind} {rel:<45} {'PROTECTED' if a else 'ok':<10} {'PROTECTED' if b else 'ok'}")
    print("\nThe mirrored layout is permitted relatively and refused absolutely: the same")
    print("file, two spellings, two answers. The flat layout is `ok` under both.")
    return bad


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", help="tracks.yaml to audit (default: the package's)")
    ap.add_argument("--layout", action="store_true", help="show the staging-layout evidence")
    a = ap.parse_args()

    if a.layout:
        sys.exit(1 if layout_report() else 0)

    findings, n = audit(a.file)

    # NEGATIVE control (R1/R11): seed one protected produces entry into an
    # in-memory copy of the DAG and require this check to see it. A gate that
    # cannot go red is a light.
    if os.environ.get("NEGATIVE") == "1":
        import copy, tempfile
        doc = yaml.safe_load(open(a.file or os.path.join(PKG, "orchestration", "tracks.yaml")))
        doc = copy.deepcopy(doc)
        victim = next(k for k, v in doc["tracks"].items() if v.get("status") != "done")
        doc["tracks"][victim].setdefault("produces", []).append("harden/checks/check_seeded_by_control.py")
        with tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False) as fh:
            yaml.safe_dump(doc, fh)
            tmp = fh.name
        seeded, _ = audit(tmp)
        os.unlink(tmp)
        hit = [f for f in seeded if f[0] == "P1" and "check_seeded_by_control" in f[2]]
        print(f"NEGATIVE control: seeded a protected produces entry into {victim}")
        print(f"  detected: {len(hit)}  (must be >= 1)")
        print("RESULT:", "PASS" if hit else "FAIL — the check cannot see a protected produces entry")
        sys.exit(0 if hit else 1)

    for code, tid, detail in findings:
        print(f"{code} {tid}: {detail}")
    print(f"\nexamined {n} open track(s); {len(findings)} finding(s)")
    print("RESULT:", "PASS" if not findings else f"FAIL {len(findings)}")
    sys.exit(1 if findings else 0)


if __name__ == "__main__":
    main()
