"""Parse and build HTTP Prefer and Preference-Applied headers per RFC 7240."""

from __future__ import annotations

from ._build import build
from ._model import Preference
from ._parse import parse

__version__ = "0.1.0"

__all__ = ["Preference", "build", "parse"]
