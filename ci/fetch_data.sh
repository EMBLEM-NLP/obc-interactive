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
#
#   bash ci/fetch_data.sh --where   prints which variable to set and what it
#                                   must point at, then exits 0 without fetching
set -euo pipefail
cd "$(dirname "$0")/.."

# --where: make the failure name its own remedy. Before this, a reader who hit
# "set OBC_DATA_TARBALL, OBC_DATA_DIR, or OBC_DATA_URL" was told three variable
# names and nothing about what any of them should contain, and README.md did not
# mention this script at all (track E9, gate DOC1).
if [ "${1:-}" = "--where" ]; then
  python3 - <<'WHERE'
import json, os, sys
man = json.load(open("data-manifest.json"))
files = man["files"]
absent = [r for r in files if not os.path.exists(r["path"])]
print(f"data-manifest.json lists {len(files)} files, {man['total_bytes']:,} bytes.")
print(f"{len(absent)} are absent from this tree"
      f"{' - nothing to fetch.' if not absent else ':'}")
for r in absent[:4]:
    print(f"    {r['bytes']:>11,}  {r['path']}")
if len(absent) > 4:
    print(f"    ... and {len(absent) - 4} more (harden/checks/check40_dataintegrity.py lists all)")
print()
print("Set exactly ONE of these, then re-run `bash ci/fetch_data.sh`:")
print()
print("  OBC_DATA_TARBALL   a URL or a local path to obc-interactive-data.tar.gz.")
print("                     Member paths inside it are relative to the package")
print("                     root, e.g. emitters/obc-mod.sqlite. Normal case.")
print("                       export OBC_DATA_TARBALL=/mnt/backup/obc-interactive-data.tar.gz")
print()
print("  OBC_DATA_DIR       a path to a tree that ALREADY holds these files at")
print("                     these same relative paths - another checkout, a")
print("                     mounted volume, a CI cache. No network.")
print("                       export OBC_DATA_DIR=/srv/obc-hydrated")
print()
print("  OBC_DATA_URL       a base URL serving one asset per file, with '/'")
print("                     replaced by '__' (release assets cannot contain a")
print("                     slash): $OBC_DATA_URL/emitters__obc-mod.sqlite")
print("                       export OBC_DATA_URL=https://<host>/<owner>/<repo>/releases/download/data-v1")
print()
print("Every file is verified against its sha256 in data-manifest.json before")
print("anything is installed; a mismatch aborts and leaves the tree untouched.")
print()
print("WHERE TO GET THE TARBALL: nowhere public, yet.")
print("  No release of the derived data has been published. The locations in the")
print("  header of this script are placeholders - `https://…/`, an ellipsis where")
print("  the host belongs. Gate DOC1-D2 is RED for exactly this reason and stays")
print("  red until a human publishes the artifact and writes its URL here.")
print("  Until then OBC_DATA_DIR is the only mode that needs no such URL, and it")
print("  needs someone to hand you a hydrated tree.")
sys.exit(0)
WHERE
  exit 0
fi

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
