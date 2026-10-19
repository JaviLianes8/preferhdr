"""Regression tests for the sixth round of the independent QA lenses."""

from __future__ import annotations

from collections.abc import Iterator, Mapping
from typing import Any

import pytest

from preferhdr import Preference


class Unreadable(Mapping[Any, str]):
    """A mapping whose keys can be listed but whose values must never be read."""

    def __init__(self, keys: list[Any]) -> None:
        self._keys = keys

    def __iter__(self) -> Iterator[Any]:
        return iter(self._keys)

    def __len__(self) -> int:
        return len(self._keys)

    def __getitem__(self, key: Any) -> str:
        raise LookupError(f"values of {key!r} are not read")


@pytest.mark.parametrize("key", [5, "é", b"x"])
def test_parameters_differ_from_a_mapping_with_a_key_no_parameter_can_have(key: Any) -> None:
    params = Preference("a", None, {"x": "1"}).params
    assert (params == Unreadable([key])) is False
    assert (params != Unreadable([key])) is True


def test_parameters_differ_from_a_mapping_with_keys_equal_after_folding() -> None:
    params = Preference("a", None, {"x": "1"}).params
    assert (params == Unreadable(["x", "X"])) is False


class Missing(Mapping[str, str]):
    """A mapping that lists a key its lookup does not find."""

    def __iter__(self) -> Iterator[str]:
        return iter(["a"])

    def __len__(self) -> int:
        return 1

    def __getitem__(self, name: str) -> str:
        raise KeyError(name)


class NoItems(dict[str, Any]):
    def items(self) -> Any:
        raise AttributeError("items")


@pytest.mark.parametrize(
    ("params", "error"), [(Missing(), "KeyError"), (NoItems(a="1"), "AttributeError")]
)
def test_unreadable_params_name_the_error_that_stopped_the_read(params: Any, error: str) -> None:
    with pytest.raises(TypeError) as caught:
        Preference("x", None, params)
    assert str(caught.value) == f"params could not be read as a mapping ({error})"
