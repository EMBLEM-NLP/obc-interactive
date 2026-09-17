#!/usr/bin/env bash
# Install the derived OBC corpus and verify it before use.
#
# Preferred mode — immutable versioned release manifest:
#
#   OBC_RELEASE_MANIFEST=data/releases/obc-corpus-2024.2025-01-16.json \
#   OBC_RELEASE_ARCHIVE=/path/to/obc-hydrated.zip \
#     bash ci/fetch_data.sh
#
# If OBC_RELEASE_ARCHIVE is omitted, ci/install_release.py downloads flat assets
# from OBC_RELEASE_BASE_URL or from artifact_base_url in the manifest.
#
# Legacy compatibility modes remain available while the current CI/data source
# migrates to the release contract:
#
#   OBC_DATA_TARBALL=https://…/obc-interactive-data.tar.gz  bash ci/fetch_data.sh
#   OBC_DATA_DIR=/path/to/a/full/tree                       bash ci/fetch_data.sh
#   OBC_DATA_URL=https://…/releases/download/data-v1        bash ci/fetch_data.sh
#
# Every mode verifies all requested files before installing any of them. Files
# already matching their manifest are skipped, so repeated installs are cheap.
set -euo pipefail
cd "$(dirname "$0")/.."

if [[ -n "${OBC_RELEASE_MANIFEST:-}" ]]; then
  args=(--manifest "$OBC_RELEASE_MANIFEST")
  if [[ -n "${OBC_RELEASE_ARCHIVE:-}" ]]; then
    args+=(--archive "$OBC_RELEASE_ARCHIVE")
  fi
  if [[ -n "${OBC_RELEASE_BASE_URL:-}" ]]; then
    args+=(--base-url "$OBC_RELEASE_BASE_URL")
  fi
  python3 ci/install_release.py "${args[@]}"
  # The versioned release may intentionally differ from the legacy
  # data-manifest.json snapshot. Its own manifest has already been verified;
  # check40 remains authoritative once data-manifest.json is migrated to the
  # same release version.
  exit 0
fi

python3 - <<'PY'
import json, os, sys, hashlib, shutil, tarfile, tempfile, urllib.request

man = json.load(open("data-manifest.json"))
tarball = os.environ.get("OBC_DATA_TARBALL")
local   = os.environ.get("OBC_DATA_DIR")
url     = os.environ.get("OBC_DATA_URL")
if not (tarball or local or url):
    sys.exit(
        "set OBC_RELEASE_MANIFEST (preferred), or one of "
        "OBC_DATA_TARBALL/OBC_DATA_DIR/OBC_DATA_URL"
    )

def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()

def correct(r):
    p = r["path"]
    return os.path.exists(p) and os.path.getsize(p) == r["bytes"] and sha(p) == r["sha256"]

need = [r for r in man["files"] if not correct(r)]
print(f"{len(man['files']) - len(need)} already correct; fetching {len(need)}")
if not need:
    sys.exit(0)

tmp = tempfile.mkdtemp()
try:
    if tarball:
        arc = os.path.join(tmp, "data.tar.gz")
        if tarball.startswith(("http://", "https://")):
            print(f"  downloading {tarball}")
            urllib.request.urlretrieve(tarball, arc)
        else:
            arc = tarball
        want = {r["path"] for r in need}
        with tarfile.open(arc) as tf:
            for m in tf.getmembers():
                name = m.name[2:] if m.name.startswith("./") else m.name
                if name not in want or not m.isfile():
                    continue
                if os.path.isabs(name) or ".." in name.split("/"):
                    sys.exit(f"refusing unsafe path in archive: {m.name}")
                m.name = name
                tf.extract(m, tmp)
        src_of = lambda r: os.path.join(tmp, r["path"])
    elif local:
        src_of = lambda r: os.path.join(local, r["path"])
    else:
        def src_of(r):
            dst = os.path.join(tmp, r["path"].replace("/", "__"))
            urllib.request.urlretrieve(f"{url}/{r['path'].replace('/', '__')}", dst)
            return dst

    staged = []
    for r in need:
        s = src_of(r)
        if not os.path.exists(s):
            sys.exit(f"FAIL {r['path']}: not present in the source ({s})")
        got = sha(s)
        if got != r["sha256"]:
            sys.exit(
                f"FAIL {r['path']}: sha256 {got[:12]} != manifest "
                f"{r['sha256'][:12]} - refusing to install unverified data"
            )
        staged.append((r, s))

    for r, s in staged:
        os.makedirs(os.path.dirname(r["path"]) or ".", exist_ok=True)
        shutil.copyfile(s, r["path"] + ".part")
        os.replace(r["path"] + ".part", r["path"])
        print(f"  ok {r['bytes']:>11,}  {r['path']}")
    print(f"all {len(staged)} files verified against data-manifest.json")
finally:
    shutil.rmtree(tmp, ignore_errors=True)
PY
python3 harden/checks/check40_dataintegrity.py --quick
