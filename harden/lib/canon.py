#!/usr/bin/env python3
"""Normalisation before assertion.

Four of the eleven check defects in this project were the same class: comparing
against a representation a downstream writer had legitimately transformed —
"King's" vs "King&#x27;s", a licence sentence wrapped across a line, a manifest
column header, an escaped apostrophe. The recognised discipline is to reduce
both sides to a canonical form and compare meaning, not bytes.
"""
import html as _html
import re
import unicodedata

def text(s, *, unescape=True, fold_ws=True, nfc=True, casefold=False):
    """Canonical text for comparison. Order matters: unescape before
    normalising, normalise before folding whitespace."""
    if s is None:
        return ""
    if unescape:
        s = _html.unescape(s)
    if nfc:
        s = unicodedata.normalize("NFC", s)
    s = (s.replace("\u00a0", " ").replace("\u2019", "'").replace("\u2018", "'")
          .replace("\u201c", '"').replace("\u201d", '"')
          .replace("\u2013", "-").replace("\u2014", "-")
          .replace("\ufb01", "fi").replace("\ufb02", "fl"))
    if fold_ws:
        s = re.sub(r"\s+", " ", s).strip()
    return s.casefold() if casefold else s

def contains(haystack, needle, **kw):
    """Substring test that cannot fail on escaping, line wrapping, smart quotes
    or Unicode form. This is the function that replaces every raw `in` test."""
    return text(needle, **kw) in text(haystack, **kw)

def squash(s):
    """All whitespace removed - for character-conservation comparisons."""
    return re.sub(r"\s+", "", text(s, fold_ws=False))

def designator(s):
    """Canonical clause/table designator: 9.10.16.1. == 9.10.16.1 == 9-10-16-1"""
    return re.sub(r"[.\-\s]", "", text(s)).upper()
