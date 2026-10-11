# preferhdr

Parse and build HTTP Prefer and Preference-Applied headers per RFC 7240, typed and zero-dependency.

## Install

```
pip install preferhdr
```

## Usage

```python
from preferhdr import Preference, build, parse

prefs = parse("respond-async, wait=10, return=minimal")
# [Preference(token='respond-async', value=None, params={}),
#  Preference(token='wait', value='10', params={}),
#  Preference(token='return', value='minimal', params={})]

prefs[0].token          # 'respond-async'
prefs[1].value          # '10'

# Preference names are case-insensitive, so they come back lower-cased.
# Values are kept verbatim; a bare token has value None.
parse("Handling=strict")  # [Preference(token='handling', value='strict', params={})]

# Parameters ride along a preference and may themselves be bare or quoted.
parse('foo=bar; baz=qux; lenient')
# [Preference(token='foo', value='bar', params={'baz': 'qux', 'lenient': None})]

# Build a header value back. Values that are not plain tokens get quoted.
build([Preference("return", "minimal"), Preference("wait", "10")])
# 'return=minimal, wait=10'

build([Preference("foo", "a, b")])
# 'foo="a, b"'
```

The same functions cover the `Preference-Applied` response header, which shares the
grammar of a comma-separated list of preferences.

## Why

RFC 7240 defines the `Prefer` request header (`respond-async`, `return=minimal`,
`return=representation`, `wait=10`, `handling=strict`, and arbitrary token or
quoted-value preferences with parameters) and the matching `Preference-Applied`
response header. The grammar is small but fiddly: parameters, optional values,
quoted-strings that may contain commas and semicolons, and case-insensitive names.

Python has no dedicated package for it. The logic is copied by hand into frameworks
such as Apache Olingo (Java) or left to ad-hoc string splitting that breaks on quoted
values. `ietfparse` and `rfcparser` do not ship a ready Prefer codec. This library is a
small, fully typed, zero-dependency codec that parses a header into preferences and
builds one back, round-tripping cleanly.

## License

MIT. See [LICENSE](LICENSE).

## Links

- Website: https://lianes8studio.com
- GitHub: https://github.com/JaviLianes8
- LinkedIn: https://www.linkedin.com/in/jlianes/
