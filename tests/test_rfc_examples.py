"""The examples of RFC 7240 and its errata read as the RFC says they do.

Vectors are cited from https://www.rfc-editor.org/rfc/rfc7240.txt (section given in each
test) and https://www.rfc-editor.org/errata/rfc7240, fetched 2026-10-13. The last test
reads every example header from a local copy of the RFC text, fetched and checked by
``python scripts/fetch_upstream.py``; it skips while that copy is absent.
"""

from __future__ import annotations

import re

from conftest import read_upstream

from preferhdr import Preference, build, parse

EXAMPLE = re.compile(r"^ +(Prefer|Preference-Applied): (.*)$", flags=re.MULTILINE)


def test_section_2_empty_values_are_equivalent() -> None:
    expected = (Preference("foo", None, {"bar": None}),)
    for value in ("foo; bar", 'foo; bar=""', 'foo=""; bar'):
        assert parse(value, strict=True) == expected


def test_section_2_several_fields_equal_one_list() -> None:
    split = parse(["respond-async, wait=100", "handling=lenient"], strict=True)
    joined = parse("handling=lenient, wait=100, respond-async", strict=True)
    assert set(split) == set(joined)
    assert (split.respond_async, split.wait, split.handling) == (True, 100, "lenient")


def test_section_2_1_example_1_async_with_an_unregistered_preference() -> None:
    prefs = parse(["respond-async, wait=10", "priority=5"], strict=True)
    assert (prefs.respond_async, prefs.wait) == (True, 10)
    assert prefs.get("priority") == Preference("priority", "5")


def test_section_2_1_example_2_names_a_preference_lenient() -> None:
    # Erratum 4955: this is a preference called "lenient", not handling=lenient.
    prefs = parse("Lenient", strict=True)
    assert prefs == (Preference("lenient"),)
    assert prefs.handling is None


def test_section_2_1_example_3_an_undefined_parameter() -> None:
    (pref,) = parse('return=minimal; foo="some parameter"', strict=True)
    assert pref == Preference("return", "minimal", {"foo": "some parameter"})


def test_section_3_preference_applied_echoes_the_honoured_value() -> None:
    request = parse("return=representation", strict=True)
    applied = build(request.applied("return"), applied=True)
    assert applied == "return=representation"
    assert parse(applied, strict=True, applied=True).return_ == "representation"


def test_section_4_registered_preferences() -> None:
    assert parse("respond-async", strict=True).respond_async is True
    assert parse("return=representation", strict=True).return_ == "representation"
    assert parse("return=minimal", strict=True).return_ == "minimal"
    assert parse("respond-async, wait=10", strict=True).wait == 10
    assert parse("handling=strict", strict=True).handling == "strict"


def test_erratum_4317_commas_separate_preferences_and_semicolons_parameters() -> None:
    assert len(parse("respond-async, wait=100", strict=True)) == 2
    assert parse("respond-async; wait=100", strict=True) == (
        Preference("respond-async", None, {"wait": "100"}),
    )


def test_every_example_header_in_the_rfc_text_is_valid() -> None:
    text = read_upstream("rfc7240.txt")
    examples = EXAMPLE.findall(text)
    assert len(examples) == 17
    for name, value in examples:
        applied = name == "Preference-Applied"
        prefs = parse(value, strict=True, applied=applied)
        assert prefs, value
        assert parse(build(prefs, applied=applied), strict=True) == prefs
