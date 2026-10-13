"""The parsed preferences of a request, with typed answers for the registered ones."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Literal

from ._model import Preference

# More digits than this cannot be a meaningful number of seconds, and converting them
# costs quadratic time; such a wait reads as no upper bound, the same as no wait at all.
_MAX_WAIT_DIGITS = 100
_DIGITS = frozenset("0123456789")


class Preferences(tuple[Preference, ...]):
    """An immutable sequence of preferences in request order.

    ``name in prefs`` and ``prefs.get(name)`` match names case-insensitively and return
    the first match. The properties read the preferences registered by RFC 7240 and give
    ``None`` (or ``False``) when the preference is absent or its value is not one the RFC
    defines.
    """

    __slots__ = ()

    def __new__(cls, prefs: Iterable[Preference] = ()) -> Preferences:
        items = tuple(prefs)
        for pref in items:
            if not isinstance(pref, Preference):
                raise TypeError(f"expected Preference, not {type(pref).__name__}")
        return super().__new__(cls, items)

    def get(self, name: str) -> Preference | None:
        """The first preference with this name, or ``None``."""
        key = name.lower()
        return next((pref for pref in self if pref.token == key), None)

    def __contains__(self, item: object) -> bool:
        if isinstance(item, str):
            return self.get(item) is not None
        return super().__contains__(item)

    def _value(self, name: str) -> str | None:
        pref = self.get(name)
        return None if pref is None else pref.value

    @property
    def respond_async(self) -> bool:
        """``True`` when ``respond-async`` is present without a value."""
        pref = self.get("respond-async")
        return pref is not None and pref.value is None

    @property
    def return_(self) -> Literal["minimal", "representation"] | None:
        """``"minimal"`` or ``"representation"`` from ``return``, else ``None``."""
        value = self._value("return")
        if value == "minimal":
            return "minimal"
        if value == "representation":
            return "representation"
        return None

    @property
    def handling(self) -> Literal["strict", "lenient"] | None:
        """``"strict"`` or ``"lenient"`` from ``handling``, else ``None``."""
        value = self._value("handling")
        if value == "strict":
            return "strict"
        if value == "lenient":
            return "lenient"
        return None

    @property
    def wait(self) -> int | None:
        """The ``wait`` value in seconds (``delay-seconds``, ASCII digits), else ``None``."""
        value = self._value("wait")
        if value is None or not set(value) <= _DIGITS:
            return None
        digits = value.lstrip("0") or "0"
        return int(digits) if len(digits) <= _MAX_WAIT_DIGITS else None

    def applied(self, *names: str) -> Preferences:
        """The preferences among ``names`` that are present, for ``Preference-Applied``.

        Parameters are dropped, since that header carries none (RFC 7240 section 3).
        Names that were not requested are skipped.
        """
        wanted = {name.lower() for name in names}
        kept = (Preference(pref.token, pref.value) for pref in self if pref.token in wanted)
        return Preferences(kept)

    def __repr__(self) -> str:
        return f"Preferences({list(self)!r})"
