"""Regression tests for the second round of the independent QA lenses."""

from __future__ import annotations

import io
import sys
from collections.abc import ItemsView, Iterator
from typing import Any

import pytest

from preferhdr import Preference, Preferences, PreferError, build
from preferhdr._cli import _from_lines, main
from preferhdr._model import Params

INJECTED = "v\r\nSet-Cookie: x=1"
KELVIN = "\u212a"


class ItemsLie(Params):
    """Parameters whose items() disagree with what was checked."""

    def items(self) -> Any:
        return [("x", INJECTED)]


class SkipsInit(Params):
    """Parameters that fill their storage without any check."""

    def __init__(self) -> None:
        self._items = {"x\r\nSet-Cookie: y": None}


class OwnStr(Preference):
    def __str__(self) -> str:
        return "a\r\nSet-Cookie: z=1"


class SkipsChecks(Preference):
    def __post_init__(self) -> None:
        pass


class LiesAboutAscii(str):
    def isascii(self) -> bool:
        return True


def test_a_params_subclass_that_overrides_items_is_checked() -> None:
    with pytest.raises(PreferError):
        Preference("a", None, ItemsLie())


def test_a_params_subclass_that_skips_its_checks_is_checked() -> None:
    with pytest.raises(PreferError):
        Preference("a", None, SkipsInit())


def test_a_params_subclass_is_stored_as_plain_params() -> None:
    class Plain(Params):
        pass

    pref = Preference("a", None, Plain({"X": "1"}))
    assert type(pref.params) is Params and pref.params == {"x": "1"}
    assert build([pref]) == "a; x=1"


def test_build_writes_a_preference_subclass_by_its_checked_fields() -> None:
    assert build([OwnStr("a", "b", {"p": None})]) == "a=b; p"


@pytest.mark.parametrize(
    ("token", "value", "params"),
    [
        ("a\r\nSet-Cookie: z", None, {}),
        ("a", INJECTED, {}),
        ("a", None, {"x": INJECTED}),
        ("a", None, {"x\r\ny": None}),
    ],
)
def test_build_checks_a_preference_subclass_that_skips_its_checks(
    token: str, value: str | None, params: dict[str, str | None]
) -> None:
    with pytest.raises(PreferError):
        build([SkipsChecks(token, value, params)])


def test_build_applies_its_rules_to_a_preference_subclass() -> None:
    with pytest.raises(PreferError):
        build([SkipsChecks("A"), SkipsChecks("a")])
    with pytest.raises(PreferError):
        build([SkipsChecks("a", None, {"p": None})], applied=True)


def test_a_key_that_is_not_a_str_is_absent_from_the_parameters() -> None:
    params: Any = Preference("a", None, {"k": "1"}).params
    with pytest.raises(KeyError):
        params[5]
    assert params.get(5) is None
    assert 5 not in params
    assert params != {5: "1"}
    assert params != {"k": "1", 5: "1"}


def test_a_lookup_does_not_trust_a_subclass_that_lies_about_isascii() -> None:
    params = Preference("a", None, {"k": "1"}).params
    with pytest.raises(KeyError):
        params[LiesAboutAscii(KELVIN)]
    assert LiesAboutAscii(KELVIN) not in params
    prefs = Preferences([Preference("k")])
    assert prefs.get(LiesAboutAscii(KELVIN)) is None
    assert LiesAboutAscii(KELVIN) not in prefs


def _run(monkeypatch: pytest.MonkeyPatch, data: bytes) -> tuple[int, list[str], str]:
    monkeypatch.setattr(sys, "stdin", io.TextIOWrapper(io.BytesIO(data)))
    out = io.StringIO()
    err = io.StringIO()
    monkeypatch.setattr(sys, "stdout", out)
    monkeypatch.setattr(sys, "stderr", err)
    code = main([])
    return code, out.getvalue().splitlines(), err.getvalue()


def test_a_folded_line_belongs_to_the_field_just_above_it() -> None:
    assert _from_lines("Host: x\nPrefer: a,\n b=1\n\n", False) == ["a, b=1"]
    assert _from_lines("X-Fold: q\n r\nPrefer: a\n", False) == ["a"]
    assert _from_lines("Prefer: a\nX-Fold: q,\n b\n", False) == ["a"]


def test_a_folded_prefer_line_after_another_header_reads_whole(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    assert _run(monkeypatch, b"Host: x\nPrefer: a,\n b=1\n\n") == (0, ["a", "b=1"], "")


def test_a_blank_folded_line_adds_nothing() -> None:
    assert _from_lines("Prefer: a=1;\n \n x=2\n", False) == ["a=1; x=2"]
    assert _from_lines("Prefer: a=1;\n \t \n\tx=2\n", False) == ["a=1; x=2"]


def test_a_blank_folded_line_does_not_move_error_positions(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    code, out, err = _run(monkeypatch, b"Prefer: a,\n \t\n @\n\n")
    assert (code, out) == (1, ["a"])
    assert err == "invalid: expected a token at position 3 of field 0\n"


def test_a_tab_after_the_colon_is_not_part_of_the_value(monkeypatch: pytest.MonkeyPatch) -> None:
    assert _from_lines("Prefer:\ta\n", False) == ["a"]
    assert _from_lines("Prefer:\t \tb=1\t\n", False) == ["b=1"]
    code, out, err = _run(monkeypatch, b"Prefer:\t@\n\n")
    assert (code, out) == (1, [])
    assert err == "invalid: expected a token at position 0 of field 0\n"


def test_params_items_follow_their_lookups() -> None:
    params = Preference("a", None, {"X": "1", "y": None}).params
    view = params.items()
    assert isinstance(view, ItemsView)
    assert ("X", "1") in view and list(view) == [("x", "1"), ("y", None)]
    items: Iterator[str] = iter(params)
    assert list(items) == ["x", "y"]
