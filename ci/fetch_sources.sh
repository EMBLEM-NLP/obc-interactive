#!/usr/bin/env bash
# Fetch the two Crown-copyright source PDFs and verify them against the sha256
# recorded in ci/checks.yaml. Exports OBC_SRC_V1/V2 for the gates that need them
# (G1, G8, V8, H9).
#
# Two sources of the URL, in order:
#
#   1. OBC_PDF_URL_V1 / OBC_PDF_URL_V2, if set. These stay in secrets and never
#      enter a transcript, .mcp.json, CLAUDE.md, or a hook. Use them when the
#      documents are served from somewhere that is not public - a mirror, an
#      internal artifact store.
#   2. Otherwise the `url` already recorded beside each source in ci/checks.yaml.
#
# The fallback is deliberate and it is not a weakening. Those URLs are Publications
# Ontario's own free-download links; they are committed in ci/checks.yaml with the
# size and sha256 of what they must serve, and printed again in README.md under
# Licence and attribution as the official sources. Requiring a secret to reach a
# document the repository already publishes twice made four gates - G1, V8, H9 and
# G8 - skip on every run for no reason anyone could act on.
#
# What is NOT negotiable is the verification. Whichever URL is used, the bytes are
# hashed and compared against ci/checks.yaml before anything is exported, and a
# mismatch aborts. A gate must never run over an unverified source.
#
# The documents themselves remain fetch-only: fetched at need, never committed,
# never redistributed. This script writes them to a scratch directory and nothing
# else in the repository reads them by path.
set -euo pipefail
cd "$(dirname "$0")/.."
DEST="${OBC_SRC_CACHE:-/tmp/obc-src}"
mkdir -p "$DEST"

python3 - "$DEST" <<'PY'
import hashlib, os, sys, urllib.request
import yaml

dest = sys.argv[1]
srcs = {x["rel"].split("/")[-1]: x for x in yaml.safe_load(open("ci/checks.yaml"))["sources"]}
fail = 0

def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()

for name, var in (("301880.pdf", "OBC_PDF_URL_V1"), ("301881.pdf", "OBC_PDF_URL_V2")):
    rec = srcs[name]
    want = rec["sha256"]
    dst = os.path.join(dest, name)

    # Already here and correct: do not download it again. The previous version
    # re-fetched ~43 MB on every run, including reruns of the same commit, from
    # a public-sector server that gains nothing from the traffic.
    if os.path.exists(dst) and sha256(dst) == want:
        print(f"  {name}: already present and verified, not re-downloaded")
        continue

    url, where = os.environ.get(var), "secret " + var
    if not url:
        url, where = rec["url"], "ci/checks.yaml"
    print(f"  {name}: fetching, url from {where}")
    try:
        urllib.request.urlretrieve(url, dst)
    except Exception as exc:                       # noqa: BLE001 - the reason is the point
        print(f"  {name}: FETCH FAILED - {type(exc).__name__}: {exc}")
        fail = 1
        continue

    got = sha256(dst)
    if got != want:
        # Never leave an unverified file where a gate might read it.
        os.remove(dst)
        print(f"  {name}: sha256 {got[:12]} != recorded {want[:12]} - refusing to run "
              f"gates on an unverified source; the file has been deleted")
        fail = 1
        continue
    print(f"  {name}: verified against ci/checks.yaml ({rec['size']:,} bytes)")

sys.exit(fail)
PY

# $GITHUB_ENV only exists on a GitHub runner. Under `set -u` this script died with
# an unbound-variable error anywhere else, which made it untestable off-CI.
if [ -n "${GITHUB_ENV:-}" ]; then
  echo "OBC_SRC_V1=$DEST/301880.pdf" >> "$GITHUB_ENV"
  echo "OBC_SRC_V2=$DEST/301881.pdf" >> "$GITHUB_ENV"
else
  echo "Not on a GitHub runner. Export these yourself:"
  echo "  export OBC_SRC_V1=$DEST/301880.pdf"
  echo "  export OBC_SRC_V2=$DEST/301881.pdf"
fi
