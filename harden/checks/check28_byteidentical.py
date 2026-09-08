#!/usr/bin/env python3
"""Check 28 (H1b) - two builds of the interactive PDF are byte-identical.

Split from check20 because the double rebuild exceeds the ledger's 120s default
and a gate that times out names the wrong thing. Two fixes were needed to make
this pass: SOURCE_DATE_EPOCH for the /Info timestamps, and no_new_id=True to stop
MuPDF writing a fresh random /ID trailer on every save - the last source of
nondeterminism, found by diffing the two builds byte by byte.
"""
import sys, os, subprocess, hashlib, shutil, tempfile
# Paths resolve from the package root with env-var overrides, so this check
# runs from the shipped bag. Before 2026-09-07 it hardcoded build-session
# paths and could not be re-run by anyone who received the artifact.
_PKG = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
env = dict(os.environ, PYTHONHASHSEED="0", SOURCE_DATE_EPOCH="1737072000", TZ="UTC")
def sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()
# stage8b_inject.py rebuilds the PDF from the source; without it this check
# cannot run. Fail with the reason, not a CalledProcessError from a subprocess.
for _v in ("OBC_SRC_V1",):
    if not os.environ.get(_v) or not os.path.exists(os.environ[_v]):
        print(f"RESULT: FAIL - set {_v} to the path of the source PDF; it is fetch-only (see fetch.txt)")
        sys.exit(1)

tmp = tempfile.mkdtemp()
fails = []
rebuilt = os.path.join(tmp, "rebuild.pdf")
subprocess.run([sys.executable, "stage8b_inject.py"], cwd=os.environ.get("OBC_BUILD_V1", os.path.join(_PKG, "pipeline")),
               env=env, capture_output=True, check=True)
shutil.copy(os.environ.get("OBC_BUILT_V1", os.path.join(_PKG, "pdf/301880_built_from_model.pdf")), rebuilt)
same = sha(rebuilt) == sha("/tmp/a.pdf") if os.path.exists("/tmp/a.pdf") else None
h1 = sha(rebuilt)
subprocess.run([sys.executable, "stage8b_inject.py"], cwd=os.environ.get("OBC_BUILD_V1", os.path.join(_PKG, "pipeline")),
               env=env, capture_output=True, check=True)
h2 = sha(os.environ.get("OBC_BUILT_V1", os.path.join(_PKG, "pdf/301880_built_from_model.pdf")))
print(f"pdf v1 rebuilt twice: {'byte-identical' if h1 == h2 else 'DIFFERS'} ({h1[:12]})")
if h1 != h2:
    fails.append("two builds of volume 1 are not byte-identical")

shutil.rmtree(tmp, ignore_errors=True)
print("RESULT:", "PASS" if not fails else f"FAIL {fails}")
sys.exit(0 if not fails else 1)
