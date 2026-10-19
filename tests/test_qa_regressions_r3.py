"""Regression tests for the third round of the independent QA lenses."""

from __future__ import annotations

import time
from collections.abc import Callable, Iterator
from typing import Any

import pytest

from preferhdr import Preference, PreferError, build
from preferhdr._model import Params

INJECTED = "v\r\nSet-Cookie: x=1"
KELVIN = chr(0x212A)


class SkipsChecks(Preference):
    def __post_init__(self) -> None:
        pass


class Raw(Params):
    """Parameters stored as given, without any check."""

    def __init__(self, items: dict[str, str | None]) -> None:
        self._items = items


class ItemsLie(Params):
    def items(self) -> Any:
        return [("x", INJECTED)]


class NoInit(Params):
    """A valid mapping that never fills the inherited storage."""

    def __init__(self) -> None:
        pass

    def __getitem__(self, name: str) -> str | None:
        return {"x": "1"}[name]

    def __iter__(self) -> Iterator[str]:
        return iter(["x"])

    def __len__(self) -> int:
        return 1


class View(Params):
    """A mapping that shows other keys than the storage it inherits."""

    def __init__(self) -> None:
        super().__init__({"safe": "1"})

    def __getitem__(self, name: str) -> str | None:
        return {"other": "2"}[name]

    def __iter__(self) -> Iterator[str]:
        return iter(["other"])


class ListStore(Params):
    def __init__(self) -> None:
        self._items = [("x", "1")]  # type: ignore[assignment]


class NoStore(Params):
    def __init__(self) -> None:
        pass


def test_a_params_subclass_that_never_fills_its_storage_is_read_as_a_mapping() -> None:
    assert build([Preference("a", None, NoInit())]) == "a; x=1"
    assert Preference("a", None, NoInit()).params == {"x": "1"}


def test_a_params_subclass_is_written_from_what_it_shows() -> None:
    assert dict(View()) == {"other": "2"}
    assert str(Preference("a", None, View())) == "a; other=2"


@pytest.mark.parametrize(
    ("params", "error"), [(ListStore, "KeyError"), (NoStore, "AttributeError")]
)
def test_a_params_subclass_that_cannot_be_read_is_a_type_error(
    params: type[Params], error: str
) -> None:
    expected = rf"^params could not be read as a mapping \({error}\)$"
    with pytest.raises(TypeError, match=expected):
        Preference("a", None, params())
    with pytest.raises(TypeError, match=expected):
        build([SkipsChecks("a", None, params())])


def test_values_in_the_raw_storage_of_a_params_subclass_are_checked() -> None:
    with pytest.raises(PreferError, match="value of parameter 'x' holds U\\+000D"):
        Preference("a", None, Raw({"x": INJECTED}))
    with pytest.raises(PreferError, match="value of parameter 'x' holds U\\+000D"):
        build([SkipsChecks("a", None, Raw({"x": INJECTED}))])


def test_repeated_names_in_the_raw_storage_of_a_params_subclass_are_rejected() -> None:
    with pytest.raises(PreferError, match="repeated parameter 'x'"):
        Preference("a", None, Raw({"X": "1", "x": "2"}))


def test_build_rejects_a_repeat_whichever_spelling_comes_first() -> None:
    with pytest.raises(PreferError, match="repeated preference 'a'"):
        build([SkipsChecks("a"), SkipsChecks("A")])
    with pytest.raises(PreferError, match="repeated preference 'a'"):
        build([SkipsChecks("A"), SkipsChecks("a")])


def test_build_checks_a_preference_subclass_before_looking_for_repeats() -> None:
    with pytest.raises(PreferError, match="is not a token"):
        build([SkipsChecks("k"), SkipsChecks(KELVIN)])


def test_build_writes_the_params_subclass_of_a_preference_subclass() -> None:
    assert build([SkipsChecks("a", None, Raw({"X": "1"}))]) == "a; x=1"
    with pytest.raises(PreferError):
        build([SkipsChecks("a", None, ItemsLie())])


def _seconds(work: Callable[[], object]) -> float:
    best = float("inf")
    for _ in range(3):
        start = time.perf_counter()
        work()
        best = min(best, time.perf_counter() - start)
    return best


def test_a_preference_with_many_parameters_is_written_in_linear_time() -> None:
    def pref(n: int) -> Preference:
        return Preference("a", None, {f"k{i}": str(i) for i in range(n)})

    small, large = pref(100_000), pref(400_000)
    assert build([large]) == "a; " + "; ".join(f"k{i}={i}" for i in range(400_000))
    ratio = _seconds(lambda: build([large])) / max(_seconds(lambda: build([small])), 1e-4)
    # Four times the parameters; quadratic writing would take about sixteen times as long.
    assert ratio < 9, ratio
