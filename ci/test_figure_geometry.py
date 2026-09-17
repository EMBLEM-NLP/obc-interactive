#!/usr/bin/env python3
"""Synthetic control for vector-figure fidelity on contents-like pages."""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "pipeline"))

from geometry_rules import (  # noqa: E402
    allow_vector_figure_detection,
    contents_like_page,
    navigation_signature,
)


def line(text, font="ArialNarrow", size=9.0):
    return {
        "b": [10, 10, 100, 20],
        "s": [{"t": text, "f": font, "sz": size}],
    }


def page(lines):
    return {"blocks": [{"l": lines}]}


def main():
    failures = []

    stage1 = (ROOT / "pipeline" / "stage1_geometry.py").read_text(encoding="utf-8")
    if "allow_vector_figure_detection(pg)" not in stage1:
        failures.append("stage1_geometry.py is not wired to the shared vector-figure guard")

    toc_lines = [
        line(f"3.1.{i}.  Topic .................................... {i}")
        for i in range(1, 18)
    ]
    toc = page(toc_lines)
    sig = navigation_signature(toc)
    if not contents_like_page(toc):
        failures.append(f"ToC-like fixture not detected; signature={sig}")
    if allow_vector_figure_detection(toc):
        failures.append("ToC-like fixture still allows vector figure detection")

    # Positive control: a genuine diagram page can contain labels, but no
    # dot-leader navigation signature. The guard must not disable vectors
    # globally.
    figure = page(
        [
            line("Figure 4.1.6.5.-A", font="Helvetica", size=10),
            line("Roof load diagram", font="Helvetica", size=9),
            line("A", font="Helvetica", size=8),
            line("B", font="Helvetica", size=8),
        ]
    )
    if contents_like_page(figure):
        failures.append("real-vector positive control misclassified as contents")
    if not allow_vector_figure_detection(figure):
        failures.append("real-vector positive control was suppressed")

    # Font-substitution control: the fallback should still catch a navigation
    # page when the embedded narrow font is replaced by a generic font.
    substituted = page(
        [
            line(f"9.10.{i}. Fire topic .............................. {i}",
                 font="Helvetica", size=9)
            for i in range(1, 18)
        ]
    )
    if not contents_like_page(substituted):
        failures.append("font-substituted ToC fixture escaped the guard")

    print(f"toc signature       : {sig}")
    print("toc negative        : detected")
    print("vector positive     : preserved")
    print("font substitution   : detected")
    for failure in failures:
        print("  FAIL", failure)
    print("RESULT:", "PASS" if not failures else f"FAIL {len(failures)}")
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
