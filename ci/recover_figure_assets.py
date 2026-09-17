#!/usr/bin/env python3
"""Recover figure assets referenced by figures JSONL from a generated PDF.

The figure model records page + bounding box + output filenames. Earlier
hydrated packages shipped the metadata but dropped pipeline/out/assets. This
tool reconstructs those files from the generated PDF without needing the
original transient pipeline directory.

It accepts both legacy refs (out/assets/foo.png) and canonical package refs
(assets/figures-v1/foo.png). Output filenames are always the basename of the
reference; callers choose the destination directory.

Raster records are recovered from their embedded image xref at native
resolution. Vector records are regenerated as SVG plus a 300 dpi PNG preview
from the recorded bounding box.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
from pathlib import Path
import sys

import pymupdf


def load_records(path: Path) -> tuple[dict, list[dict]]:
    rows = [json.loads(line) for line in gzip.open(path, "rt", encoding="utf-8") if line.strip()]
    if not rows or not rows[0].get("_meta"):
        raise RuntimeError(f"{path} has no figure metadata header")
    return rows[0], rows[1:]


def canonical_ref(value: str) -> str:
    return f"assets/figures-v1/{Path(value).name}"


def bbox_distance(a, b) -> float:
    return max(abs(float(a[i]) - float(b[i])) for i in range(4))


def embedded_xref(page, box, tolerance=0.30):
    images = [im for im in page.get_image_info(xrefs=True) if im.get("xref")]
    if not images:
        return None
    best = min(images, key=lambda im: bbox_distance(im["bbox"], box))
    return best["xref"] if bbox_distance(best["bbox"], box) <= tolerance else None


def save_raster(doc, page, record, target: Path) -> None:
    xref = embedded_xref(page, record["box"])
    if not xref:
        raise RuntimeError(
            f"page {record['page']} region {record.get('region')}: "
            "no embedded raster image matches the recorded bounding box"
        )
    pix = pymupdf.Pixmap(doc, xref)
    if pix.n - pix.alpha > 3:
        pix = pymupdf.Pixmap(pymupdf.csRGB, pix)
    pix.save(target)


def save_vector(doc, page, record, target: Path) -> None:
    clip = pymupdf.Rect(*record["box"]) + (-3, -3, 3, 3)
    if target.suffix.lower() == ".svg":
        tmp = pymupdf.open()
        tmp.insert_pdf(doc, from_page=record["page"] - 1, to_page=record["page"] - 1)
        tmp[0].set_cropbox(clip)
        target.write_text(tmp[0].get_svg_image(text_as_path=False), encoding="utf-8")
        tmp.close()
    elif target.suffix.lower() == ".png":
        page.get_pixmap(dpi=300, clip=clip).save(target)
    else:
        raise RuntimeError(f"unsupported vector asset extension: {target.suffix}")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def recover(pdf_path: Path, metadata_path: Path, out_dir: Path) -> list[dict]:
    _, records = load_records(metadata_path)
    out_dir.mkdir(parents=True, exist_ok=True)
    doc = pymupdf.open(pdf_path)
    manifest = []

    for record in records:
        files = record.get("files") or []
        if not files:
            raise RuntimeError(
                f"page {record.get('page')} region {record.get('region')} has no asset references"
            )
        page = doc[int(record["page"]) - 1]
        for ref in files:
            target = out_dir / Path(ref).name
            kind = record.get("kind")
            if kind == "raster":
                if target.suffix.lower() != ".png":
                    raise RuntimeError(f"raster asset must be PNG: {ref}")
                save_raster(doc, page, record, target)
            elif kind == "vector":
                save_vector(doc, page, record, target)
            else:
                raise RuntimeError(f"cannot recover figure kind {kind!r}: {ref}")

            if not target.is_file() or target.stat().st_size == 0:
                raise RuntimeError(f"recovered empty asset: {target}")
            manifest.append(
                {
                    "path": canonical_ref(ref),
                    "page": int(record["page"]),
                    "region": record.get("region"),
                    "designator": record.get("designator"),
                    "kind": kind,
                    "bytes": target.stat().st_size,
                    "sha256": sha256(target),
                }
            )

    doc.close()
    lines = [f"{item['sha256']}  {Path(item['path']).name}" for item in manifest]
    (out_dir / "MANIFEST.sha256").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (out_dir / "manifest.json").write_text(
        json.dumps(
            {"schema_version": 1, "asset_set": "figures-v1", "count": len(manifest), "items": manifest},
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    return manifest


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pdf", required=True)
    ap.add_argument("--metadata", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    try:
        items = recover(Path(args.pdf), Path(args.metadata), Path(args.out))
    except Exception as exc:
        print(f"RESULT: FAIL - {exc}")
        return 1
    print(f"figure assets recovered : {len(items)}")
    print(f"output directory         : {args.out}")
    print("RESULT: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
