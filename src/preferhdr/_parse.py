"""Parse Prefer or Preference-Applied field values into preferences."""

from __future__ import annotations

from collections.abc import Iterable

from ._errors import PreferError
from ._model import Preference
from ._prefs import Preferences
from ._scan import scan_field


def parse(
    value: str | Iterable[str], *, strict: bool = False, applied: bool = False
) -> Preferences:
    """Parse one field value, or several (one per header line), into preferences.

    Several values mean the same as their comma-separated concatenation (RFC 7240
    section 2). When a preference is repeated, only the first one counts; the same goes
    for a repeated parameter. Names are lower-cased and an empty value becomes ``None``.

    By default the parser is tolerant, as a server must be: whitespace around ``=`` and
    empty list elements are accepted, CR, LF and NUL read as spaces, and a malformed
    member (or a malformed parameter of a valid preference) is skipped. It never raises
    ``PreferError``.

    With ``strict=True`` the value must follow the grammar a sender is bound to (RFC 7240
    with erratum 4439, RFC 9110 lists): no empty elements, no whitespace around ``=``,
    no repeated preference. The first violation raises ``PreferError``.

    With ``applied=True`` the value is a ``Preference-Applied`` field, which carries no
    parameters: strict mode rejects them, tolerant mode drops them.
    """
    fields = [value] if isinstance(value, str) else list(value)
    seen: set[str] = set()
    out: list[Preference] = []
    for index, field in enumerate(fields):
        if not isinstance(field, str):
            raise TypeError(f"field values must be str, not {type(field).__name__}")
        try:
            members = scan_field(field, strict=strict, applied=applied)
        except PreferError as error:
            raise PreferError(error.message, error.position, index) from None
        for name, pref_value, params, start in members:
            if name in seen:
                if strict:
                    raise PreferError(f"repeated preference {name!r}", start, index)
                continue
            seen.add(name)
            first: dict[str, str | None] = {}
            for param, param_value in params:
                first.setdefault(param, param_value)
            out.append(Preference(name, pref_value, first))
    return Preferences(out)
