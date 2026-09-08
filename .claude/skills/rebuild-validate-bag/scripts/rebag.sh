#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../../../.."
bash ci/regenerate.sh && touch .regen.stamp
BAG="${OBC_BAG:-$(pwd)/../bag}"
python3 - "$BAG" <<'PY'
import os, sys, shutil, hashlib, yaml, bagit
PKG=os.getcwd(); BAG=sys.argv[1]
srcs=yaml.safe_load(open("ci/checks.yaml"))["sources"]
if os.path.exists(BAG): shutil.rmtree(BAG)
shutil.copytree(PKG, BAG, ignore=shutil.ignore_patterns("__pycache__","out",".regen.stamp"))
bagit.make_bag(BAG, {"Bag-Software-Agent":"bagit.py + obc pipeline"}, checksums=["sha512","sha256"])
open(os.path.join(BAG,"fetch.txt"),"w").writelines(f"{x['url']} {x['size']} {x['rel']}\n" for x in srcs)
for alg in ("sha256","sha512"):
    open(os.path.join(BAG,f"manifest-{alg}.txt"),"a").writelines(f"{x[alg]}  {x['rel']}\n" for x in srcs)
bagit.Bag(BAG).save(manifests=False)
for alg in ("sha512","sha256"):
    ent=[f"{hashlib.new(alg,open(os.path.join(BAG,n),'rb').read()).hexdigest()}  {n}\n" for n in sorted(os.listdir(BAG)) if os.path.isfile(os.path.join(BAG,n)) and not n.startswith("tagmanifest-")]
    open(os.path.join(BAG,f"tagmanifest-{alg}.txt"),"w").writelines(ent)
print("bag:", BAG)
PY
OBC_BAG="$BAG" python3 harden/checks/check21_bagit.py | tail -1
OBC_PKG="$(pwd)" python3 harden/checks/check26_provenance.py | tail -1
