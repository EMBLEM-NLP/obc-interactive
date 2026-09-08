#!/usr/bin/env bash
# Fetch the two Crown-copyright source PDFs in CI from secret URLs and verify
# them against the manifest hashes in ci/checks.yaml. The URLs never enter a
# transcript, .mcp.json, CLAUDE.md, or a hook. Exports OBC_SRC_V1/V2 for the
# gates that need them (G1, G8, V8, H9).
set -euo pipefail
cd "$(dirname "$0")/.."
[ -n "${OBC_PDF_URL_V1:-}" ] || { echo "OBC_PDF_URL_V1 unset; source gates will SKIP"; exit 0; }
mkdir -p /tmp/obc-src
python3 - <<'PY'
import os, yaml, hashlib, urllib.request
srcs = {x["rel"].split("/")[-1]: x for x in yaml.safe_load(open("ci/checks.yaml"))["sources"]}
for name, var in (("301880.pdf","OBC_PDF_URL_V1"),("301881.pdf","OBC_PDF_URL_V2")):
    url = os.environ.get(var)
    if not url: continue
    dst = f"/tmp/obc-src/{name}"
    urllib.request.urlretrieve(url, dst)
    got = hashlib.sha256(open(dst,"rb").read()).hexdigest()
    want = srcs[name]["sha256"]
    assert got == want, f"{name}: sha256 {got[:12]} != manifest {want[:12]} - refusing to run gates on an unverified source"
    print(f"{name}: fetched and verified against manifest")
PY
# $GITHUB_ENV only exists on a GitHub runner. Under `set -u` this script died
# with an unbound-variable error anywhere else, which made it untestable off-CI.
if [ -n "${GITHUB_ENV:-}" ]; then
  echo "OBC_SRC_V1=/tmp/obc-src/301880.pdf" >> "$GITHUB_ENV"
  echo "OBC_SRC_V2=/tmp/obc-src/301881.pdf" >> "$GITHUB_ENV"
else
  echo "Not on a GitHub runner. Export these yourself:"
  echo "  export OBC_SRC_V1=/tmp/obc-src/301880.pdf"
  echo "  export OBC_SRC_V2=/tmp/obc-src/301881.pdf"
fi
