#!/usr/bin/env python3
"""Synthetic control for classified image-asset packaging."""
import gzip, hashlib, json, subprocess, sys, tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; VALIDATOR=ROOT/"ci/recover_figure_assets.py"
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def run(meta,root): return subprocess.run([sys.executable,str(VALIDATOR),"--metadata",str(meta),"--out",str(root),"--validate-only"],capture_output=True,text=True,timeout=30)
def main():
    failures=[]
    with tempfile.TemporaryDirectory() as td:
        root=Path(td); meta=root/"figures-v1.jsonl.gz"; assets=root/"assets"; fig=assets/"figures-v1"; fig.mkdir(parents=True)
        rows=[{"_meta":True,"assets":2},{"page":1,"region":0,"designator":"A-1","kind":"raster","asset_role":"formal_figure","box":[10,10,20,20],"files":["assets/figures-v1/a.png"]},{"page":2,"region":0,"designator":None,"kind":"raster","asset_role":"micro_nonfigure","box":[1,1,2,2],"files":[]}]
        with gzip.open(meta,"wt",encoding="utf-8") as fh:
            for x in rows: fh.write(json.dumps(x)+"\n")
        p=fig/"a.png"; p.write_bytes(b"fixture")
        (assets/"MANIFEST.sha256").write_text(f"{sha(p)}  figures-v1/a.png\n",encoding="utf-8")
        if run(meta,assets).returncode!=0: failures.append("complete classified set did not validate")
        p.unlink()
        if run(meta,assets).returncode==0: failures.append("missing asset stayed green")
        p.write_bytes(b"corrupt")
        if run(meta,assets).returncode==0: failures.append("corrupt asset stayed green")
    print("RESULT:","PASS" if not failures else f"FAIL {len(failures)}")
    [print("  FAIL",x) for x in failures]
    return 0 if not failures else 1
if __name__=="__main__": raise SystemExit(main())
