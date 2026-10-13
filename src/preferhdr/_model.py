"""One preference: a validated, immutable, hashable value."""

from __future__ import annotations

from collections.abc import Iterator, Mapping
from dataclasses import dataclass, field

from ._errors import PreferError
from ._grammar import check_name, check_value, quote


class Params(Mapping[str, "str | None"]):
    """Read-only parameters of a preference; names are matched case-insensitively."""

    def __init__(self, items: Mapping[str, str | None] | None = None) -> None:
        checked: dict[str, str | None] = {}
        for name, value in (items or {}).items():
            key = check_name(name, "parameter name")
            if key in checked:
                raise PreferError(f"repeated parameter {key!r}")
            checked[key] = check_value(value, f"value of parameter {key!r}")
        self._items = checked

    def __getitem__(self, name: str) -> str | None:
        return self._items[name.lower() if isinstance(name, str) else name]

    def __iter__(self) -> Iterator[str]:
        return iter(self._items)

    def __len__(self) -> int:
        return len(self._items)

    def __hash__(self) -> int:
        return hash(frozenset(self._items.items()))

    def __repr__(self) -> str:
        return repr(self._items)


@dataclass(frozen=True)
class Preference:
    """One preference: a token, an optional value, and optional parameters.

    Names are checked to be tokens and lower-cased, since RFC 7240 compares them
    case-insensitively. Values are kept verbatim; an empty value becomes ``None``, as the
    RFC makes ``foo=""`` and ``foo`` equivalent. A value holding a character no header
    field can carry (CR, LF, other controls, anything above U+00FF) raises ``PreferError``.
    """

    token: str
    value: str | None = None
    params: Mapping[str, str | None] = field(default_factory=Params)

    def __post_init__(self) -> None:
        object.__setattr__(self, "token", check_name(self.token, "preference name"))
        object.__setattr__(self, "value", check_value(self.value, f"value of {self.token!r}"))
        if not isinstance(self.params, Params):
            if not isinstance(self.params, Mapping):
                raise TypeError("params must be a mapping")
            object.__setattr__(self, "params", Params(self.params))

    # Written out rather than generated so that type checkers see a custom equality and
    # accept ``"wait" in prefs`` (a str looked up in a sequence of preferences).
    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Preference):
            return NotImplemented
        return (self.token, self.value, self.params) == (other.token, other.value, other.params)

    def __str__(self) -> str:
        """The preference as it is written in a header field."""
        out = _pair(self.token, self.value)
        for name, value in self.params.items():
            out += "; " + _pair(name, value)
        return out


def _pair(name: str, value: str | None) -> str:
    return name if value is None else f"{name}={quote(value)}"
