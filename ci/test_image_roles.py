#!/usr/bin/env python3
"""No-data controls for E6c image roles, naming, rendering, and Stage 6 runtime."""
import gzip, json, subprocess, sys, tempfile
from pathlib import Path
import pymupdf
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"pipeline"))
from image_assets import classify_raster, flatten_rgb_with_mask, normalize_designator

def main():
    failures=[]
    if normalize_designator("4.1.7.6-.G")!="4.1.7.6.-G": failures.append("Figure G punctuation not normalized")
    if classify_raster(page=27,width=6,height=1,box=[0,0,6,1],designator=None,table_boxes=[])!="micro_nonfigure": failures.append("6x1 micro raster promoted")
    if classify_raster(page=608,width=40,height=40,box=[10,10,50,50],designator=None,table_boxes=[[0,0,100,100]])!="table_cell_graphic": failures.append("table raster not classified")
    if classify_raster(page=501,width=100,height=50,box=[0,0,100,50],designator="4.1.7.6-.G",table_boxes=[])!="formal_figure": failures.append("formal figure not classified")
    if classify_raster(page=180,width=100,height=40,box=[0,0,100,40],designator=None,table_boxes=[])!="inline_equation": failures.append("inline equation not classified")
    if classify_raster(page=2,width=100,height=40,box=[0,0,100,40],designator=None,table_boxes=[])!="front_matter": failures.append("front matter not classified")
    out=flatten_rgb_with_mask(bytes([0,0,0,0,0,0]),bytes([0,255]),3)
    if out!=bytes([255,255,255,0,0,0]): failures.append("soft-mask flattening is not white/black portable RGB")

    with tempfile.TemporaryDirectory() as td:
        td=Path(td); (td/"out").mkdir()
        pdf=td/"fixture.pdf"; d=pymupdf.open(); p=d.new_page(width=200,height=200); p.draw_rect(pymupdf.Rect(30,30,150,150),color=(0,0,0),width=2); d.save(pdf); d.close()
        inv=[{"_meta":True,"pages":1},{"page":1,"rect":[0,0,200,200],"blocks":[],"images":[]}]
        geo=[{"page":1,"roles":{},"tables":[],"figures":[[30,30,150,150]],"columns":[]}]
        with gzip.open(td/"out/inventory.jsonl.gz","wt",encoding="utf-8") as fh:
            for r in inv: fh.write(json.dumps(r)+"\n")
        with gzip.open(td/"out/geometry.jsonl.gz","wt",encoding="utf-8") as fh:
            for r in geo: fh.write(json.dumps(r)+"\n")
        r=subprocess.run([sys.executable,str(ROOT/"pipeline/stage6_figures.py"),str(pdf)],cwd=td,capture_output=True,text=True,timeout=30)
        if r.returncode!=0: failures.append("Stage 6 synthetic runtime failed: "+(r.stderr or r.stdout)[-300:])
        elif not (td/"out/figures.jsonl.gz").exists(): failures.append("Stage 6 synthetic runtime produced no metadata")

    print("Figure G normalization : checked")
    print("role classifier        : checked")
    print("soft-mask compositor   : checked")
    print("Stage 6 runtime        : checked")
    for x in failures: print("  FAIL",x)
    print("RESULT:","PASS" if not failures else f"FAIL {len(failures)}")
    return 0 if not failures else 1
if __name__=="__main__": raise SystemExit(main())
