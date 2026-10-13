"""Add Prefer to a Vary field value, as RFC 7240 section 2 requires of some servers."""

from __future__ import annotations

from collections.abc import Iterable

from ._errors import PreferError
from ._grammar import is_token


def vary(current: str | Iterable[str] | None = None) -> str:
    """Return the ``Vary`` value with ``Prefer`` listed once.

    A server that may apply a preference changing what a cache can reuse must list
    ``Prefer`` in ``Vary``, whether or not this request sent one. ``current`` is the
    existing value (or several, one per header line). A list holding ``*`` already covers
    every field and comes back as ``*``. Members must be field names (tokens).
    """
    if isinstance(current, (bytes, bytearray)):
        raise TypeError("Vary values must be str, not bytes")
    fields = [] if current is None else [current] if isinstance(current, str) else list(current)
    members: list[str] = []
    for field in fields:
        if not isinstance(field, str):
            raise TypeError(f"Vary values must be str, not {type(field).__name__}")
        for raw in field.split(","):
            member = raw.strip(" \t")
            if not member:
                continue
            if member != "*" and not is_token(member):
                raise PreferError(f"{member!r} is not a field name")
            members.append(member)
    if "*" in members:
        return "*"
    if not any(member.lower() == "prefer" for member in members):
        members.append("Prefer")
    return ", ".join(members)
