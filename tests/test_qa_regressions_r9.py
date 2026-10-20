"""Regression tests for the ninth round of the independent QA lenses."""

from __future__ import annotations

from collections.abc import ItemsView, Iterator, Mapping
from typing import Any

import pytest

from preferhdr import Preference
from preferhdr._model import Params


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


def test_two_keys_that_fold_together_differ_from_as_many_parameters() -> None:
    params = Preference("a", None, {"x": "1", "y": "2"}).params
    assert (params == Unreadable(["x", "X"])) is False
    assert (params != Unreadable(["x", "X"])) is True


class FailingLookup(Mapping[str, str]):
    """A mapping that lists the key ``a`` and whose lookup raises ``KeyError('inner')``."""

    def __iter__(self) -> Iterator[str]:
        return iter(["a"])

    def __len__(self) -> int:
        return 1

    def __getitem__(self, key: str) -> str:
        raise KeyError("inner")


@pytest.mark.parametrize("compare", [lambda p, m: p == m, lambda p, m: p != m])
def test_comparing_with_an_unreadable_mapping_lets_its_error_through(compare: Any) -> None:
    params = Preference("a", None, {"a": "1"}).params
    with pytest.raises(KeyError) as caught:
        compare(params, FailingLookup())
    assert caught.value.args == ("inner",)


class Lower(dict[str, Any]):
    pass


class DictSubclassStorage(Params):
    """A parameter mapping whose storage is a ``dict`` subclass holding an upper-case key."""

    def __init__(self) -> None:
        self.__dict__["_items"] = Lower(A="1")


def test_storage_held_in_a_dict_subclass_is_read_through_the_lookups() -> None:
    with pytest.raises(TypeError, match=r"^params could not be read as a mapping \(KeyError\)$"):
        Preference("x", None, DictSubclassStorage())


class IterMore(Params):
    def __iter__(self) -> Iterator[str]:
        return iter(["a", "b"])


def test_a_subclass_overriding_only_iteration_is_read_through_it() -> None:
    with pytest.raises(TypeError, match=r"^params could not be read as a mapping \(KeyError\)$"):
        Preference("x", None, IterMore({"a": "1"}))


class LookTwo(Params):
    def __getitem__(self, name: str) -> str:
        return "2"


def test_a_subclass_overriding_only_lookup_is_read_through_it() -> None:
    assert dict(Preference("x", None, LookTwo({"a": "1"})).params) == {"a": "2"}


class ShadowedStorage(Params):
    """Storage in the instance, hidden from attribute access by a class property."""

    def __init__(self) -> None:
        self.__dict__["_items"] = {"a": "1"}

    @property
    def _items(self) -> dict[str, str | None]:  # type: ignore[override]
        return {"b": "2"}


def test_inherited_storage_is_read_for_both_its_keys_and_its_values() -> None:
    assert dict(Preference("x", None, ShadowedStorage()).params) == {"a": "1"}


class ItemsOrder(Mapping[str, str]):
    """A mapping whose own ``items()`` lists ``a`` then ``b``; iteration lists ``b`` first."""

    def __iter__(self) -> Iterator[str]:
        return iter(["b", "a"])

    def __len__(self) -> int:
        return 2

    def __getitem__(self, key: str) -> str:
        return {"a": "1", "b": "2"}[key]

    def items(self) -> Any:
        return [("a", "1"), ("b", "2")]


class DictItemsOrder(dict[str, str]):
    """A ``dict`` subclass storing ``b`` first whose own ``items()`` lists ``a`` first."""

    def items(self) -> Any:
        return ItemsView({"a": "1", "b": "2"})


@pytest.mark.parametrize("params", [ItemsOrder(), DictItemsOrder(b="2", a="1")])
def test_parameters_keep_the_order_of_an_overridden_items(params: Mapping[str, str]) -> None:
    assert str(Preference("x", None, params)) == "x; a=1; b=2"
