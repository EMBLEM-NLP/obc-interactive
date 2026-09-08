#!/usr/bin/env python3
"""
check35_MAINT_control.py - the H10 control for gate M2.

STAGED, NOT INSTALLED. This is not a new check; it is two mutation functions and
two registry rows destined for `SUBPROCESS_CONTROLS` in
`harden/checks/check35_controls.py`, which is protected
(`check41_machinery.PROTECTED` pattern `harden/checks/*`) and which a track
executor may not edit. See PROMOTION at the bottom for the exact edit, and run
this file directly to see the control pass before anyone makes it.

Why it exists
-------------
M2 reports a ratio - precision and recall over the seeded change set - and R1
says a ratio gate without a mutation that drives it below its floor is void,
however green. Six such gates shipped in this project and every one of them had
a real evidence digest.

The contract, both directions:

    untouched  ->  check45_diff.py --gate M2   must exit 0
    mutated    ->  check45_diff.py --gate M2   must exit non-zero

Both, because a check that always fails passes a mutation-only test and a check
that never fails passes an untouched-only test.

What is mutated, and what is not (R2)
-------------------------------------
The mutation targets `tools/diff_editions.py` - the MECHANISM, the pipeline
output M2 scores. It does not touch `tools/fixtures/make_fixtures.py` or
`seed.json` - the GROUND TRUTH M2 scores against.

That distinction is the whole of R2 and it is easy to get wrong here. Weakening
the seed manifest would shrink both sides of the ratio and leave precision and
recall at 1.0, which is check33's tautology one level up and the exact mistake
this project has already made once. So the fixtures are built by the SHIPPED
maker in both runs; only the tool differs.

Two mutations, because M2 can be failed from either side
--------------------------------------------------------
    m_diff_layout_blind   empties LAYOUT_FIELDS and LAYOUT_TOKEN_KEYS, so the
                          repagination re-enters the projection. The diff then
                          reports all 15 fixture nodes. Recall stays 1.0 - it
                          did find the amendment - and PRECISION collapses to
                          4/15. This is the control for "a diff that reports
                          everything is as useless as one that reports nothing",
                          and it is the mutation that matters, because a gate
                          written on recall alone would survive it.

    m_diff_text_blind     removes `body` from the projection, so the amended
                          sentence stops registering. RECALL collapses. The
                          other direction.

Neither mutation is subtle and neither is meant to be. A control is cheap on
purpose; the reason tautological metrics survive is not that controls are
expensive, it is that nobody is required to write one.
"""
import os
import re
import shutil
import subprocess
import sys
import tempfile


def _root(start=None):
    d = os.path.dirname(os.path.abspath(start or __file__))
    for _ in range(8):
        if os.path.isfile(os.path.join(d, "orchestration", "tracks.yaml")):
            return d
        nd = os.path.dirname(d)
        if nd == d:
            break
        d = nd
    sys.exit("check35_MAINT_control: cannot locate the package root")


_PKG = _root()

# The check under control. Staged here; `harden/checks/check45_diff.py` once
# promoted. Both spellings are tried so the control works before and after.
_CHECK_CANDIDATES = (
    os.path.join(_PKG, "harden", "checks", "check45_diff.py"),
    os.path.join(_PKG, "proposed", "MAINT", "check45_diff.py"),
)


def _check_path():
    for p in _CHECK_CANDIDATES:
        if os.path.isfile(p):
            return p
    sys.exit("check35_MAINT_control: check45_diff.py is not at either of "
             + ", ".join(_CHECK_CANDIDATES))


def _sub(path, pattern, repl, what):
    """Replace and PROVE the replacement happened.

    A patch that silently matches nothing produces a mutation that changes
    nothing, and a mutation that changes nothing reports NEVER FAILS - which
    reads as `the check is vacuous` when the truth is `the control is broken`.
    This project has already lost time to a regex that assumed one space where
    the YAML had two. So: count, and refuse zero.
    """
    with open(path, encoding="utf-8") as fh:
        src = fh.read()
    # re.M is load-bearing: the LAYOUT_FIELDS patterns anchor with ^/$ on a
    # line, and without it they anchor on the whole file and match nothing.
    # That is exactly the silent-no-op this function exists to refuse, and it
    # caught itself on the first run.
    new, n = re.subn(pattern, repl, src, flags=re.M)
    if n == 0:
        raise SystemExit(f"mutation did not apply: {what} matched nothing in "
                         f"{path}. The control is broken, not the check.")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(new)
    return n


def _copy_tool(tmp):
    """Copy only tools/ - the mechanism. The fixtures are regenerated by the
    SHIPPED maker in both runs, so the ground truth is byte-identical between
    them by construction."""
    dst = os.path.join(tmp, "tools")
    shutil.copytree(os.path.join(_PKG, "tools"), dst,
                    ignore=shutil.ignore_patterns("__pycache__", "build"))
    return os.path.join(dst, "diff_editions.py")


def m_diff_layout_blind(tmp):
    """Stop excluding layout. Precision collapses; recall does not."""
    tool = _copy_tool(tmp)
    _sub(tool, r'^LAYOUT_FIELDS = \([^)]*\)$', 'LAYOUT_FIELDS = ()',
         "LAYOUT_FIELDS")
    _sub(tool, r'^LAYOUT_TOKEN_KEYS = \([^)]*\)$', 'LAYOUT_TOKEN_KEYS = ()',
         "LAYOUT_TOKEN_KEYS")
    return tool, ("layout excluded from nothing: LAYOUT_FIELDS and "
                  "LAYOUT_TOKEN_KEYS emptied, so the repagination re-enters "
                  "the projection and every node is reported")


def m_diff_text_blind(tmp):
    """Stop comparing the text. Recall collapses."""
    tool = _copy_tool(tmp)
    _sub(tool, r'"body": body\(n\),', '"body": "",',
         "the body term of the projection")
    return tool, ("`body` removed from the projection, so an amended sentence "
                  "no longer registers as changed")


# ---- registry: name, gate, check script, mutation, args, env-builder --------
CONTROLS = [
    ("check45_diff M2 precision", "M2", "check45_diff.py",
     m_diff_layout_blind, ("--gate", "M2")),
    ("check45_diff M2 recall", "M2", "check45_diff.py",
     m_diff_text_blind, ("--gate", "M2")),
]


def _exit(check, args, env):
    r = subprocess.run([sys.executable, check, *args], cwd=_PKG,
                       capture_output=True, text=True, timeout=600,
                       env={**os.environ, **env})
    return r.returncode, (r.stdout.strip().splitlines() or [""])[-1]


def run():
    check = _check_path()
    print(f"check under control: {os.path.relpath(check, _PKG)}")
    print(f"{'control':<30}{'untouched':>11}{'mutated':>10}  verdict")
    print("-" * 72)
    fails = []
    for name, gate, _script, mutate, args in CONTROLS:
        tmp = tempfile.mkdtemp(prefix="h10-maint-")
        try:
            rc_ok, _ = _exit(check, args, {})
            tool, note = mutate(tmp)
            # The maker is deliberately NOT overridden: the fixtures and the
            # seed manifest are the ground truth and are identical in both runs.
            rc_mut, _ = _exit(check, args, {"OBC_DIFF_TOOL": tool})
        except SystemExit as e:
            rc_ok, rc_mut, note = -1, -1, f"control error: {e}"
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
        ok = rc_ok == 0 and rc_mut != 0
        verdict = ("ok" if ok else
                   "NEVER PASSES" if rc_ok != 0 else "NEVER FAILS")
        print(f"{name:<30}{('exit ' + str(rc_ok)):>11}{('exit ' + str(rc_mut)):>10}"
              f"  {verdict}")
        print(f"{'':<30}gate {gate}; mutation: {note}")
        if not ok:
            fails.append(f"{name}: untouched exit {rc_ok}, mutated exit {rc_mut}")
    print()
    for f in fails:
        print(f"FAIL {f}")
    print(f"RESULT: {'PASS' if not fails else 'FAIL'}")
    return 0 if not fails else 1


PROMOTION = """
To install, after check45_diff.py is promoted to harden/checks/:

1. Copy m_diff_layout_blind, m_diff_text_blind and _sub into
   check35_controls.py part 2, beside m_capture and the others.
2. check35's _exit() runs `checks/<script>` relative to a scope directory and
   its scopes are verify/<vol>, `retrieval` and `harden`. These two controls
   need a fourth shape, because the working set they copy is tools/ and the
   check runs in place from the package root. Add a `maint` branch to
   run_subprocess_controls() alongside the existing `harden` branch:

       elif scope == "maint":
           d = _PKG
           rc_ok, _ = _exit(d, check, args, env)
           tool, note = mutate(tempfile.mkdtemp())
           rc_mut, last = _exit(d, check, args, {**env, "OBC_DIFF_TOOL": tool})

3. Append to SUBPROCESS_CONTROLS:

       ("check45_diff M2", "maint", "check45_diff.py",
        m_diff_layout_blind, ("--gate", "M2"), {}),
       ("check45_diff M2r", "maint", "check45_diff.py",
        m_diff_text_blind, ("--gate", "M2"), {}),

Until step 2 is made, check35 has no `maint` scope and these rows cannot simply
be pasted into the existing registry - they would fall through to _materialise()
and report NEVER PASSES with exit 2, which is a cwd error and not a check
failure. Stated here so the promoter does not diagnose it twice.
"""

if __name__ == "__main__":
    if "--promotion" in sys.argv:
        print(PROMOTION)
        sys.exit(0)
    sys.exit(run())
