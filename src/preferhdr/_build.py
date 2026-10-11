"""Build a Prefer or Preference-Applied header value from preferences."""

from __future__ import annotations

from collections.abc import Iterable

from ._model import Preference
from ._quote import quote


def build(prefs: Iterable[Preference]) -> str:
    """Serialise preferences into a single comma-separated header value."""
    return ", ".join(_build_one(pref) for pref in prefs)


def _build_one(pref: Preference) -> str:
    out = _pair(pref.token, pref.value)
    for name, value in pref.params.items():
        out += "; " + _pair(name, value)
    return out


def _pair(name: str, value: str | None) -> str:
    if value is None:
        return name
    return f"{name}={quote(value)}"
