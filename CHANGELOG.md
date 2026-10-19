# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.0.0] - 2026-10-19

The public API is now stable: `parse`, `build`, `vary`, `Preference`, `Preferences` and
`PreferError`, with the signatures, defaults and error types of 0.2.0. Every valid value
reads and builds exactly as in 0.2.0; the changes below only touch missing headers,
wrong argument types, error message texts and the command line.

### Added

- `parse(None)` gives empty `Preferences`, so a missing header needs no special case.
- Every public name, method and property carries a runnable example, checked as a doctest.
- `GUIDE.md`: every rule the parser follows, the error reference and upgrade notes.

### Changed

- Error messages quote at most 40 characters of a name, value or type name and give
  the length of anything longer; 0.2.0 quoted the whole input.
- `Preferences.get` and `Preferences.applied` raise `TypeError` for a name that is not a
  `str`; 0.2.0 answered `None` or skipped it.
- `parse` of something that is neither a `str` nor an iterable raises `TypeError` with a
  message naming the type (0.2.0 raised Python's own "not iterable" `TypeError`).
- `Preference(..., params=...)` with something other than a mapping names the type in
  its `TypeError` message.
- `PreferError`, `Preference` and `Preferences` report `preferhdr` as their module, so
  they show and pickle as `preferhdr.<Name>`; a pickled `Preference` stores its
  parameters as a plain `dict`, so no pickle names a private module. Pickles written by
  0.2.0 still load.
- The `preferhdr` command exits 1 without a traceback when the reader of its output
  goes away, and cuts argparse's echo of an unknown argument to 200 characters.
- `python -m preferhdr` no longer runs the command when the module is merely imported.
- Classifier `Development Status :: 5 - Production/Stable`.

## [0.2.0]

### Added

- `parse` accepts several field values (one per header line) and reads them as one list.
- `parse(..., strict=True)` checks the sender grammar (RFC 7240 with erratum 4439, RFC
  9110 lists) and raises `PreferError` with the position and field index.
- `parse(..., applied=True)` and `build(..., applied=True)` for `Preference-Applied`,
  which carries no parameters.
- `Preferences`, the result of `parse`: an immutable sequence with case-insensitive `get`
  and `in`, typed `respond_async`, `return_`, `wait` and `handling`, and `applied(*names)`.
- `vary()` adds `Prefer` to a `Vary` value once.
- `PreferError`, a `ValueError` with `message`, `position` and `field`.
- `str(preference)` writes one preference.
- A `preferhdr` command (and `python -m preferhdr`) that prints and checks a value.

### Changed

- `parse` returns `Preferences` (a tuple subclass) instead of a list.
- Only the first of a repeated preference or parameter is kept (RFC 7240 section 2).
- An empty value (`foo=""`) is `None`, the same as no value.
- Only SP and HTAB count as whitespace; CR, LF and NUL read as spaces; a malformed
  member or parameter is skipped instead of being returned half parsed.
- `Preference` checks names are tokens and values fit in a header field, lower-cases
  names, and keeps its parameters in an immutable, hashable mapping.
- `build` refuses a repeated preference, so any non-empty output passes strict parsing.

### Fixed

- A name or value holding CR or LF could split the header written by `build`.
- `Preference` was not hashable and its parameters could be changed after creation.

## [0.1.0]

- First release: `parse` and `build` for the HTTP Prefer and Preference-Applied
  headers per RFC 7240, with a typed `Preference` model covering token preferences,
  valued preferences (bare or quoted), parameters, and multiple comma-separated
  preferences. Zero dependencies.
