#!/usr/bin/env bash
# Fetch the derived binaries listed in data-manifest.json and verify each one.
#
# The repo is ~400 KB of code; the data is ~323 MB and lives outside git - see
# .gitattributes for why (no Git LFS). Three source modes, in the order you are
# most likely to use them:
#
#   OBC_DATA_TARBALL=https://…/obc-interactive-data.tar.gz  bash ci/fetch_data.sh
#   OBC_DATA_DIR=/path/to/a/full/tree                       bash ci/fetch_data.sh
#   OBC_DATA_URL=https://…/releases/download/data-v1        bash ci/fetch_data.sh
#
# TARBALL is the normal case and matches the artifact this project ships. URL
# mode expects one asset per file, named by replacing "/" with "__"
# (emitters__obc-mod.sqlite), because release assets cannot contain slashes.
#
# Every file is checked against data-manifest.json before it is installed;
# a mismatch aborts and leaves the tree untouched. Files already correct are
# skipped, so this is cheap to re-run and safe in a cached CI step.
set -euo pipefail
cd "$(dirname "$0")/.."
python3 - <<'PY'
import json, os, sys, hashlib, shutil, tarfile, tempfile, urllib.request

man = json.load(open("data-manifest.json"))
tarball = os.environ.get("OBC_DATA_TARBALL")
local   = os.environ.get("OBC_DATA_DIR")
url     = os.environ.get("OBC_DATA_URL")
if not (tarball or local or url):
    sys.exit("set OBC_DATA_TARBALL, OBC_DATA_DIR, or OBC_DATA_URL (see the header of this script)")

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
            # extract only what the manifest asks for, and never outside the tree
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
            sys.exit(f"FAIL {r['path']}: sha256 {got[:12]} != manifest {r['sha256'][:12]} - refusing to install unverified data")
        staged.append((r, s))

    # verify everything before installing anything, so a bad archive cannot
    # leave the tree half-updated
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
