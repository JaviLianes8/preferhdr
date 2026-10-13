"""Preferences answers the questions a server asks about the registered preferences."""

from __future__ import annotations

import pytest

from preferhdr import Preference, Preferences, parse


def test_lookup_is_case_insensitive_and_returns_the_first() -> None:
    prefs = Preferences([Preference("wait", "1"), Preference("wait", "2")])
    assert prefs.get("WAIT") == Preference("wait", "1")
    assert "Wait" in prefs
    assert prefs.get("missing") is None
    assert "missing" not in prefs


def test_membership_still_works_for_preferences() -> None:
    prefs = parse("a=1")
    assert Preference("a", "1") in prefs
    assert Preference("a", "2") not in prefs


def test_preferences_is_an_immutable_hashable_tuple() -> None:
    prefs = parse("a, b")
    assert isinstance(prefs, tuple)
    assert hash(prefs) == hash(parse("a, b"))
    with pytest.raises(AttributeError):
        prefs.extra = 1  # type: ignore[attr-defined]


def test_only_preferences_can_be_held() -> None:
    with pytest.raises(TypeError):
        Preferences(["a"])  # type: ignore[list-item]


def test_empty_preferences_answer_nothing() -> None:
    prefs = Preferences()
    assert (prefs.respond_async, prefs.return_, prefs.wait, prefs.handling) == (
        False,
        None,
        None,
        None,
    )


def test_respond_async_needs_the_bare_preference() -> None:
    assert parse("Respond-Async").respond_async is True
    assert parse('respond-async=""').respond_async is True
    assert parse("respond-async=yes").respond_async is False


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("return=minimal", "minimal"),
        ('return="representation"', "representation"),
        ("RETURN=minimal", "minimal"),
        ("return=Minimal", None),
        ("return", None),
        ("return=full", None),
        ("return=minimal, return=representation", "minimal"),
    ],
)
def test_return_reads_the_two_defined_values(value: str, expected: str | None) -> None:
    assert parse(value).return_ == expected


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("handling=strict", "strict"),
        ("handling=lenient", "lenient"),
        ("handling=Strict", None),
        ("lenient", None),
        ("handling=lenient, handling=strict", "lenient"),
    ],
)
def test_handling_reads_the_two_defined_values(value: str, expected: str | None) -> None:
    assert parse(value).handling == expected


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("wait=10", 10),
        ("wait=0", 0),
        ('wait="100"', 100),
        ("wait=007", 7),
        ("wait=" + "0" * 500 + "5", 5),
        ("wait=" + "9" * 100, int("9" * 100)),
        ("wait=" + "9" * 101, None),
        ("wait=-1", None),
        ("wait=+1", None),
        ("wait=1.5", None),
        ('wait="1 "', None),
        ('wait="\xb2"', None),
        ("wait", None),
    ],
)
def test_wait_reads_delay_seconds(value: str, expected: int | None) -> None:
    assert parse(value).wait == expected


def test_unicode_digits_are_not_delay_seconds() -> None:
    assert Preferences([Preference("wait", "\xb9")]).wait is None


def test_applied_keeps_the_honoured_preferences_without_parameters() -> None:
    prefs = parse("respond-async, return=minimal; foo=1, wait=10")
    assert prefs.applied("Return", "respond-async", "handling") == (
        Preference("respond-async"),
        Preference("return", "minimal"),
    )


def test_applied_with_no_names_is_empty() -> None:
    assert parse("a").applied() == ()


def test_repr_names_the_type() -> None:
    assert repr(parse("a")) == "Preferences([Preference(token='a', value=None, params={})])"
