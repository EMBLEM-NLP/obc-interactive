#!/usr/bin/env python3
"""
check44_distribution.py - DOC1. The front page tells a reader how to obtain the
data the repository does not contain, and the fetcher names somewhere real.

Why this exists
---------------
An external audit found the repository advertising interactive PDFs it does not
contain. The absence itself is fine and is declared three times over -
`.gitignore` lines 19-21, `data-manifest.json`, and gate DATA1, which fails red
naming all 29 files on every CI run.

The defect is that nothing told a reader where to get them. Before this check,
`README.md` contained zero occurrences of `fetch_data`, `download`, `release`,
`tarball` or `gitignore`. A reader cloning the repository saw a front page
describing a `pdf/` directory, an `emitters/` directory and a completion table,
and had no way to learn that the tree they were holding contained none of it.

The mechanism that let it drift is the one AUDIT-rev12 finding 1 describes, in
the same file one section up: `harden/gen_readme.py` regenerates only the span
between `## What is still open` and `## Licence and attribution`. Everything
outside that span is hand-maintained and unwatched, and the README never said
which tree - hydrated bag or git checkout - its numbers described.

The two assertions, and why they must fail independently
--------------------------------------------------------
D1  For every path in `data-manifest.json` that is absent from the tree,
    `README.md` must name `ci/fetch_data.sh`.

D2  `ci/fetch_data.sh` must carry a location a reader can resolve, rather than
    a `...` placeholder.

**D2 is RED today and must stay red until a human publishes the release.** No
public release of the 338,348,579 bytes exists. That is the honest state and
this check reports it as a failure, not as a warning: a project that documents
a fetch script pointing at an ellipsis has not solved the distribution problem,
it has described it.

D1 passing must not mask D2 failing, so the two halves are separately
selectable (`--only d1`, `--only d2`) and separately exercised by the controls.
The default run fails while either half fails, and prints which.

The controls, and why both directions
-------------------------------------
`--controls` runs THIS script as a black box in a subprocess, four times:

    C1  D1 on the real README                      -> must exit 0
        D1 on a README with the pointer stripped   -> must exit non-zero
    C2  D2 on a fetch script with a real host      -> must exit 0
        D2 on the placeholder script (as shipped)  -> must exit non-zero

A check that always fails passes a mutation-only test, and a check that always
passes passes a pass-only test. C2's green direction is the load-bearing half
here precisely because D2's shipped state is red: without it, DOC1-D2 would be
indistinguishable from `sys.exit(1)`.

`check41_machinery.py` shipped with a one-directional control and CI run 11
found it firing on `mtime` for files nothing had changed - a false red, which
gets a gate ignored as thoroughly as a false green. See that file, lines
145-158 (the `update-index --refresh` fix) and 214-221 (the false-positive half
its control gained afterwards).

The mutations target the mechanism, never the ground truth (R2): C1 mutates the
README being scored, not `data-manifest.json`, which decides what is absent;
C2 mutates the fetch script being scored, not the definition of "resolvable".

Paths
-----
Every path resolves from the package root with an environment override (R7), so
this runs identically staged at `proposed/E/` and promoted to `harden/checks/`:

    OBC_PKG       package root (default: the tree above this file)
    OBC_README    default $OBC_PKG/README.md
    OBC_MANIFEST  default $OBC_PKG/data-manifest.json
    OBC_FETCH     default $OBC_PKG/ci/fetch_data.sh

    python3 check44_distribution.py               # both halves
    python3 check44_distribution.py --only d1     # D1 alone (PASS today)
    python3 check44_distribution.py --only d2     # D2 alone (FAIL today, deliberate)
    python3 check44_distribution.py --controls    # C1 and C2, both directions
    python3 check44_distribution.py --statements  # phrases H3 and G16d require
"""
import argparse
import json
import os
import re
import subprocess
import sys
import tempfile

FETCHER = "ci/fetch_data.sh"

# A location is a placeholder if it carries any of these. The ellipsis is both
# the U+2026 character the script actually uses and the three-dot ASCII form.
PLACEHOLDER_TOKENS = ("…", "...", "<", ">", "example.com", "EXAMPLE",
                      "TODO", "FIXME", "CHANGEME", "REPLACE", "your-host")

# Trailing punctuation that belongs to the prose, not to the URL.
_LOC_RE = re.compile(r"https?://[^\s\"'`,)\]}]+")

# Required by check22_docs.py (H3) and check19_package.py (G16d). Kept here so
# the split of README.md into README.md + PACKAGE.md cannot silently drop one.
#
# The third field is whether the owning check matches case-insensitively. H3
# goes through lib/canon.contains(..., casefold=True); G16d does a plain `in`
# on whitespace-normalised text. Where both own a phrase the strict form wins,
# because satisfying the loose one is not enough for the strict one. Getting
# this backwards would let a README pass this helper and fail G16d.
REQUIRED_STATEMENTS = [
    ("Unofficial",       "H3, G16d", False),
    ("free of charge",   "H3, G16d", False),
    ("King's Printer",   "H3, G16d", False),
    ("HANDOFF REQUIRED", "H3, G16d", False),
    ("current to",       "H3",       True),
    ("E4",               "G16d",     False),
]


def _root(start=None):
    """Walk up until orchestration/tracks.yaml is found, so this file works both
    staged at proposed/E/ and promoted to harden/checks/."""
    d = os.path.dirname(os.path.abspath(start or __file__))
    for _ in range(8):
        if os.path.isfile(os.path.join(d, "orchestration", "tracks.yaml")):
            return d
        nd = os.path.dirname(d)
        if nd == d:
            break
        d = nd
    sys.exit("check44: cannot locate the package root (no orchestration/tracks.yaml above me)")


PKG = os.environ.get("OBC_PKG") or _root()


def _p(env, rel):
    return os.environ.get(env) or os.path.join(PKG, rel)


def _read(path, what):
    if not os.path.isfile(path):
        return None, f"{what} is missing at {path}"
    with open(path, encoding="utf-8") as fh:
        return fh.read(), None


# --------------------------------------------------------------------------
# D1 - the front page points at the fetcher for data it does not carry
# --------------------------------------------------------------------------
def d1(readme_path=None, manifest_path=None):
    """Return (ok, lines). ok is False only on a real failure."""
    readme_path = readme_path or _p("OBC_README", "README.md")
    manifest_path = manifest_path or _p("OBC_MANIFEST", "data-manifest.json")
    out = []

    raw, err = _read(manifest_path, "data-manifest.json")
    if err:
        return False, [f"D1 FAIL: {err}"]
    try:
        man = json.loads(raw)
    except json.JSONDecodeError as e:
        return False, [f"D1 FAIL: data-manifest.json is not JSON ({e})"]
    files = man.get("files") or []
    if not files:
        return False, ["D1 FAIL: data-manifest.json lists no files"]

    absent = [r["path"] for r in files
              if not os.path.exists(os.path.join(PKG, r["path"]))]
    absent_bytes = sum(r["bytes"] for r in files if r["path"] in set(absent))
    out.append(f"D1 absent from the tree      : {len(absent)} of {len(files)} "
               f"({absent_bytes:,} B of {man.get('total_bytes', 0):,} B)")

    readme, err = _read(readme_path, "README.md")
    if err:
        return False, out + [f"D1 FAIL: {err}"]

    names = FETCHER in readme
    out.append(f"D1 README names {FETCHER:<14}: {'yes' if names else 'NO'}"
               f"   ({os.path.relpath(readme_path, PKG)})")

    # Informational, not gated: the three source modes a reader must choose
    # between. Reported so a README that names the script but not how to point
    # it anywhere is visible, without widening what D1 asserts.
    envs = [v for v in ("OBC_DATA_TARBALL", "OBC_DATA_DIR", "OBC_DATA_URL")
            if v in readme]
    out.append(f"D1 README names the source modes: {len(envs)} of 3 {envs}")

    if not absent:
        # R4: an assertion quantified over an empty set cannot fail. Say so in
        # the output rather than printing a bare PASS a reader would misread.
        out.append("D1 vacuous (nothing absent): the tree is hydrated, so D1 "
                   "has nothing to test here")
        return True, out
    if not names:
        out.append(f"D1 FAIL: {len(absent)} manifest paths are absent and "
                   f"README.md never names {FETCHER}")
        return False, out
    out.append("D1 PASS")
    return True, out


# --------------------------------------------------------------------------
# D2 - the fetcher names somewhere a reader can go
# --------------------------------------------------------------------------
def _classify(loc):
    """Return None if the location resolves, else the reason it does not."""
    for tok in PLACEHOLDER_TOKENS:
        if tok in loc:
            return f"placeholder {tok!r}"
    host = loc.split("://", 1)[1].split("/", 1)[0]
    if not host:
        return "bare scheme, no host"
    if "." not in host:
        return f"host {host!r} has no dot"
    return None


def d2(fetch_path=None):
    """Return (ok, lines)."""
    fetch_path = fetch_path or _p("OBC_FETCH", FETCHER)
    out = []
    text, err = _read(fetch_path, FETCHER)
    if err:
        return False, [f"D2 FAIL: {err}"]

    cands, seen = [], set()
    for m in _LOC_RE.finditer(text):
        loc = m.group(0).rstrip(".;:")
        # `startswith(("http://", "https://"))` in the script is a scheme test,
        # not a location. Drop bare schemes before counting, so the script is
        # not credited with locations it never states.
        if loc.rstrip("/") in ("http:/", "https:/", "http:", "https:"):
            continue
        if loc.split("://", 1)[1] == "":
            continue
        if loc in seen:
            continue
        seen.add(loc)
        cands.append(loc)

    resolvable = []
    for loc in cands:
        why = _classify(loc)
        out.append(f"D2   {loc:<52} {'resolves' if why is None else why}")
        if why is None:
            resolvable.append(loc)

    out.insert(0, f"D2 locations in {os.path.relpath(fetch_path, PKG)}"
                  f"        : {len(resolvable)} of {len(cands)} resolve")
    if not cands:
        out.append(f"D2 FAIL: {os.path.relpath(fetch_path, PKG)} states no "
                   f"location at all")
        return False, out
    if not resolvable:
        out.append("D2 FAIL: every location is a placeholder. This is the "
                   "honest state of the project: no public release of the "
                   "derived data exists yet.")
        out.append("D2       Closing this is a HUMAN act - publish the "
                   "artifact, then write its URL into " + FETCHER + ". "
                   "It may not be closed by editing this check.")
        return False, out
    out.append("D2 PASS")
    return True, out


# --------------------------------------------------------------------------
# statements - the split may not drop a phrase another gate requires
# --------------------------------------------------------------------------
def statements(readme_path=None):
    readme_path = readme_path or _p("OBC_README", "README.md")
    out = []
    readme, err = _read(readme_path, "README.md")
    if err:
        return False, [f"STATEMENTS FAIL: {err}"]
    flat = re.sub(r"\s+", " ", readme)   # the licence sentence wraps
    missing = []
    for phrase, who, casefold in REQUIRED_STATEMENTS:
        hay = flat.casefold() if casefold else flat
        needle = phrase.casefold() if casefold else phrase
        present = needle in hay
        out.append(f"  {phrase:<18} {'present' if present else 'MISSING'}"
                   f"   required by {who}"
                   f"{' (case-insensitive)' if casefold else ''}")
        if not present:
            missing.append(phrase)
    if missing:
        out.append(f"STATEMENTS FAIL: README.md lost {missing}")
        return False, out
    out.append(f"STATEMENTS PASS: {len(REQUIRED_STATEMENTS)} of "
               f"{len(REQUIRED_STATEMENTS)} present")
    return True, out


# --------------------------------------------------------------------------
# controls - this script, run as a black box, both directions, per half
# --------------------------------------------------------------------------
def _spawn(args, extra_env):
    env = dict(os.environ)
    env.update(extra_env)
    env.setdefault("OBC_PKG", PKG)
    r = subprocess.run([sys.executable, os.path.abspath(__file__), *args],
                       capture_output=True, text=True, env=env)
    return r.returncode


def controls():
    """Both halves, both directions. Returns (ok, lines)."""
    out, fails = [], []
    readme_path = _p("OBC_README", "README.md")
    fetch_path = _p("OBC_FETCH", FETCHER)
    tmp = tempfile.mkdtemp(prefix="check44_")

    # ---- C1: mutate the README, which is what D1 scores. Not the manifest,
    # which is the ground truth D1 scores it against (R2).
    readme, err = _read(readme_path, "README.md")
    if err:
        return False, [f"C1 FAIL: {err}"]
    stripped = readme.replace(FETCHER, "the data fetcher")
    mutated_readme = os.path.join(tmp, "README.stripped.md")
    with open(mutated_readme, "w", encoding="utf-8") as fh:
        fh.write(stripped)
    removed = readme.count(FETCHER)
    rc_ok = _spawn(["--only", "d1"], {"OBC_README": readme_path})
    rc_mut = _spawn(["--only", "d1"], {"OBC_README": mutated_readme})
    ok1 = rc_ok == 0 and rc_mut != 0
    out.append(f"C1 strip-pointer      untouched exit {rc_ok}   "
               f"mutated exit {rc_mut}   "
               f"{'ok' if ok1 else ('NEVER PASSES' if rc_ok else 'NEVER FAILS')}")
    out.append(f"   mutation: removed {removed} occurrence(s) of {FETCHER!r} "
               f"from a copy of README.md")
    if not ok1:
        fails.append(f"C1: untouched exit {rc_ok}, mutated exit {rc_mut}")

    # ---- C2: mutate the fetch script, which is what D2 scores. The green
    # direction is the load-bearing one: D2's shipped state is red, so without
    # a copy that passes, D2 is indistinguishable from sys.exit(1).
    fetch, err = _read(fetch_path, FETCHER)
    if err:
        return False, out + [f"C2 FAIL: {err}"]
    repaired_text = fetch.replace("…", "github.com")
    repaired = os.path.join(tmp, "fetch_data.repaired.sh")
    with open(repaired, "w", encoding="utf-8") as fh:
        fh.write(repaired_text)
    rc_ok2 = _spawn(["--only", "d2"], {"OBC_FETCH": repaired})
    rc_mut2 = _spawn(["--only", "d2"], {"OBC_FETCH": fetch_path})
    ok2 = rc_ok2 == 0 and rc_mut2 != 0
    out.append(f"C2 restore-placeholder repaired exit {rc_ok2}   "
               f"placeholder exit {rc_mut2}   "
               f"{'ok' if ok2 else ('NEVER PASSES' if rc_ok2 else 'NEVER FAILS')}")
    out.append(f"   mutation: replaced {fetch.count(chr(0x2026))} ellipsis(es) "
               f"with a real host in a copy of {FETCHER}, then restored the "
               f"shipped file")
    if not ok2:
        fails.append(f"C2: repaired exit {rc_ok2}, placeholder exit {rc_mut2}")

    out.append("")
    out.append("Each half is asserted in BOTH directions. A check that always "
               "fails passes a mutation-only test.")
    return not fails, out


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    ap.add_argument("--only", choices=["d1", "d2"],
                    help="run one half alone, so one cannot mask the other")
    ap.add_argument("--controls", action="store_true",
                    help="both halves, both directions, as a black box")
    ap.add_argument("--statements", action="store_true",
                    help="phrases H3 and G16d require README.md to keep")
    a = ap.parse_args()

    if a.controls:
        ok, lines = controls()
    elif a.statements:
        ok, lines = statements()
    elif a.only == "d1":
        ok, lines = d1()
    elif a.only == "d2":
        ok, lines = d2()
    else:
        ok1, l1 = d1()
        ok2, l2 = d2()
        ok, lines = ok1 and ok2, l1 + [""] + l2 + [""]
        lines.append(f"DOC1 halves: D1 {'PASS' if ok1 else 'FAIL'}, "
                     f"D2 {'PASS' if ok2 else 'FAIL'}")
        if ok1 and not ok2:
            lines.append("D2's red is the declared state of this project, not "
                         "a regression. See gates/GATES-E.md, DOC1-D2.")

    for l in lines:
        print(l)
    print("RESULT:", "PASS" if ok else "FAIL")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
