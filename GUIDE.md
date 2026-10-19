# preferhdr guide

Everything `preferhdr` promises, rule by rule. The README is the short tour; this page is
the reference. Every example below runs as part of the test suite.

## The two parsers

`parse(value)` is the tolerant reader a server needs: it never raises `PreferError` and
keeps every well-formed preference it can find. `parse(value, strict=True)` checks the
grammar a sender is bound to and raises `PreferError` at the first problem.

| Input | Tolerant | Strict |
| --- | --- | --- |
| `wait = 5` (whitespace around `=`) | `wait=5` | error: whitespace before `=` |
| `a, , b` (empty list element) | `a`, `b` | error: empty list element |
| `a, @b, c` (malformed member) | `a`, `c` | error: expected a token |
| `a; x=@` (malformed parameter) | `a` | error: expected a token or quoted string |
| `a, A` (repeated preference) | `a` (the first) | error: repeated preference |
| `a; x=1; x=2` (repeated parameter) | `a; x=1` | `a; x=1` (no rule forbids it) |
| CR, LF or NUL | read as a space | error |
| `a, b="x, c` (unterminated quote) | `a`: the rest of that value is dropped | error |

The strict grammar is RFC 7240 section 2 with verified erratum 4439, built on the RFC
9110 rules for tokens, quoted strings, parameters and lists:

```
Prefer               = 1#preference
preference           = preference-parameter *( OWS ";" [ OWS preference-parameter ] )
preference-parameter = parameter / token
parameter            = token "=" ( token / quoted-string )
```

The test suite reads these rules from the RFC text and the errata page and checks that
strict mode accepts exactly what they allow, on tens of thousands of generated values.

```python
from preferhdr import PreferError, parse

print([str(p) for p in parse("wait = 5, a, , @b, c; x=@")])
# ['wait=5', 'a', 'c']
for value in ("a, A", "a; x=1; x=2"):
    try:
        print([str(p) for p in parse(value, strict=True)])
    except PreferError as error:
        print(error)
# repeated preference 'a' at position 3 of field 0
# ['a; x=1']
```

## Names and values

- Names (of preferences and parameters) compare without case, in ASCII only, and come
  back lower-cased. Values are case-sensitive and kept verbatim.
- An empty value is no value: `foo`, `foo=""` and `foo=` (tolerant) are the same.
- A quoted string is unquoted and its quoted pairs resolved: `"a\"b"` is `a"b`.
- Values may hold HTAB, SP, visible ASCII and the Latin-1 range U+00A0 to U+00FF. The
  C1 controls U+0080 to U+009F are refused although RFC 9110 allows them as obs-text:
  U+0085 is a line break to `str.splitlines` and none of them carries text.
- Header bytes are opaque octets. Decode them as Latin-1 before calling `parse`, which
  refuses `bytes`.

## Several header lines

A request may carry several `Prefer` lines; they mean the same as one line joined with
commas (RFC 7240 section 2). Pass them as a list. Error positions count characters
inside one value, and `field` says which one.

```python
from preferhdr import PreferError, parse

prefs = parse(["respond-async, wait=100", "handling=lenient"])
print(prefs.respond_async, prefs.wait, prefs.handling)
# True 100 lenient
try:
    parse(["respond-async", "wait=1, wait=2"], strict=True)
except PreferError as error:
    print(error.message, error.position, error.field)
# repeated preference 'wait' 8 1
```

## The registered preferences

| Property | Preference | Gives |
| --- | --- | --- |
| `respond_async` | `respond-async` | `True` only when present without a value |
| `return_` | `return` | `"minimal"`, `"representation"` or `None` |
| `wait` | `wait` | seconds as an `int` (ASCII digits, at most 100 after leading zeros) or `None` |
| `handling` | `handling` | `"strict"`, `"lenient"` or `None` |

Any other value reads as `None`, because the RFC defines no meaning for it. When a
preference is repeated only the first counts, so `return=minimal, return=representation`
gives `"minimal"`. `Prefer: Lenient` names a preference called `lenient`, not
`handling=lenient` (erratum 4955). Unregistered preferences are read like any other:
`prefs.get("depth-noroot")`.

## Answering: Preference-Applied and Vary

`prefs.applied(*names)` keeps the named preferences that were requested, in request
order and without parameters, and `build(..., applied=True)` writes them.
`parse(..., applied=True)` reads a `Preference-Applied` value: strict mode refuses
parameters (reported erratum 4625) and tolerant mode drops them. `vary(current)` adds
`Prefer` to a `Vary` value once, keeps `*` as it is, and refuses members that are not
field names.

```python
from preferhdr import build, parse, vary

prefs = parse("return=minimal; x=1, wait=5")
print(build(prefs.applied("return", "handling"), applied=True))
# return=minimal
print(vary(["Accept", "Accept-Encoding"]), vary("*"))
# Accept, Accept-Encoding, Prefer *
```

## Errors

| Raised | When |
| --- | --- |
| `PreferError` | strict parsing finds a grammar violation; `Preference` gets a name that is not a token, a value no header can carry or a repeated parameter; `build` gets a repeated preference, or parameters with `applied=True`; `vary` gets a member that is not a field name |
| `TypeError` | a value of the wrong type anywhere: `bytes` or a non-`str` field value, a non-`str` name or value, `params` that is not a mapping, a non-`Preference` in `build` or `Preferences`, a non-`str` name in `get` or `applied` |

`PreferError` is a `ValueError` with `message`, `position` (the character offset in the
field value) and `field` (the index among the values passed to `parse`); both are `None`
when they do not apply. It survives pickling. Every message quotes at most 40 characters
of the input and gives the length of anything longer, so huge input stays out of logs.

## Command line

`preferhdr VALUE...` (or `python -m preferhdr`) prints each preference on its own line
and checks the values in strict mode. Without arguments it reads stdin: the `Prefer`
lines of a request (or `Preference-Applied` with `--applied`) up to the first empty
line, with folded lines joined by a space, or plain values one per line when there are
no header lines. `--json` prints JSON. It exits 0 when every value is valid, 1 when one
is not, when no value is found or when its output pipe closes, and 2 on a usage error.

## Upgrading from 0.2.0

Every valid value reads and builds exactly as in 0.2.0; a test compares both releases on
tens of thousands of generated inputs. The differences are:

- `parse(None)` gives empty `Preferences` (0.2.0 raised `TypeError`).
- `Preferences.get` and `Preferences.applied` raise `TypeError` for a name that is not a
  `str` (0.2.0 answered `None` or skipped it).
- Messages quote at most 40 characters of the input, and `TypeError` messages name the
  type.
- The public classes report `preferhdr` as their module, and pickles name only public
  classes. Pickles written by 0.2.0 still load.
- The command exits 1 without a traceback when its output pipe closes.
