#!/usr/bin/env python3
"""H6 - property-based tests over the parser and emitter helpers.

Hypothesis generates adversarial inputs (empty strings, surrogates, combining
marks, control characters) and shrinks any failure to a minimal counterexample.
These assert invariants that must hold for ALL inputs, not for the examples I
happened to think of - which is the failure mode behind most of the eleven
check defects.
"""
import sys, os, os, re
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from hypothesis import given, strategies as st, settings, HealthCheck
from lib.canon import text, contains, squash, designator

TEXT = st.text(max_size=200)

@given(TEXT)
def test_canonicalisation_is_idempotent(s):
    once = text(s)
    assert text(once) == once

@given(TEXT)
def test_a_string_contains_itself(s):
    assert contains(s, s)

@given(TEXT, TEXT, TEXT)
def test_contains_is_stable_under_wrapping(a, b, c):
    """A needle must still be found when the haystack is line-wrapped around it -
    the defect that failed the licence-phrase assertion."""
    needle = text(b)
    if not needle:
        return
    hay = f"{a}\n{b.replace(' ', chr(10))}\n{c}"
    assert contains(hay, needle) or " " not in needle

@given(TEXT)
def test_escaping_round_trips(s):
    """HTML-escaping then canonicalising must equal canonicalising - the defect
    that failed on King&#x27;s."""
    import html
    assert text(html.escape(s)) == text(s)

@given(st.integers(min_value=1, max_value=99), st.integers(min_value=1, max_value=99),
       st.integers(min_value=1, max_value=99))
def test_designator_ignores_punctuation(a, b, c):
    assert designator(f"{a}.{b}.{c}.") == designator(f"{a}.{b}.{c}") \
        == designator(f"{a}-{b}-{c}")

@given(TEXT)
def test_squash_removes_all_whitespace(s):
    assert not re.search(r"\s", squash(s))

@settings(suppress_health_check=[HealthCheck.too_slow], max_examples=50)
@given(st.lists(st.integers(min_value=1, max_value=20), min_size=1, max_size=6))
def test_permalink_is_injective_on_designators(parts):
    """Distinct clause paths must produce distinct permalinks - the property that
    keeps an inserted 9.10.16.1A from colliding with its siblings."""
    sys.path.insert(0, os.environ.get("OBC_EMIT", os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "pipeline", "emitters"))))
    from emit_common import permalink
    a = "B/9/" + ".".join(str(p) for p in parts)
    b = a + "A"
    assert permalink(a) != permalink(b)
