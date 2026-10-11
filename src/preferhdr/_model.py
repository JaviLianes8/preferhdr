"""The parsed form of a single preference."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Preference:
    """One preference: a token, an optional value, and optional parameters.

    A bare preference such as ``respond-async`` has ``value`` set to ``None``.
    A parameter with no value (for example ``;lenient``) maps to ``None`` too.
    """

    token: str
    value: str | None = None
    params: Mapping[str, str | None] = field(default_factory=dict)
