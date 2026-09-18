#!/usr/bin/env python3
"""Stage 6 - image asset export, classification, and figure binding.

Raster candidates are classified into semantic roles before packaging:
formal figures, front-matter graphics, inline equations, table-cell graphics,
or micro/non-figure rasterization artifacts. Soft masks are flattened onto a
white RGB background for portable PNG previews. Vector figures are clipped
losslessly to SVG plus a 300 dpi PNG preview.
"""
import pymupdf, gzip, json, os, re, sys, time
from collections import Counter

from image_assets import (
    MICRO_ROLE,
    classify_raster,
    image_tuple_for_box,
    normalize_designator,
    package_ref,
    role_directory,
    save_raster_portable,
)

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

# Accept both canonical "4.1.7.6.-G" and source typo "4.1.7.6-.G".
CAP = re.compile(
    r"^Figure\s+([A-Z]?-?\d+(?:\.\d+)*\.?(?:-\.?[A-Z0-9/]+)?)\s*(\(Cont)?",
    re.I,
)
FORM = re.compile(
    r"Forming Part of\s+(?:Sentence|Article|Subsection|Section|Clause)?s?\s*"
    r"([0-9]+(?:\.[0-9]+){1,4}[A-Z]?)\.?(?:\((\d+)\))?"
)


def output_target(role, base, suffix):
    directory = role_directory(role)
    if not directory:
        return None
    folder = os.path.join(OUTDIR, directory)
    os.makedirs(folder, exist_ok=True)
    return os.path.join(folder, base + suffix)


t0 = time.time()
assets = []
asset_bytes = 0

for p in sorted(geo):
    regions = geo[p]["figures"]
    if not regions:
        continue

    lines = sorted(
        (
            (l["b"], "".join(s["t"] for s in l["s"]).strip())
            for b in inv[p]["blocks"]
            for l in b["l"]
        ),
        key=lambda x: x[0][1],
    )
    caps = []
    for b, text in lines:
        match = CAP.match(text) if text else None
        if match:
            caps.append((b[1], normalize_designator(match.group(1)), text))

    forming = next(
        (FORM.search(text).group(1) for b, text in lines if text and FORM.search(text)),
        None,
    )
    page = doc[p - 1]
    table_boxes = geo[p].get("tables") or []

    for i, box in enumerate(regions):
        des = None
        below = [c for c in caps if c[0] >= box[3] - 4]
        above = [c for c in caps if c[0] < box[1] + 4]
        if below:
            des = below[0][1]
        elif above:
            des = above[-1][1]
        des = normalize_designator(des)

        image_tuple = image_tuple_for_box(page, box)
        kind = "raster" if image_tuple else "vector"
        source_width = int(image_tuple[2]) if image_tuple else None
        source_height = int(image_tuple[3]) if image_tuple else None

        if kind == "raster":
            role = classify_raster(
                page=p,
                width=source_width,
                height=source_height,
                box=box,
                designator=des,
                table_boxes=table_boxes,
            )
        else:
            role = "formal_figure" if des else "inline_equation"

        safe_des = (des or "unnamed").replace("/", "-")
        base = f"p{p:04d}_{i}_{safe_des}"
        files = []
        rendering = {"xref": None, "smask": 0, "soft_mask_flattened": False}

        if kind == "raster" and role != MICRO_ROLE:
            target = output_target(role, base, ".png")
            try:
                rendering = save_raster_portable(doc, page, image_tuple, target)
                files.append(package_ref(role, os.path.basename(target)))
                asset_bytes += os.path.getsize(target)
            except Exception as exc:
                kind = "raster-failed"
                rendering["error"] = str(exc)

        elif kind == "vector":
            svg_target = output_target(role, base, ".svg")
            png_target = output_target(role, base, ".png")
            clip = pymupdf.Rect(*box) + (-3, -3, 3, 3)
            tmp = pymupdf.open()
            tmp.insert_pdf(doc, from_page=p - 1, to_page=p - 1)
            tmp[0].set_cropbox(clip)
            open(svg_target, "w", encoding="utf-8").write(
                tmp[0].get_svg_image(text_as_path=False)
            )
            tmp.close()
            page.get_pixmap(dpi=300, clip=clip).save(png_target)
            files.extend([
                package_ref(role, os.path.basename(svg_target)),
                package_ref(role, os.path.basename(png_target)),
            ])
            asset_bytes += os.path.getsize(svg_target) + os.path.getsize(png_target)

        assets.append(
            {
                "page": p,
                "region": i,
                "designator": des,
                "kind": kind,
                "asset_role": role,
                "box": box,
                "forming_part_of": forming,
                "source_width": source_width,
                "source_height": source_height,
                "xref": rendering.get("xref"),
                "smask": rendering.get("smask", 0),
                "soft_mask_flattened": rendering.get("soft_mask_flattened", False),
                "files": [f for f in files if f],
            }
        )

with gzip.open("out/figures.jsonl.gz", "wt", encoding="utf-8") as fh:
    fh.write(
        json.dumps(
            {
                "_meta": True,
                "assets": len(assets),
                "packaged_files": sum(len(a["files"]) for a in assets),
                "roles": dict(Counter(a["asset_role"] for a in assets)),
            }
        )
        + "\n"
    )
    for asset in assets:
        fh.write(json.dumps(asset) + "\n")

kinds = Counter(a["kind"] for a in assets)
roles = Counter(a["asset_role"] for a in assets)
named = sum(1 for a in assets if a["designator"])
print(f"image regions classified: {len(assets)}  kinds={dict(kinds)}")
print(f"  roles                : {dict(roles)}")
print(f"  captioned figures    : {named}")
print(f"  packaged files       : {sum(len(a['files']) for a in assets)}")
print(f"  bytes on disk        : {asset_bytes/1e6:.1f} MB")
print(f"-> out/figures.jsonl.gz, out/assets/  {time.time()-t0:.0f}s")
