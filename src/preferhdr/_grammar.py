"""RFC 9110 tokens and quoted strings, shared by the parser, the model and the builder."""

from __future__ import annotations

from ._errors import PreferError

TCHAR = frozenset("!#$%&'*+-.^_`|~0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz")
# Messages quote at most this many characters of a value, so huge input stays out of logs.
SHOWN = 40


def show(text: str) -> str:
    """Quote text for a message, cut to ``SHOWN`` characters with a note of its length."""
    if len(text) <= SHOWN:
        return repr(text)
    return f"{text[:SHOWN]!r}... ({len(text)} characters)"


def type_name(value: object) -> str:
    """The name of value's type for a message, cut like ``show`` cuts text."""
    name = str(type(value).__name__)
    return name if len(name) <= SHOWN else name[:SHOWN] + "..."


def exact(text: str) -> str:
    """The characters of a str as a plain str, whatever a subclass (an Enum) overrides."""
    # Checks and output must see the same characters; a subclass can change both iteration
    # and formatting, so only its underlying data is trusted.
    return str.__str__(text)


def is_token(text: str) -> bool:
    """Report whether text is a non-empty RFC 9110 token."""
    return bool(text) and all(ch in TCHAR for ch in text)


def is_text_char(ch: str) -> bool:
    """Report whether ch may appear in a quoted string: HTAB, SP, VCHAR or obs-text.

    obs-text stops short of the C1 controls (U+0080 to U+009F): RFC 9110 allows them, but
    U+0085 is a line break to ``str.splitlines`` and they carry no text in Latin-1.
    """
    return ch == "\t" or " " <= ch <= "~" or "\xa0" <= ch <= "\xff"


def ascii_lower(name: str) -> str | None:
    """Lower-case a name for lookup, or ``None`` when it is not ASCII (so cannot match)."""
    if not isinstance(name, str):
        return None
    name = exact(name)
    return name.lower() if name.isascii() else None


def check_name(name: object, what: str) -> str:
    if not isinstance(name, str):
        raise TypeError(f"{what} must be a str, not {type_name(name)}")
    name = exact(name)
    if not is_token(name):
        raise PreferError(f"{what} {show(name)} is not a token")
    # Names compare case-insensitively (RFC 7240 section 2); one spelling keeps equality exact.
    return name.lower()


def check_value(value: object, what: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise TypeError(f"{what} must be a str or None, not {type_name(value)}")
    value = exact(value)
    for ch in value:
        if not is_text_char(ch):
            raise PreferError(f"{what} holds U+{ord(ch):04X}, which a header field cannot carry")
    # An empty value is the same as no value at all (RFC 7240 section 2).
    return value or None


def quote(value: str) -> str:
    """Return value as a bare token when it is one, else as an escaped quoted string."""
    if is_token(value):
        return value
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'
