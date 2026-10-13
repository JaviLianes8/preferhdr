"""The builder writes only what a header field can carry and the parser reads back."""

from __future__ import annotations

import pytest

from preferhdr import Preference, PreferError, build, parse


def test_build_a_bare_token() -> None:
    assert build([Preference("respond-async")]) == "respond-async"


def test_build_a_valued_preference() -> None:
    assert build([Preference("return", "minimal")]) == "return=minimal"


def test_build_quotes_a_value_that_is_not_a_token() -> None:
    assert build([Preference("foo", "bar baz")]) == 'foo="bar baz"'


def test_build_escapes_quotes_and_backslashes() -> None:
    assert build([Preference("foo", 'a"b\\c')]) == r'foo="a\"b\\c"'


def test_build_emits_parameters() -> None:
    pref = Preference("foo", "bar", {"baz": "qux", "lenient": None, "note": "a, b"})
    assert build([pref]) == 'foo=bar; baz=qux; lenient; note="a, b"'


def test_build_joins_preferences_with_comma_space() -> None:
    prefs = [Preference("respond-async"), Preference("wait", "10")]
    assert build(prefs) == "respond-async, wait=10"


def test_build_writes_an_empty_value_as_a_bare_name() -> None:
    assert build([Preference("foo", "", {"bar": ""})]) == "foo; bar"


def test_build_of_nothing_is_empty() -> None:
    assert build([]) == ""


def test_build_accepts_the_result_of_parse() -> None:
    header = 'respond-async, wait=10, return=minimal; note="a, b"'
    assert build(parse(header)) == header


def test_build_output_is_strictly_valid() -> None:
    prefs = [Preference("a", 'x "y" \\ z\t\xe9'), Preference("b", "", {"c": "d e"})]
    assert parse(build(prefs), strict=True) == tuple(prefs)


def test_a_repeated_preference_is_rejected() -> None:
    with pytest.raises(PreferError, match="repeated preference 'wait'"):
        build([Preference("wait", "1"), Preference("WAIT", "2")])


def test_preference_applied_takes_values() -> None:
    prefs = [Preference("return", "representation"), Preference("respond-async")]
    assert build(prefs, applied=True) == "return=representation, respond-async"


def test_preference_applied_rejects_parameters() -> None:
    with pytest.raises(PreferError, match="takes no parameters"):
        build([Preference("return", "minimal", {"foo": "x"})], applied=True)


def test_build_rejects_what_is_not_a_preference() -> None:
    with pytest.raises(TypeError):
        build(["return=minimal"])  # type: ignore[list-item]


@pytest.mark.parametrize(
    "attempt",
    [
        lambda: Preference("return\r\nSet-Cookie", "x"),
        lambda: Preference("return", "minimal\r\nSet-Cookie: a=1"),
        lambda: Preference("return", "minimal", {"x": "1\nX-Evil: 1"}),
        lambda: Preference("return", "minimal", {"x\r\nX-Evil": "1"}),
    ],
)
def test_no_input_can_split_the_header(attempt: object) -> None:
    with pytest.raises(PreferError):
        build([attempt()])  # type: ignore[operator]
