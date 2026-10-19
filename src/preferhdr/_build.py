"""Build a Prefer or Preference-Applied field value from preferences."""

from __future__ import annotations

from collections.abc import Iterable

from ._errors import PreferError
from ._grammar import show, type_name
from ._model import Preference


def build(prefs: Iterable[Preference], *, applied: bool = False) -> str:
    """Serialise preferences into one comma-separated field value.

    Every name and value was checked when its ``Preference`` was made, so the result can
    never split a header. Values that are tokens are written bare, others as quoted
    strings. A repeated preference raises ``PreferError`` (a sender should not repeat
    one), and so does a parameter when ``applied=True``, as ``Preference-Applied``
    carries none. An empty iterable gives ``""``: send no header at all in that case.
    Anything other than a ``Preference`` in ``prefs`` raises ``TypeError``.

    >>> from preferhdr import Preference, parse
    >>> build([Preference("return", "minimal"), Preference("note", "a, b", {"x": None})])
    'return=minimal, note="a, b"; x'
    >>> build(parse("wait=10; x=1").applied("wait"), applied=True)
    'wait=10'
    """
    seen: set[str] = set()
    parts: list[str] = []
    for pref in prefs:
        if not isinstance(pref, Preference):
            raise TypeError(f"expected Preference, not {type_name(pref)}")
        if pref.token in seen:
            raise PreferError(f"repeated preference {show(pref.token)}")
        if applied and pref.params:
            raise PreferError(f"Preference-Applied takes no parameters ({show(pref.token)})")
        seen.add(pref.token)
        parts.append(str(pref))
    return ", ".join(parts)
