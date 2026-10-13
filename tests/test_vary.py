"""vary() lists Prefer once in a Vary value and never writes an unsafe one."""

from __future__ import annotations

import pytest

from preferhdr import PreferError, vary


def test_no_current_value_gives_prefer() -> None:
    assert vary() == "Prefer"
    assert vary("") == "Prefer"
    assert vary([]) == "Prefer"


def test_prefer_is_appended_to_the_existing_list() -> None:
    assert vary("Accept-Encoding,  accept-language") == "Accept-Encoding, accept-language, Prefer"


def test_prefer_already_listed_is_not_repeated() -> None:
    assert vary("accept, PREFER") == "accept, PREFER"


def test_several_field_lines_are_one_list() -> None:
    assert vary(["Accept", "Origin"]) == "Accept, Origin, Prefer"


def test_empty_members_are_dropped() -> None:
    assert vary(" , Accept,,\t") == "Accept, Prefer"


def test_a_wildcard_already_covers_prefer() -> None:
    assert vary("Accept, *") == "*"


@pytest.mark.parametrize("value", ["Accept\r\nSet-Cookie: a=1", "a b", "x;y", '"a"', "€"])
def test_a_member_that_is_not_a_field_name_is_rejected(value: str) -> None:
    with pytest.raises(PreferError, match="is not a field name"):
        vary(value)


def test_a_value_that_is_not_a_string_is_a_type_error() -> None:
    with pytest.raises(TypeError):
        vary([1])  # type: ignore[list-item]
