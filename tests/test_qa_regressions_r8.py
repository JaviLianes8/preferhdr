"""Regression tests for the eighth round of the independent QA lenses."""

from __future__ import annotations

from collections.abc import Iterator, Mapping

import pytest

from preferhdr import Preference


class LookupDiffers(dict[str, str]):
    """A dict subclass whose own lookup disagrees with its storage."""

    def __getitem__(self, key: str) -> str:
        return "2"


def test_parameters_read_a_dict_subclass_the_way_construction_reads_it() -> None:
    params = Preference("a", None, {"x": "1"}).params
    other = LookupDiffers({"x": "1"})
    built = Preference("a", None, other).params
    assert dict(built) == {"x": "2"}
    assert (params == other) is (built == params) is False
    assert (params != other) is True
    assert built == LookupDiffers({"x": "1"})


class LongerThanItLists(Mapping[str, str]):
    """A mapping that iterates one key while its length claims two."""

    def __iter__(self) -> Iterator[str]:
        return iter(["x"])

    def __len__(self) -> int:
        return 2

    def __getitem__(self, key: str) -> str:
        return "1"


def test_parameters_count_the_keys_a_mapping_lists_not_its_length() -> None:
    params = Preference("a", None, {"x": "1"}).params
    other = LongerThanItLists()
    assert (Preference("a", None, other).params == params) is True
    assert (params == other) is True
    assert (params != other) is False


class Unreadable(Mapping[str, str]):
    """A mapping whose keys can be listed but whose values must never be read."""

    def __init__(self, keys: list[str]) -> None:
        self._keys = keys

    def __iter__(self) -> Iterator[str]:
        return iter(self._keys)

    def __len__(self) -> int:
        return len(self._keys)

    def __getitem__(self, key: str) -> str:
        raise LookupError(f"values of {key!r} are not read")


@pytest.mark.parametrize("keys", [[], ["y", "z"], ["x", "y"]])
def test_parameters_differ_from_a_mapping_with_another_number_of_keys(keys: list[str]) -> None:
    params = Preference("a", None, {"x": "1"}).params
    assert (params == Unreadable(keys)) is False
    assert (params != Unreadable(keys)) is True


class FailingLookup(Mapping[str, str]):
    """A mapping that lists the key ``a`` and whose lookup raises ``KeyError('inner')``."""

    def __iter__(self) -> Iterator[str]:
        return iter(["a"])

    def __len__(self) -> int:
        return 1

    def __getitem__(self, key: str) -> str:
        raise KeyError("inner")


def test_an_unreadable_params_mapping_hides_the_inner_error() -> None:
    with pytest.raises(TypeError) as caught:
        Preference("x", None, FailingLookup())
    assert str(caught.value) == "params could not be read as a mapping (KeyError)"
    assert caught.value.__cause__ is None
    assert caught.value.__suppress_context__ is True
