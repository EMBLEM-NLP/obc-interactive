"""Shared geometry rules for distinguishing document navigation from figures.

A page with dense dot-leader navigation can contain hundreds of filled vector
rectangles/rules. The generic connected-component detector can otherwise see
those as one large "figure". Keep this decision in a small pure module so it is
falsifiable without the OBC corpus.
"""

from __future__ import annotations

import re

LEADER = re.compile(r"\.{4,}")


def iter_text_lines(page):
    for block in page.get("blocks", []):
        for line in block.get("l", []):
            text = "".join(span.get("t", "") for span in line.get("s", [])).strip()
            if text:
                yield line, text


def navigation_signature(page):
    """Return dot-leader, narrow-font and non-empty text-line counts."""
    leaders = 0
    narrow = 0
    total = 0
    for line, text in iter_text_lines(page):
        total += 1
        if LEADER.search(text):
            leaders += 1
        spans = line.get("s") or []
        if spans:
            first = spans[0]
            font = first.get("f", "")
            size = float(first.get("sz", 0) or 0)
            if font.startswith("ArialNarrow") and size <= 9.5:
                narrow += 1
    return leaders, narrow, total


def contents_like_page(page):
    """Detect ToC/index-style navigation pages without reading section names.

    The strong production signature is the same one Stage 2 uses: at least two
    dot-leader lines plus ten narrow-font lines. The total-line fallback keeps
    synthetic controls and font-substituted renderings testable without tying
    the safety rule to one exact embedded font name.
    """
    leaders, narrow, total = navigation_signature(page)
    return leaders >= 2 and (narrow >= 10 or total >= 15)


def allow_vector_figure_detection(page):
    """Vector figure components are ignored on contents-like navigation pages."""
    return not contents_like_page(page)
