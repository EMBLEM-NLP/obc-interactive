#!/usr/bin/env python3
"""Recover and validate classified image assets referenced by figures JSONL."""
from __future__ import annotations
import argparse, gzip, hashlib, json, sys
from pathlib import Path
import pymupdf
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "pipeline"))
from image_assets import (MICRO_ROLE, image_tuple_for_box, normalize_designator,
                          package_ref, role_directory, save_raster_portable)

def load_records(path):
    rows=[json.loads(x) for x in gzip.open(path,"rt",encoding="utf-8") if x.strip()]
    if not rows or not rows[0].get("_meta"): raise RuntimeError("missing metadata header")
    return rows[0], rows[1:]

def sha256(path):
    h=hashlib.sha256()
    with open(path,"rb") as fh:
        for c in iter(lambda: fh.read(1<<20), b""): h.update(c)
    return h.hexdigest()

def target_for(out_root, ref, role):
    if ref:
        parts=Path(ref).parts
        if len(parts)>=3 and parts[0]=="assets": return out_root / Path(*parts[1:])
    d=role_directory(role)
    return out_root / d / Path(ref or "asset.png").name if d else None

def recover(pdf_path, metadata_path, out_root):
    _, records=load_records(metadata_path)
    out_root.mkdir(parents=True, exist_ok=True)
    doc=pymupdf.open(pdf_path)
    manifest=[]
    for rec in records:
        role=rec.get("asset_role") or ("formal_figure" if rec.get("designator") else "inline_equation")
        rec["designator"]=normalize_designator(rec.get("designator"))
        if role==MICRO_ROLE:
            if rec.get("files"): raise RuntimeError("micro_nonfigure record must not package files")
            continue
        page=doc[int(rec["page"])-1]
        kind=rec.get("kind")
        refs=rec.get("files") or []
        if kind=="raster":
            image=image_tuple_for_box(page,rec["box"])
            if not image: raise RuntimeError(f"no raster match page {rec['page']}")
            if not refs:
                name=f"p{int(rec['page']):04d}_{rec.get('region',0)}_{rec.get('designator') or 'unnamed'}.png".replace("/","-")
                refs=[package_ref(role,name)]
            for ref in refs:
                target=target_for(out_root,ref,role); target.parent.mkdir(parents=True,exist_ok=True)
                rendering=save_raster_portable(doc,page,image,target)
                manifest.append({"path":f"assets/{target.relative_to(out_root).as_posix()}","bytes":target.stat().st_size,"sha256":sha256(target),"role":role,**rendering})
        elif kind=="vector":
            # vector recovery remains clip-based
            clip=pymupdf.Rect(*rec["box"])+(-3,-3,3,3)
            for ref in refs:
                target=target_for(out_root,ref,role); target.parent.mkdir(parents=True,exist_ok=True)
                if target.suffix.lower()==".png": page.get_pixmap(dpi=300,clip=clip).save(target)
                elif target.suffix.lower()==".svg":
                    tmp=pymupdf.open(); tmp.insert_pdf(doc,from_page=rec["page"]-1,to_page=rec["page"]-1); tmp[0].set_cropbox(clip)
                    target.write_text(tmp[0].get_svg_image(text_as_path=False),encoding="utf-8"); tmp.close()
                else: raise RuntimeError(f"unsupported vector extension {target}")
                manifest.append({"path":f"assets/{target.relative_to(out_root).as_posix()}","bytes":target.stat().st_size,"sha256":sha256(target),"role":role})
        else: raise RuntimeError(f"unsupported kind {kind}")
    doc.close()
    lines=[f"{x['sha256']}  {Path(x['path']).relative_to('assets').as_posix()}" for x in manifest]
    (out_root/"MANIFEST.sha256").write_text("\n".join(lines)+"\n",encoding="utf-8")
    (out_root/"manifest.json").write_text(json.dumps({"schema_version":2,"count":len(manifest),"items":manifest},indent=2,sort_keys=True)+"\n",encoding="utf-8")
    return manifest

def validate(metadata_path,out_root):
    _,records=load_records(metadata_path); failures=[]; expected=set()
    for rec in records:
        role=rec.get("asset_role")
        files=rec.get("files") or []
        if role==MICRO_ROLE and files:
            failures.append(f"micro_nonfigure has files page {rec.get('page')}")
        if role!=MICRO_ROLE and not files:
            failures.append(
                f"packageable asset has no files page {rec.get('page')} "
                f"role={role or 'unknown'} designator={rec.get('designator')}"
            )
        for ref in files:
            rel=Path(ref).relative_to("assets") if str(ref).startswith("assets/") else Path(role_directory(role) or "figures-v1")/Path(ref).name
            expected.add(rel.as_posix())
    mp=out_root/"MANIFEST.sha256"; hashes={}
    if not mp.exists(): failures.append("missing assets/MANIFEST.sha256")
    else:
        for line in mp.read_text(encoding="utf-8").splitlines():
            if line.strip():
                h,rel=line.split(None,1); hashes[rel.strip()]=h
    for rel in sorted(expected):
        p=out_root/rel
        if not p.is_file(): failures.append(f"missing assets/{rel}"); continue
        if p.stat().st_size==0: failures.append(f"empty assets/{rel}")
        elif hashes.get(rel)!=sha256(p): failures.append(f"hash mismatch assets/{rel}")
    for rel in sorted(set(hashes)-expected): failures.append(f"unreferenced manifest asset {rel}")
    return failures,len(expected)

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--pdf"); ap.add_argument("--metadata",required=True); ap.add_argument("--out",required=True); ap.add_argument("--validate-only",action="store_true"); a=ap.parse_args()
    try:
        if a.validate_only:
            failures,n=validate(Path(a.metadata),Path(a.out)); print(f"packaged asset references: {n}"); print(f"invalid assets: {len(failures)}"); [print("  "+x) for x in failures[:10]]; print("RESULT:","PASS" if not failures else f"FAIL {len(failures)}"); return 0 if not failures else 1
        if not a.pdf: raise RuntimeError("--pdf required")
        items=recover(Path(a.pdf),Path(a.metadata),Path(a.out)); print(f"assets recovered: {len(items)}"); print("RESULT: PASS"); return 0
    except Exception as exc: print(f"RESULT: FAIL - {exc}"); return 1
if __name__=="__main__": raise SystemExit(main())
