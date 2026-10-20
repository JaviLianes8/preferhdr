"""Regression tests for the seventh round of the independent QA lenses."""

from __future__ import annotations

from collections.abc import Iterator, Mapping

import pytest

from preferhdr import Preference


class Liar(str):
    """A str subclass whose own case folding lies about its text."""

    def lower(self) -> str:
        return "zzz"

    def __str__(self) -> str:
        return "zzz"


def test_parameters_equal_a_mapping_keyed_by_a_str_subclass_with_the_same_text() -> None:
    params = Preference("a", None, {"x": "1"}).params
    other: dict[str, str] = {Liar("X"): "1"}
    assert (params == other) is True
    assert (params != other) is False
    assert Preference("a", None, other).params == params


class Raising(Mapping[str, str]):
    """A mapping that lists the key ``a`` and whose lookup raises the given error."""

    def __init__(self, error: Exception) -> None:
        self._error = error

    def __iter__(self) -> Iterator[str]:
        return iter(["a"])

    def __len__(self) -> int:
        return 1

    def __getitem__(self, name: str) -> str:
        raise self._error


@pytest.mark.parametrize(
    "error", [IndexError("i"), LookupError("l"), ValueError("v"), RuntimeError("r")]
)
def test_other_errors_from_a_params_mapping_propagate_unchanged(error: Exception) -> None:
    with pytest.raises(type(error)) as caught:
        Preference("x", None, Raising(error))
    assert caught.value is error
    assert caught.type is type(error)
