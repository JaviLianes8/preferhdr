"""The strict parser: the grammar a sender must follow, with error positions."""

from __future__ import annotations

import pickle

import pytest

from preferhdr import Preference, PreferError, parse


@pytest.mark.parametrize(
    "value",
    [
        "respond-async",
        "a, b",
        "a ,b\t,  c",
        "  return=minimal  ",
        'foo=""; bar',
        'foo; bar=""',
        "a;",
        "a;;b",
        "a ; b ;c=1",
        'a="x\\"y"; b="caf\xe9"',
        "a=!#$%&'*+-.^_`|~09AZaz",
    ],
)
def test_valid_values_are_accepted(value: str) -> None:
    assert parse(value, strict=True) == parse(value)


@pytest.mark.parametrize(
    ("value", "message", "position"),
    [
        ("", "empty list element", 0),
        (" ", "empty list element", 0),
        (",a", "empty list element", 0),
        ("a,", "empty list element", 2),
        ("a, ,b", "empty list element", 3),
        ("a =1", "whitespace before '='", 1),
        ("a= 1", "whitespace after '='", 2),
        ("a; b =1", "whitespace before '='", 4),
        ("a=", "expected a token or quoted string after '='", 2),
        ("a=@", "expected a token or quoted string after '='", 2),
        ("=a", "expected a token", 0),
        ("a; =b", "expected a token", 3),
        ("a b", "unexpected character", 2),
        ("a=b c", "unexpected character", 4),
        ('a="x"y', "unexpected character", 5),
        ('a="x', "unterminated quoted string", 2),
        ('a="x\\', "unterminated quoted string", 2),
        ('a="\x01"', "invalid character in quoted string", 3),
        ('a="\\\x01"', "invalid character in quoted string", 4),
        ('a="€"', "invalid character in quoted string", 3),
        ("a\r\nb", "unexpected character", 1),
        ("a=1\0", "unexpected character", 3),
        ("a, b, A", "repeated preference 'a'", 6),
    ],
)
def test_violations_raise_with_their_position(value: str, message: str, position: int) -> None:
    with pytest.raises(PreferError) as caught:
        parse(value, strict=True)
    assert (caught.value.message, caught.value.position, caught.value.field) == (
        message,
        position,
        0,
    )


def test_the_error_names_the_field_it_was_found_in() -> None:
    with pytest.raises(PreferError, match=r"at position 2 of field 1$") as caught:
        parse(["a", "b=", "c"], strict=True)
    assert caught.value.field == 1


def test_a_preference_repeated_in_a_later_field_is_rejected() -> None:
    with pytest.raises(PreferError) as caught:
        parse(["wait=1", "x, wait=2"], strict=True)
    assert (caught.value.position, caught.value.field) == (3, 1)


def test_a_repeated_parameter_is_allowed_and_the_first_wins() -> None:
    assert parse("a; x=1; x=2", strict=True) == (Preference("a", None, {"x": "1"}),)


def test_no_field_values_are_valid() -> None:
    assert parse([], strict=True) == ()


def test_the_error_is_a_value_error_and_survives_pickling() -> None:
    with pytest.raises(ValueError) as caught:
        parse("a=", strict=True)
    copy = pickle.loads(pickle.dumps(caught.value))
    assert isinstance(copy, PreferError)
    assert (copy.message, copy.position, copy.field) == (
        "expected a token or quoted string after '='",
        2,
        0,
    )
    assert str(copy) == str(caught.value)


def test_preference_applied_accepts_values_without_parameters() -> None:
    value = "return=representation, respond-async"
    assert parse(value, strict=True, applied=True) == parse(value)


@pytest.mark.parametrize(("value", "position"), [("a; b", 1), ("a=1, b;", 6), ("a ;", 2)])
def test_preference_applied_rejects_parameters(value: str, position: int) -> None:
    with pytest.raises(PreferError, match="takes no parameters") as caught:
        parse(value, strict=True, applied=True)
    assert caught.value.position == position


def test_tolerant_preference_applied_drops_parameters() -> None:
    assert parse("a=1; b=2, c", applied=True) == (Preference("a", "1"), Preference("c"))
