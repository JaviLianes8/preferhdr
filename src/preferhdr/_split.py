"""Split a header on a separator while ignoring separators inside quoted-strings."""

from __future__ import annotations


def split_top(text: str, sep: str) -> list[str]:
    """Split text on sep at the top level, skipping separators within quotes."""
    parts: list[str] = []
    buf: list[str] = []
    in_quotes = False
    escaped = False
    for ch in text:
        if escaped:
            buf.append(ch)
            escaped = False
        elif ch == "\\" and in_quotes:
            buf.append(ch)
            escaped = True
        elif ch == '"':
            in_quotes = not in_quotes
            buf.append(ch)
        elif ch == sep and not in_quotes:
            parts.append("".join(buf))
            buf = []
        else:
            buf.append(ch)
    parts.append("".join(buf))
    return parts
