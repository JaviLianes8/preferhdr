"""Preference checks its input where it is made and stays immutable."""

from __future__ import annotations

import pickle
from typing import Any

import pytest

from preferhdr import Preference, PreferError


def test_names_are_lower_cased() -> None:
    pref = Preference("Return", "minimal", {"Foo": "x"})
    assert (pref.token, dict(pref.params)) == ("return", {"foo": "x"})


def test_an_empty_value_becomes_none() -> None:
    assert Preference("a", "", {"b": ""}) == Preference("a", None, {"b": None})


def test_equality_ignores_parameter_order_and_name_case() -> None:
    assert Preference("a", None, {"x": "1", "y": "2"}) == Preference(
        "A", None, {"Y": "2", "X": "1"}
    )


def test_parameters_are_looked_up_case_insensitively() -> None:
    params = Preference("a", None, {"x": "1"}).params
    assert params["X"] == "1"
    assert "X" in params
    assert params.get("y") is None


def test_preferences_are_hashable() -> None:
    first = Preference("a", "1", {"x": "y"})
    assert len({first, Preference("A", "1", {"X": "y"})}) == 1


def test_parameters_cannot_be_changed() -> None:
    source = {"x": "1"}
    pref = Preference("a", None, source)
    source["x"] = "2"
    assert pref.params["x"] == "1"
    with pytest.raises(TypeError):
        pref.params["x"] = "3"  # type: ignore[index]


def test_fields_cannot_be_reassigned() -> None:
    pref = Preference("a")
    with pytest.raises(AttributeError):
        pref.token = "b"  # type: ignore[misc]


def test_a_preference_survives_pickling() -> None:
    pref = Preference("a", "x y", {"b": None})
    assert pickle.loads(pickle.dumps(pref)) == pref


@pytest.mark.parametrize("name", ["", "a b", "a\r\nb", "a=b", "a;b", '"a"', "caf\xe9", "a,b"])
def test_a_name_that_is_not_a_token_is_rejected(name: str) -> None:
    with pytest.raises(PreferError, match="is not a token"):
        Preference(name)
    with pytest.raises(PreferError, match="is not a token"):
        Preference("a", None, {name: "1"})


@pytest.mark.parametrize("value", ["a\rb", "a\nb", "\0", "\x01", "\x7f", "€", "\ud800"])
def test_a_value_no_field_can_carry_is_rejected(value: str) -> None:
    with pytest.raises(PreferError, match="which a header field cannot carry"):
        Preference("a", value)
    with pytest.raises(PreferError, match="which a header field cannot carry"):
        Preference("a", None, {"b": value})


def test_tab_space_and_obs_text_values_are_allowed() -> None:
    assert Preference("a", "\t x \xff").value == "\t x \xff"


def test_a_parameter_named_twice_is_rejected() -> None:
    with pytest.raises(PreferError, match="repeated parameter 'x'"):
        Preference("a", None, {"x": "1", "X": "2"})


@pytest.mark.parametrize(
    "kwargs",
    [{"token": 1}, {"token": "a", "value": 5}, {"token": "a", "params": [("x", "1")]}],
)
def test_wrong_types_are_type_errors(kwargs: dict[str, Any]) -> None:
    with pytest.raises(TypeError):
        Preference(**kwargs)


def test_a_parameter_value_of_the_wrong_type_is_a_type_error() -> None:
    with pytest.raises(TypeError):
        Preference("a", None, {"x": 1})  # type: ignore[dict-item]


def test_str_writes_the_preference_as_sent() -> None:
    pref = Preference("return", "minimal", {"foo": "some parameter", "bar": None})
    assert str(pref) == 'return=minimal; foo="some parameter"; bar'


def test_params_repr_reads_like_a_dict() -> None:
    assert repr(Preference("a", None, {"b": "1"})) == (
        "Preference(token='a', value=None, params={'b': '1'})"
    )
