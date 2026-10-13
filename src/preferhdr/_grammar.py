"""RFC 9110 tokens and quoted strings, shared by the parser, the model and the builder."""

from __future__ import annotations

from ._errors import PreferError

TCHAR = frozenset("!#$%&'*+-.^_`|~0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz")


def is_token(text: str) -> bool:
    """Report whether text is a non-empty RFC 9110 token."""
    return bool(text) and all(ch in TCHAR for ch in text)


def is_text_char(ch: str) -> bool:
    """Report whether ch may appear in a quoted string: HTAB, SP, VCHAR or obs-text."""
    return ch == "\t" or " " <= ch <= "~" or "\x80" <= ch <= "\xff"


def check_name(name: object, what: str) -> str:
    if not isinstance(name, str):
        raise TypeError(f"{what} must be a str, not {type(name).__name__}")
    if not is_token(name):
        raise PreferError(f"{what} {name!r} is not a token")
    # Names compare case-insensitively (RFC 7240 section 2); one spelling keeps equality exact.
    return name.lower()


def check_value(value: object, what: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise TypeError(f"{what} must be a str or None, not {type(value).__name__}")
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
