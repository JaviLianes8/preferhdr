"""Regression tests for the findings of the independent QA lenses."""

from __future__ import annotations

import enum
import time
from collections.abc import Callable
from typing import Any

import pytest

from preferhdr import Preference, Preferences, PreferError, build, parse, vary
from preferhdr._cli import _from_lines


class Hostile(str):
    """A str whose methods lie about its characters."""

    def __iter__(self) -> Any:
        return iter("ok")

    def __getitem__(self, index: Any) -> Any:
        return "o"

    def __len__(self) -> int:
        return 2

    def __str__(self) -> str:
        return "ok"

    def __format__(self, spec: str) -> str:
        return "ok"

    def lower(self) -> Any:
        return "ok"

    def isascii(self) -> bool:
        return True

    def split(self, *args: Any, **kwargs: Any) -> Any:
        return ["ok"]

    def strip(self, *args: Any) -> Any:
        return "ok"

    def replace(self, *args: Any) -> Any:
        return "ok"


class Ret(str, enum.Enum):
    MINIMAL = "minimal"
    REPRESENTATION = "a b"


INJECTED = "a\r\nSet-Cookie: x=1"


@pytest.mark.parametrize(
    "make",
    [
        lambda: Preference(Hostile(INJECTED)),
        lambda: Preference("return", Hostile(INJECTED)),
        lambda: Preference("a", None, {Hostile(INJECTED): None}),
        lambda: Preference("a", None, {"p": Hostile(INJECTED)}),
        lambda: vary(Hostile(INJECTED)),
        lambda: vary([Hostile(INJECTED)]),
    ],
    ids=["name", "value", "parameter name", "parameter value", "vary", "vary list"],
)
def test_a_str_subclass_is_checked_by_its_real_characters(make: Callable[[], object]) -> None:
    with pytest.raises(PreferError):
        make()


def test_a_str_subclass_is_stored_and_written_as_a_plain_str() -> None:
    pref = Preference(Hostile("Return"), Hostile("a b"), {Hostile("P"): Hostile("q")})
    assert (pref.token, pref.value, dict(pref.params)) == ("return", "a b", {"p": "q"})
    assert {type(pref.token), type(pref.value), *map(type, pref.params)} == {str}
    assert type(pref.params["p"]) is str
    assert build([pref]) == 'return="a b"; p=q'
    assert vary(Hostile("Accept")) == "Accept, Prefer"


def test_a_str_subclass_field_parses_as_its_characters() -> None:
    for strict in (False, True):
        prefs = parse(Hostile("wait=10, return=minimal"), strict=strict)
        assert [str(pref) for pref in prefs] == ["wait=10", "return=minimal"]
    assert parse([Hostile(INJECTED)]) == parse(INJECTED)
    assert "\r" not in build(parse(Hostile(INJECTED)))


def test_names_given_as_str_subclasses_are_looked_up_by_their_characters() -> None:
    prefs = Preferences([Preference("return", "minimal", {"p": "1"})])
    assert prefs.get(Hostile("RETURN")) == prefs[0]
    assert Hostile("Return") in prefs
    assert prefs[0].params[Hostile("P")] == "1"
    assert prefs.applied(Hostile("return")) == (Preference("return", "minimal"),)


def test_str_enums_are_written_as_their_values() -> None:
    pref = Preference("return", Ret.MINIMAL, {"x": Ret.REPRESENTATION})
    assert type(pref.value) is str and type(pref.params["x"]) is str
    assert build([pref]) == 'return=minimal; x="a b"'
    str_enum: Any = getattr(enum, "StrEnum", None)
    if str_enum is None:
        pytest.skip("enum.StrEnum needs Python 3.11")
    name = str_enum("Name", {"RETURN": "Return", "NOTE": "a b"})
    pref = Preference(name.RETURN, name.NOTE, {name.RETURN: name.NOTE})
    assert build([pref]) == 'return="a b"; return="a b"'
    assert type(pref.token) is str and type(pref.value) is str


def test_preferences_differing_only_in_parameters_are_unequal() -> None:
    base = Preference("a", "1", {"x": "1"})
    for other in ({}, {"x": None}, {"x": "2"}, {"x": "1", "y": "1"}, {"y": "1"}):
        assert base != Preference("a", "1", other)
    assert parse("a; x=1") != parse("a")
    assert len({base, Preference("a", "1")}) == 2


def test_parameter_order_changes_neither_equality_nor_hash() -> None:
    first = Preference("a", None, {"x": "1", "y": "2", "z": None})
    second = Preference("a", None, {"z": None, "y": "2", "x": "1"})
    assert first == second and hash(first) == hash(second)
    assert len({first, second}) == 1
    assert {first: 1}[second] == 1
    assert hash(parse("a; x=1; y=2")[0]) == hash(parse("a; y=2; x=1")[0])


def test_messages_cut_exactly_after_forty_characters() -> None:
    with pytest.raises(PreferError) as caught:
        Preference("b" * 40 + "@")
    assert str(caught.value) == f"preference name {'b' * 40!r}... (41 characters) is not a token"
    with pytest.raises(PreferError) as caught:
        Preference("b" * 39 + "@")
    assert str(caught.value) == f"preference name {'b' * 39 + '@'!r} is not a token"


@pytest.mark.parametrize(
    ("text", "kept"),
    [
        ('a="x""y, b=1', ["b=1"]),
        ('a="x" "y, b=1', ["b=1"]),
        ('a="x"y"z, b=1, c', ["b=1", "c"]),
        ('a; p="x""y, b', ["a", "b"]),
    ],
)
def test_a_quote_after_a_closed_string_does_not_open_another(text: str, kept: list[str]) -> None:
    assert [str(pref) for pref in parse(text)] == kept


@pytest.mark.parametrize(
    ("text", "kept"),
    [
        ('a, b; p="q, c', ["a", "b"]),
        ('a=1; y=2; x="open; z=3, b', ["a=1; y=2"]),
        ('a, b="x, c', ["a"]),
    ],
)
def test_an_unterminated_quote_drops_what_it_belongs_to_and_the_rest(
    text: str, kept: list[str]
) -> None:
    assert [str(pref) for pref in parse(text)] == kept


def _seconds(work: Callable[[], object]) -> float:
    best = float("inf")
    for _ in range(3):
        start = time.perf_counter()
        work()
        best = min(best, time.perf_counter() - start)
    return best


def test_folded_header_lines_are_joined_in_linear_time() -> None:
    def folded(n: int) -> str:
        return "Prefer: a=1\n" + " b\n" * n

    assert _from_lines("Prefer: a=1\n b\n\tc \nWait: 1\n", applied=False) == ["a=1 b c"]
    small, large = folded(50_000), folded(200_000)
    assert _from_lines(large, applied=False) == ["a=1" + " b" * 200_000]
    ratio = _seconds(lambda: _from_lines(large, False)) / max(
        _seconds(lambda: _from_lines(small, False)), 1e-4
    )
    # Four times the input; quadratic joining would take about sixteen times as long.
    assert ratio < 9, ratio
