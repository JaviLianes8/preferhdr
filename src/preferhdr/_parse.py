"""Parse a Prefer or Preference-Applied header value into preferences."""

from __future__ import annotations

from ._model import Preference
from ._quote import unquote
from ._split import split_top


def parse(header: str) -> list[Preference]:
    """Parse a header value into a list of preferences, tolerating empty entries.

    Preference and parameter names are lower-cased, since they are case-insensitive
    per RFC 7240. Values are kept verbatim. Blank or nameless entries are skipped.
    """
    prefs: list[Preference] = []
    for element in split_top(header, ","):
        pref = _parse_element(element)
        if pref is not None:
            prefs.append(pref)
    return prefs


def _parse_element(element: str) -> Preference | None:
    parts = split_top(element, ";")
    token, value = _parse_pair(parts[0])
    if not token:
        return None
    params: dict[str, str | None] = {}
    for part in parts[1:]:
        name, param_value = _parse_pair(part)
        if name:
            params[name] = param_value
    return Preference(token=token, value=value, params=params)


def _parse_pair(part: str) -> tuple[str, str | None]:
    name, sep, raw = part.partition("=")
    if not sep:
        return name.strip().lower(), None
    return name.strip().lower(), unquote(raw.strip())
