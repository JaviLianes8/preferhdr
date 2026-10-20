"""Regression tests for the fourth round of the independent QA lenses."""

from __future__ import annotations

from collections import OrderedDict
from collections.abc import Iterator
from typing import Any

import pytest

from preferhdr import Preference, build


def test_a_long_type_name_is_cut_with_its_length() -> None:
    long_type = type("X" * 500, (object,), {})
    with pytest.raises(TypeError) as caught:
        Preference(long_type())
    shown = "X" * 40
    assert str(caught.value) == f"preference name must be a str, not {shown}... (500 characters)"


def test_a_type_name_of_forty_characters_is_shown_whole() -> None:
    with pytest.raises(TypeError) as caught:
        Preference(type("Y" * 40, (object,), {})())
    assert str(caught.value) == f"preference name must be a str, not {'Y' * 40}"


class RejectsLookups(dict[str, Any]):
    def __getitem__(self, name: str) -> Any:
        raise KeyError(name)


class ShowsOther(dict[str, Any]):
    def __getitem__(self, name: str) -> Any:
        return "shown"


class IteratesOther(dict[str, Any]):
    def __iter__(self) -> Iterator[str]:
        return iter(["other"])

    def __getitem__(self, name: str) -> Any:
        return {"other": "2"}[name]


class OrderedShowsOther(OrderedDict[str, Any]):
    def __getitem__(self, name: str) -> Any:
        return "shown"


def test_a_dict_subclass_whose_lookup_rejects_its_keys_is_a_type_error() -> None:
    with pytest.raises(TypeError, match=r"^params could not be read as a mapping \(KeyError\)$"):
        Preference("x", None, RejectsLookups(a="1"))


@pytest.mark.parametrize("params", [ShowsOther(a="stored"), OrderedShowsOther(a="stored")])
def test_a_dict_subclass_is_read_through_its_lookups(params: dict[str, Any]) -> None:
    assert dict(Preference("x", None, params).params) == {"a": "shown"}
    assert build([Preference("x", None, params)]) == "x; a=shown"


def test_a_dict_subclass_is_read_through_its_iteration() -> None:
    assert dict(Preference("x", None, IteratesOther(safe="1")).params) == {"other": "2"}


def test_a_dict_subclass_that_overrides_items_is_read_through_items() -> None:
    class OwnItems(dict[str, Any]):
        def items(self) -> Any:
            return [("b", "2")]

    assert dict(Preference("x", None, OwnItems(a="1")).params) == {"b": "2"}


def test_a_plain_dict_is_read_as_it_is() -> None:
    assert dict(Preference("x", None, {"A": "1", "b": None}).params) == {"a": "1", "b": None}


@pytest.mark.parametrize("other", [None, 5, "x", ["x"], [("x", "1")], b"x", object()])
def test_parameters_never_equal_a_non_mapping(other: object) -> None:
    params = Preference("a", None, {"x": "1"}).params
    assert (params == other) is False
    assert (params != other) is True
    assert (other == params) is False
    assert (other != params) is True
