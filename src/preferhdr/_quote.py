"""Token and quoted-string helpers from RFC 7230, shared by the parser and builder."""

from __future__ import annotations

_TCHAR = frozenset("!#$%&'*+-.^_`|~0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz")


def is_token(text: str) -> bool:
    """Report whether text is a non-empty RFC 7230 token (no quoting needed)."""
    return bool(text) and all(ch in _TCHAR for ch in text)


def quote(value: str) -> str:
    """Return value as a bare token when it qualifies, else a quoted-string."""
    if is_token(value):
        return value
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def unquote(word: str) -> str:
    """Strip the quotes and quoted-pairs from a word; a bare token is kept as-is."""
    if len(word) >= 2 and word[0] == '"' and word[-1] == '"':
        return _unescape(word[1:-1])
    return word


def _unescape(inner: str) -> str:
    out: list[str] = []
    i = 0
    while i < len(inner):
        ch = inner[i]
        if ch == "\\" and i + 1 < len(inner):
            out.append(inner[i + 1])
            i += 2
        else:
            out.append(ch)
            i += 1
    return "".join(out)
