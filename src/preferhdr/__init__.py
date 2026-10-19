"""Parse and build HTTP Prefer and Preference-Applied headers per RFC 7240."""

from ._build import build
from ._errors import PreferError
from ._model import Preference
from ._parse import parse
from ._prefs import Preferences
from ._vary import vary

__version__ = "1.0.0"

# The public classes show and pickle as preferhdr.<Name>, so a pickle never depends on
# the private module that defines them.
for _cls in (PreferError, Preference, Preferences):
    _cls.__module__ = __name__
    # Methods follow, so doctest finds their examples here (it takes properties anyway).
    for _member in vars(_cls).values():
        if callable(_member) and str(getattr(_member, "__module__", "")).startswith("preferhdr._"):
            _member.__module__ = __name__
del _cls, _member

__all__ = ["PreferError", "Preference", "Preferences", "build", "parse", "vary"]
