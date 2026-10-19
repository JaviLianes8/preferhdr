"""One preference: a validated, immutable, hashable value."""

from __future__ import annotations

from collections.abc import Iterator, Mapping
from dataclasses import dataclass, field

from ._errors import PreferError
from ._grammar import ascii_lower, check_name, check_value, quote, show, type_name


class Params(Mapping[str, "str | None"]):
    """Read-only parameters of a preference; names are matched case-insensitively."""

    def __init__(self, items: Mapping[str, str | None] | None = None) -> None:
        checked: dict[str, str | None] = {}
        for name, value in (items or {}).items():
            key = check_name(name, "parameter name")
            if key in checked:
                raise PreferError(f"repeated parameter {show(key)}")
            checked[key] = check_value(value, f"value of parameter {show(key)}")
        self._items = checked

    def __getitem__(self, name: str) -> str | None:
        key = ascii_lower(name)
        if key is None:
            raise KeyError(name)
        return self._items[key]

    def __iter__(self) -> Iterator[str]:
        return iter(self._items)

    def __len__(self) -> int:
        return len(self._items)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Mapping):
            return NotImplemented
        keys = [ascii_lower(key) for key in other]
        if None in keys or len(set(keys)) != len(other):
            return False
        return self._items == {ascii_lower(key): value for key, value in other.items()}

    def __hash__(self) -> int:
        return hash(frozenset(self._items.items()))

    def __repr__(self) -> str:
        return repr(self._items)


@dataclass(frozen=True)
class Preference:
    r"""One preference: a token, an optional value, and optional parameters.

    Names are checked to be tokens and lower-cased, since RFC 7240 compares them
    case-insensitively. Values are kept verbatim; an empty value becomes ``None``, as the
    RFC makes ``foo=""`` and ``foo`` equivalent. A value holding a character no header
    field can carry (CR, LF, other controls, anything above U+00FF) raises ``PreferError``;
    a name or value that is not a ``str``, or ``params`` that is not a mapping, raises
    ``TypeError``. Parameters are a read-only mapping; equality ignores their order.

    >>> pref = Preference("Return", "minimal", {"Foo": "a b"})
    >>> pref.token, pref.value, pref.params["FOO"]
    ('return', 'minimal', 'a b')
    >>> pref == Preference("return", "minimal", {"foo": "a b"}), Preference("x", "").value
    (True, None)
    >>> Preference("return", "minimal\r\nSet-Cookie: a=1")
    Traceback (most recent call last):
    ...
    preferhdr.PreferError: value of 'return' holds U+000D, which a header field cannot carry
    """

    token: str
    value: str | None = None
    params: Mapping[str, str | None] = field(default_factory=Params)

    def __post_init__(self) -> None:
        object.__setattr__(self, "token", check_name(self.token, "preference name"))
        object.__setattr__(self, "value", check_value(self.value, f"value of {show(self.token)}"))
        if not isinstance(self.params, Params):
            if not isinstance(self.params, Mapping):
                raise TypeError(f"params must be a mapping, not {type_name(self.params)}")
            object.__setattr__(self, "params", Params(self.params))

    # Written out rather than generated so that type checkers see a custom equality and
    # accept ``"wait" in prefs`` (a str looked up in a sequence of preferences).
    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Preference):
            return NotImplemented
        return (self.token, self.value, self.params) == (other.token, other.value, other.params)

    def __str__(self) -> str:
        r"""The preference as it is written in a header field.

        >>> print(Preference("return", "minimal", {"note": 'say "hi"', "x": None}))
        return=minimal; note="say \"hi\""; x
        """
        out = _pair(self.token, self.value)
        for name, value in self.params.items():
            out += "; " + _pair(name, value)
        return out


def _pair(name: str, value: str | None) -> str:
    return name if value is None else f"{name}={quote(value)}"
