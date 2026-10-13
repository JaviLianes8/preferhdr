# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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
