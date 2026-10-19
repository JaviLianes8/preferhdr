"""Parse Prefer or Preference-Applied field values into preferences."""

from __future__ import annotations

from collections.abc import Iterable

from ._errors import PreferError
from ._grammar import show, type_name
from ._model import Preference
from ._prefs import Preferences
from ._scan import scan_field


def parse(
    value: str | Iterable[str] | None, *, strict: bool = False, applied: bool = False
) -> Preferences:
    """Parse one field value, or several (one per header line), into preferences.

    Several values mean the same as their comma-separated concatenation (RFC 7240
    section 2), and ``None`` (a request without the header) gives no preferences. When a
    preference is repeated, only the first one counts; the same goes for a repeated
    parameter. Names are lower-cased and an empty value becomes ``None``.

    >>> prefs = parse(["respond-async, wait=10", 'Return=minimal; foo="a, b"'])
    >>> prefs.respond_async, prefs.wait, prefs.return_
    (True, 10, 'minimal')
    >>> prefs.get("return").params["foo"]
    'a, b'
    >>> parse(None)
    Preferences([])

    By default the parser is tolerant, as a server must be: whitespace around ``=`` and
    empty list elements are accepted, CR, LF and NUL read as spaces, and a malformed
    member (or a malformed parameter of a valid preference) is skipped. It never raises
    ``PreferError``.

    >>> [str(pref) for pref in parse("wait = 5, bad member, , handling=lenient; x=@")]
    ['wait=5', 'handling=lenient']

    With ``strict=True`` the value must follow the grammar a sender is bound to (RFC 7240
    with erratum 4439, RFC 9110 lists): no empty elements, no whitespace around ``=``,
    no repeated preference. The first violation raises ``PreferError``.

    >>> parse(["respond-async", "wait =10"], strict=True)
    Traceback (most recent call last):
    ...
    preferhdr.PreferError: whitespace before '=' at position 4 of field 1

    With ``applied=True`` the value is a ``Preference-Applied`` field, which carries no
    parameters: strict mode rejects them, tolerant mode drops them.

    >>> parse("return=minimal; x=1", applied=True)
    Preferences([Preference(token='return', value='minimal', params={})])

    A value that is not a ``str`` (bytes included: decode them as Latin-1 first), or an
    iterable holding one, raises ``TypeError``.
    """
    if isinstance(value, (bytes, bytearray)):
        raise TypeError("field values must be str, not bytes; decode them as Latin-1")
    if value is None or isinstance(value, str):
        fields: list[str] = [] if value is None else [value]
    else:
        try:
            values = iter(value)
        except TypeError:
            raise TypeError(
                f"expected a str or an iterable of str, not {type_name(value)}"
            ) from None
        fields = list(values)
    seen: set[str] = set()
    out: list[Preference] = []
    for index, field in enumerate(fields):
        if not isinstance(field, str):
            raise TypeError(f"field values must be str, not {type_name(field)}")
        try:
            members = scan_field(field, strict=strict, applied=applied)
        except PreferError as error:
            raise PreferError(error.message, error.position, index) from None
        for name, pref_value, params, start in members:
            if name in seen:
                if strict:
                    raise PreferError(f"repeated preference {show(name)}", start, index)
                continue
            seen.add(name)
            first: dict[str, str | None] = {}
            for param, param_value in params:
                first.setdefault(param, param_value)
            out.append(Preference(name, pref_value, first))
    return Preferences(out)
