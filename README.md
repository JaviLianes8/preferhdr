# preferhdr

[![Lianes8 Certified](https://lianes8studio.com/certified/lianes8-certified-badge.svg)](https://lianes8studio.com/certified)

Parse, validate and build the HTTP `Prefer` and `Preference-Applied` headers (RFC 7240),
typed and zero-dependency.

## Install

```
pip install preferhdr
```

## Reading a request

`parse` takes the field value, or several values when the request carries several
`Prefer` lines, and answers the questions a server asks about the registered preferences:

```python
from preferhdr import parse

prefs = parse(["respond-async, wait=10", 'return=minimal; foo="some parameter"'])
print(prefs.respond_async, prefs.wait, prefs.return_, prefs.handling)
# True 10 minimal None
print(prefs.get("return"))
# return=minimal; foo="some parameter"
applied = prefs.get("return")
assert applied is not None  # get() gives None when the preference is absent
print("Wait" in prefs, applied.params["foo"])
# True some parameter
```

Names are case-insensitive, so they come back lower-cased; values are kept verbatim, and
an empty value (`foo=""`) is the same as no value. When a preference is repeated, only the
first one counts, as RFC 7240 asks:

```python
from preferhdr import parse

print(list(parse('Return=minimal, return=representation, foo=""')))
# [Preference(token='return', value='minimal', params={}), Preference(token='foo', value=None, params={})]
```

The default parser is tolerant, as a server must be: it accepts whitespace around `=` and
empty list elements, reads CR, LF and NUL as spaces, and skips a malformed member (or a
malformed parameter) while keeping the rest. It never raises `PreferError`:

```python
from preferhdr import parse

print(list(parse("wait = 5, bad member, , handling=lenient; x=@")))
# [Preference(token='wait', value='5', params={}), Preference(token='handling', value='lenient', params={})]
```

## Validating a value

`strict=True` checks the grammar a sender must follow (RFC 7240 with erratum 4439, RFC
9110 lists) and reports the first problem with its position:

```python
from preferhdr import PreferError, parse

try:
    parse(["respond-async", "wait =10"], strict=True)
except PreferError as error:
    print(error.message, error.position, error.field)
# whitespace before '=' 4 1
```

## Answering

`Preferences.applied` keeps the preferences a server honoured, without their parameters,
ready for `Preference-Applied`. `build` writes any list of preferences, and `vary` adds
`Prefer` to the `Vary` header, which RFC 7240 requires whenever a preference can change
what a cache may reuse:

```python
from preferhdr import Preference, build, parse, vary

prefs = parse("return=representation; x=1, respond-async")
print(build(prefs.applied("return"), applied=True))
# return=representation
print(build([Preference("return", "minimal"), Preference("note", "a, b")]))
# return=minimal, note="a, b"
print(vary("Accept-Encoding"))
# Accept-Encoding, Prefer
```

Every name and value is checked when the `Preference` is made, so the builder can never
split a header:

```python
from preferhdr import Preference, PreferError

try:
    Preference("return", "minimal\r\nSet-Cookie: a=1")
except PreferError as error:
    print(error)
# value of 'return' holds U+000D, which a header field cannot carry
```

## Command line

`preferhdr` checks a value (or the `Prefer` lines of a request on stdin, as copied from a
log) and prints one preference per line, exiting with 1 when the value breaks the grammar:

```
$ preferhdr 'Respond-Async, wait=10, return=minimal; foo="some parameter"'
respond-async
wait=10
return=minimal; foo="some parameter"
$ preferhdr 'wait = 10'
wait=10
invalid: whitespace before '=' at position 4 of field 0
```

`--applied` reads `Preference-Applied` instead, `--json` prints JSON.

## API

| Name | What it does |
| --- | --- |
| `parse(value, *, strict=False, applied=False)` | Field value or values to `Preferences`. |
| `Preferences` | Immutable sequence: `get`, `in`, `respond_async`, `return_`, `wait`, `handling`, `applied(*names)`. |
| `Preference(token, value=None, params={})` | One validated, hashable preference; `str()` writes it. |
| `build(prefs, *, applied=False)` | Preferences to one field value. |
| `vary(current=None)` | A `Vary` value that lists `Prefer` once. |
| `PreferError` | `ValueError` with `message`, `position` and `field`. |

## Where the RFC leaves room

- `return=minimal, return=representation` (and the same with `handling`): sections 4.2
  and 4.4 say such a request may be treated as if neither was sent; section 2 says the
  first instance is the one considered. This library applies the first-wins rule, so
  `return_` is `"minimal"`.
- `Prefer: Lenient` names a preference called `lenient`, not `handling=lenient`
  (erratum 4955).
- A repeated parameter keeps its first value, like a repeated preference.
- `respond_async` is `True` only for the bare preference; `return_` and `handling` only
  for the values the RFC defines (values are case-sensitive).
- `wait` must be ASCII digits; a value longer than 100 digits reads as no wait at all
  (it is an upper bound, and no bound means the same thing).
- An unterminated quoted string runs to the end of its field value, so the tolerant
  parser drops its member and whatever follows it in that value.
- Values may hold obs-text as opaque data, U+00A0 to U+00FF. The C1 controls (U+0080 to
  U+009F) are rejected although RFC 9110 allows them: U+0085 is a line break to Python's
  `str.splitlines`, and they carry no text. Anything above U+00FF is rejected too.
- Names are matched case-insensitively in ASCII only, as tokens are ASCII.
- Strict mode accepts a repeated parameter (no rule forbids it) and keeps the first.
- On stdin the command line reads the header section only (up to the first empty line)
  and joins folded lines with a space (RFC 9112 section 5.2).

## Why

RFC 7240 is small but fiddly: optional values, quoted strings holding commas and
semicolons, case-insensitive names, several header lines, first-wins duplicates, and a
grammar fixed by errata. Hand-rolled splitting breaks on quoted values and lets CR LF
through into responses.

Python has no parser for it. The standard library's `urllib.request.parse_http_list`
and `email.message.Message.get_params` can be combined to split such a value, but they
know nothing of RFC 7240: they keep empty and repeated members, fold the case of some
names and not others, and misread a quoted value holding an escaped `"`. The PyPI
packages with "prefer" in their name (checked 2026-10-19) are about application
settings, not this header, and Werkzeug 3.1.9, Django 6.1.2 and Starlette 1.9.0 do not
read it. In JavaScript, `parse-prefer-header` 1.0.0 reads it into camel-case keys, drops
the value of a quoted string holding an escaped `"` and has no strict mode or builder.
The test suite runs both against this library and asserts every difference.

`preferhdr` is one small, typed, zero-dependency codec for both directions: a tolerant
reader for servers, a strict checker for tests and clients, a builder that cannot split
a header, and typed answers for the registered preferences.

## Ground truth

The strict grammar, the registered preferences and the errata are read from the RFC
text, the RFC Editor errata page and the IANA registry, fetched by
`scripts/fetch_upstream.py` and checked against the hashes in `tests/upstream/MANIFEST.json`
(the files are not shipped). The [GUIDE](https://github.com/JaviLianes8/preferhdr/blob/main/GUIDE.md)
gives every rule the parser follows.

## License

MIT. See [LICENSE](https://github.com/JaviLianes8/preferhdr/blob/main/LICENSE).

## Links

- Guide: https://github.com/JaviLianes8/preferhdr/blob/main/GUIDE.md
- Changelog: https://github.com/JaviLianes8/preferhdr/blob/main/CHANGELOG.md
- Website: https://lianes8studio.com
- GitHub: https://github.com/JaviLianes8
- LinkedIn: https://www.linkedin.com/in/jlianes/
