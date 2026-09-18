"""Shared raster-image role, naming, and rendering rules for Stage 6.

The PDF contains several kinds of raster objects. Only captioned Code figures
belong in the browseable figure set. Table-cell diagrams, front-matter art,
inline equations, and tiny rasterization artifacts need different treatment.

Keep these rules in one pure-ish module so Stage 6, recovery tooling, and
no-data CI controls agree on classification and rendering.
"""

from __future__ import annotations

from pathlib import Path
import re

import pymupdf


ROLE_DIR = {
    "formal_figure": "figures-v1",
    "front_matter": "front-matter-v1",
    "inline_equation": "inline-raster-v1",
    "table_cell_graphic": "table-raster-v1",
}
BROWSEABLE_ROLES = set(ROLE_DIR)
MICRO_ROLE = "micro_nonfigure"

# Current Volume 1 front matter ends at page 20. Tiny artifacts are rejected
# before this boundary is consulted, so page-24/27 glyph fragments do not get
# promoted to front-matter assets.
FRONT_MATTER_MAX_PAGE = 20


def normalize_designator(value: str | None) -> str | None:
    """Normalize known figure-caption punctuation variants.

    The source uses both 4.1.7.6.-G and the malformed 4.1.7.6-.G.
    The canonical identifier is the former.
    """
    if not value:
        return None
    value = value.strip().rstrip(".")
    value = re.sub(r"(?<=\d)-\.([A-Z0-9/]+)$", r".-\1", value, flags=re.I)
    value = re.sub(r"(?<=\d)\.\.-([A-Z0-9/]+)$", r".-\1", value, flags=re.I)
    return value


def overlap_fraction(inner, outer) -> float:
    ix0, iy0 = max(inner[0], outer[0]), max(inner[1], outer[1])
    ix1, iy1 = min(inner[2], outer[2]), min(inner[3], outer[3])
    if ix1 <= ix0 or iy1 <= iy0:
        return 0.0
    area = max((inner[2] - inner[0]) * (inner[3] - inner[1]), 1e-9)
    return ((ix1 - ix0) * (iy1 - iy0)) / area


def is_micro_raster(width: int, height: int) -> bool:
    """Reject rasterized glyph/rule fragments rather than surface them as figures."""
    width, height = int(width), int(height)
    return (width <= 16 and height <= 16) or width <= 2 or height <= 2


def classify_raster(*, page: int, width: int, height: int, box,
                    designator: str | None, table_boxes=()) -> str:
    """Return the semantic role for one raster candidate."""
    if is_micro_raster(width, height):
        return MICRO_ROLE
    if any(overlap_fraction(box, table) >= 0.55 for table in table_boxes):
        return "table_cell_graphic"
    if normalize_designator(designator):
        return "formal_figure"
    if int(page) <= FRONT_MATTER_MAX_PAGE:
        return "front_matter"
    return "inline_equation"


def role_directory(role: str) -> str | None:
    return ROLE_DIR.get(role)


def package_ref(role: str, filename: str) -> str | None:
    directory = role_directory(role)
    if not directory:
        return None
    return f"assets/{directory}/{Path(filename).name}"


def bbox_distance(a, b) -> float:
    return max(abs(float(a[i]) - float(b[i])) for i in range(4))


def image_tuple_for_box(page, box, tolerance: float = 0.35):
    """Find the embedded image tuple whose placement matches a geometry box."""
    best = None
    best_distance = float("inf")
    for image in page.get_images(full=True):
        try:
            rect = page.get_image_bbox(image)
        except Exception:
            continue
        candidate = [rect.x0, rect.y0, rect.x1, rect.y1]
        distance = bbox_distance(candidate, box)
        if distance < best_distance:
            best, best_distance = image, distance
    if best is None or best_distance > tolerance:
        return None
    return best


def flatten_rgb_with_mask(rgb: bytes, mask: bytes, channels: int) -> bytes:
    """Composite source samples through an 8-bit soft mask onto white."""
    if channels < 3:
        raise ValueError("source raster must have at least 3 color channels")
    if len(rgb) < len(mask) * channels:
        raise ValueError("color sample buffer is smaller than mask geometry")
    out = bytearray(len(mask) * 3)
    for i, alpha in enumerate(mask):
        inv = 255 - alpha
        src = i * channels
        dst = i * 3
        out[dst] = (rgb[src] * alpha + 255 * inv + 127) // 255
        out[dst + 1] = (rgb[src + 1] * alpha + 255 * inv + 127) // 255
        out[dst + 2] = (rgb[src + 2] * alpha + 255 * inv + 127) // 255
    return bytes(out)


def save_raster_portable(doc, page, image_tuple, target) -> dict:
    """Write an RGB PNG, flattening any PDF soft mask onto white."""
    xref = int(image_tuple[0])
    smask = int(image_tuple[1] or 0)
    base = pymupdf.Pixmap(doc, xref)
    if base.alpha:
        base = pymupdf.Pixmap(base, 0)
    if base.n - base.alpha < 3:
        base = pymupdf.Pixmap(pymupdf.csRGB, base)

    target = str(target)
    if smask:
        mask = pymupdf.Pixmap(doc, smask)
        if base.width != mask.width or base.height != mask.height:
            raise RuntimeError(
                f"soft-mask geometry mismatch for xref {xref}: "
                f"{base.width}x{base.height} vs {mask.width}x{mask.height}"
            )
        samples = flatten_rgb_with_mask(base.samples, mask.samples, base.n)
        flattened = pymupdf.Pixmap(
            pymupdf.csRGB, base.width, base.height, samples, False
        )
        flattened.save(target)
        return {"xref": xref, "smask": smask, "soft_mask_flattened": True}

    base.save(target)
    return {"xref": xref, "smask": 0, "soft_mask_flattened": False}
