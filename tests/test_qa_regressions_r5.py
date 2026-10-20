"""Regression tests for the fifth round of the independent QA lenses."""

from __future__ import annotations

from typing import Any
from unittest import mock

import pytest

from preferhdr import Preference
from preferhdr._model import Params


class AlwaysEqual:
    def __eq__(self, other: object) -> bool:
        return True

    def __ne__(self, other: object) -> bool:
        return False

    __hash__ = object.__hash__


@pytest.mark.parametrize("other", [mock.ANY, AlwaysEqual()])
def test_parameters_leave_a_non_mapping_comparison_to_the_other_side(other: object) -> None:
    params = Preference("a", None, {"x": "1"}).params
    assert (params == other) is True
    assert (params != other) is False


def message_for(value: Any) -> str:
    with pytest.raises(TypeError) as caught:
        Preference(value)
    return str(caught.value)


def test_a_type_name_of_forty_one_characters_is_cut() -> None:
    expected = f"preference name must be a str, not {'Z' * 40}... (41 characters)"
    assert message_for(type("Z" * 41, (object,), {})()) == expected


def test_a_long_type_name_keeps_its_head() -> None:
    expected = f"preference name must be a str, not {'H' * 40}... (100 characters)"
    assert message_for(type("H" * 40 + "T" * 60, (object,), {})()) == expected


class Outer:
    class Inner:
        pass


def test_a_nested_type_is_named_without_its_enclosing_class() -> None:
    assert message_for(Outer.Inner()) == "preference name must be a str, not Inner"


def test_a_type_is_named_by_its_real_class_not_the_one_it_claims() -> None:
    liar = type("Liar", (object,), {"__class__": property(lambda self: int)})
    assert message_for(liar()) == "preference name must be a str, not Liar"


class ShowsOther(dict[str, Any]):
    def __getitem__(self, name: str) -> Any:
        return "shown"


class StoresSubclass(Params):
    def __init__(self) -> None:
        self._items = ShowsOther(a="stored")


def test_a_params_subclass_storing_a_dict_subclass_is_read_through_its_lookups() -> None:
    assert dict(Preference("x", None, StoresSubclass()).params) == {"a": "shown"}
