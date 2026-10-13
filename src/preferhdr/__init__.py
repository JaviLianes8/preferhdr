"""Parse and build HTTP Prefer and Preference-Applied headers per RFC 7240."""

from __future__ import annotations

from ._build import build
from ._errors import PreferError
from ._model import Preference
from ._parse import parse
from ._prefs import Preferences
from ._vary import vary

__version__ = "0.2.0"

__all__ = ["PreferError", "Preference", "Preferences", "build", "parse", "vary"]
