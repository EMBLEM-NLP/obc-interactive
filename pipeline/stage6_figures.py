#!/usr/bin/env python3
"""Stage 6 - figure export and binding.

Raster figures are pulled by xref at native resolution. Vector figures are
clipped from the page to SVG (lossless) plus a 300 dpi PNG for preview -
pdfimages sees none of these, and most of Part 4 is vector.
"""
import pymupdf, gzip, json, os, re, sys, time

SRC = sys.argv[1] if len(sys.argv) > 1 else "/mnt/user-data/uploads/301880.pdf"
OUTDIR = "out/assets"
os.makedirs(OUTDIR, exist_ok=True)
doc = pymupdf.open(SRC)
inv, geo = {}, {}
for line in gzip.open("out/inventory.jsonl.gz", "rt"):
    r = json.loads(line)
    if not r.get("_meta"):
        inv[r["page"]] = r
for line in gzip.open("out/geometry.jsonl.gz", "rt"):
    r = json.loads(line)
    geo[r["page"]] = r

CAP = re.compile(r"^Figure\s+([A-Z]?-?\d+(?:\.\d+)*\.?(?:-[A-Z0-9/]+)?)\s*(\(Cont)?", re.I)
FORM = re.compile(r"Forming Part of\s+(?:Sentence|Article|Subsection|Section|Clause)?s?\s*"
                  r"([0-9]+(?:\.[0-9]+){1,4}[A-Z]?)\.?(?:\((\d+)\))?")

t0 = time.time()
assets = []
for p in sorted(geo):
    regions = geo[p]["figures"]
    if not regions:
        continue
    lines = sorted(((l["b"], "".join(s["t"] for s in l["s"]).strip())
                    for b in inv[p]["blocks"] for l in b["l"]), key=lambda x: x[0][1])
    caps = [(b[1], CAP.match(t).group(1).rstrip("."), t) for b, t in lines if t and CAP.match(t)]
    forming = next((FORM.search(t).group(1) for b, t in lines if t and FORM.search(t)), None)
    page = doc[p - 1]
    xrefs = {tuple(round(v, 1) for v in (im["b"] or [0, 0, 0, 0])): im["xref"]
             for im in inv[p]["images"] if im["b"]}
    for i, box in enumerate(regions):
        key = tuple(round(v, 1) for v in box)
        des = None
        below = [c for c in caps if c[0] >= box[3] - 4]
        above = [c for c in caps if c[0] < box[1] + 4]
        if below:
            des = below[0][1]
        elif above:
            des = above[-1][1]
        stem = f"{OUTDIR}/p{p:04d}_{i}_{(des or 'unnamed').replace('/','-')}"
        kind, files = None, []
        if key in xrefs:
            kind = "raster"
            try:
                pix = pymupdf.Pixmap(doc, xrefs[key])
                if pix.n - pix.alpha > 3:
                    pix = pymupdf.Pixmap(pymupdf.csRGB, pix)
                pix.save(stem + ".png")
                files.append(stem + ".png")
            except Exception as e:
                kind = "raster-failed"
        else:
            kind = "vector"
            clip = pymupdf.Rect(*box) + (-3, -3, 3, 3)
            # SVG has no clip argument, so crop a one-page copy and export that
            tmp = pymupdf.open()
            tmp.insert_pdf(doc, from_page=p - 1, to_page=p - 1)
            tmp[0].set_cropbox(clip)
            open(stem + ".svg", "w").write(tmp[0].get_svg_image(text_as_path=False))
            tmp.close()
            page.get_pixmap(dpi=300, clip=clip).save(stem + ".png")
            files += [stem + ".svg", stem + ".png"]
        assets.append({"page": p, "region": i, "designator": des, "kind": kind,
                       "box": box, "forming_part_of": forming, "files": files})

with gzip.open("out/figures.jsonl.gz", "wt", encoding="utf-8") as fh:
    fh.write(json.dumps({"_meta": True, "assets": len(assets)}) + "\n")
    for a in assets:
        fh.write(json.dumps(a) + "\n")
from collections import Counter
c = Counter(a["kind"] for a in assets)
named = sum(1 for a in assets if a["designator"])
print(f"figure regions exported : {len(assets)}  {dict(c)}")
print(f"  with a Figure caption : {named}")
print(f"  bytes on disk         : {sum(os.path.getsize(f) for a in assets for f in a['files'])/1e6:.1f} MB")
print(f"-> out/figures.jsonl.gz, out/assets/  {time.time()-t0:.0f}s")
