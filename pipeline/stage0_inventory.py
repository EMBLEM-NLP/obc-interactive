#!/usr/bin/env python3
"""Stage 0 - page inventory.

Reads the PRISTINE source PDF and records what is physically on each page:
text spans with font/size/bbox, vector drawing primitives, raster images and
existing link annotations. Nothing is interpreted. Every later stage reads this
file, never the PDF, so the interpretation layers can be rerun cheaply and are
reproducible from source.
"""
import pymupdf, gzip, json, sys, time, hashlib, os

SRC = sys.argv[1] if len(sys.argv) > 1 else "/mnt/user-data/uploads/301880.pdf"
OUT = sys.argv[2] if len(sys.argv) > 2 else "out/inventory.jsonl.gz"

def rd(v, n=2):
    return round(float(v), n)

def main():
    t0 = time.time()
    doc = pymupdf.open(SRC)
    src_sha = hashlib.sha256(open(SRC, "rb").read()).hexdigest()[:16]
    os.makedirs(os.path.dirname(OUT) or ".", exist_ok=True)
    nspan = nline = ndraw = nimg = nlink = 0
    with gzip.open(OUT, "wt", encoding="utf-8") as fh:
        fh.write(json.dumps({
            "_meta": True, "source": os.path.basename(SRC), "sha256_16": src_sha,
            "pages": doc.page_count, "pymupdf": pymupdf.__doc__.strip()[:40],
            "generated": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }) + "\n")
        for i in range(doc.page_count):
            page = doc[i]
            rect = page.rect
            blocks = []
            d = page.get_text("dict")
            for b in d["blocks"]:
                if b["type"] != 0:
                    continue
                lines = []
                for l in b["lines"]:
                    spans = []
                    for s in l["spans"]:
                        if not s["text"]:
                            continue
                        spans.append({
                            "t": s["text"],
                            "b": [rd(x) for x in s["bbox"]],
                            "f": s["font"], "sz": rd(s["size"], 1),
                            "c": s["color"], "fl": s["flags"],
                        })
                        nspan += 1
                    if spans:
                        lines.append({"b": [rd(x) for x in l["bbox"]],
                                      "d": rd(l.get("dir", (1, 0))[0], 3),
                                      "s": spans})
                        nline += 1
                if lines:
                    blocks.append({"b": [rd(x) for x in b["bbox"]], "l": lines})
            # vector primitives, reduced to what the geometry stage needs
            draws = []
            for g in page.get_drawings():
                r = g["rect"]
                draws.append({
                    "b": [rd(r.x0), rd(r.y0), rd(r.x1), rd(r.y1)],
                    "ty": g["type"],                      # f | s | fs
                    "fill": g.get("fill") is not None,
                    "w": rd(g.get("width") or 0, 2),
                    "n": len(g.get("items") or []),
                })
                ndraw += 1
            images = []
            for im in page.get_images(full=True):
                try:
                    bb = page.get_image_bbox(im)
                    bbox = [rd(bb.x0), rd(bb.y0), rd(bb.x1), rd(bb.y1)]
                except Exception:
                    bbox = None
                images.append({"xref": im[0], "w": im[2], "h": im[3], "b": bbox})
                nimg += 1
            links = []
            for l in page.get_links():
                links.append({"k": l["kind"], "b": [rd(x) for x in l["from"]],
                              "p": l.get("page"), "uri": l.get("uri"),
                              "file": l.get("file")})
                nlink += 1
            fh.write(json.dumps({
                "page": i + 1,
                "rect": [rd(rect.x0), rd(rect.y0), rd(rect.x1), rd(rect.y1)],
                "rot": page.rotation,
                "blocks": blocks, "draws": draws, "images": images, "links": links,
            }, ensure_ascii=False) + "\n")
            if (i + 1) % 250 == 0:
                print(f"  ...{i+1} pages  {time.time()-t0:.0f}s", flush=True)
    print(f"stage0: {doc.page_count} pages | spans {nspan} lines {nline} "
          f"draws {ndraw} images {nimg} links {nlink}")
    print(f"        -> {OUT}  {os.path.getsize(OUT)/1e6:.1f} MB  {time.time()-t0:.0f}s")

if __name__ == "__main__":
    main()
