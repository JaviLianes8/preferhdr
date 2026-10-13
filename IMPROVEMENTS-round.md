# preferhdr improvement round

Progress:
- [x] Brainstorm ranked improvements (this file)
- [x] Pin the ground truth: RFC 7240 and its errata, RFC 8144, RFC 9110, IANA registry
- [x] Tolerant parser: several fields, OWS only, empty values, first wins, malformed members
- [x] Strict parser for the sender grammar with error positions
- [x] Validated model and safe builder: no header injection, Preference-Applied without params
- [x] Typed accessors (respond-async, return, wait, handling), applied helper, Vary helper
- [x] Command line checker
- [x] Contracts: RFC examples (local fetched copy), cited vectors, round trip, README, typing
- [x] Docs and packaging: README, CHANGELOG, metadata, installed-wheel e2e test
- [x] Gates: ruff format, ruff check, mypy --strict, pytest
- [x] Mutation run: removing guarded logic makes the suite fail
- [x] Independent review findings fixed with regression tests
- [ ] Pull request opened, guard clean

## Starting point

`0.1.0` gives `Preference`, `parse` and `build`. Compared with the sources below:

- `parse` takes one string only, so several `Prefer` fields cannot be combined as RFC 7240
  section 2 requires.
- `foo=""` comes back with the value `""`, although section 2 says an empty value is the
  same as no value (`foo; bar`, `foo; bar=""` and `foo=""; bar` are equivalent).
- A repeated preference is returned twice; section 2 says only the first one counts.
- Whitespace is removed with `str.strip()`, which also eats CR, LF, vertical tab and
  Unicode spaces. RFC 9110 only allows SP and HTAB as OWS/BWS.
- Anything that is not a token is accepted as a name (`a b=1` gives the name `a b`), a
  value such as `"a"b` or an unterminated quote is returned half unquoted, and CR, LF or
  NUL pass through untouched.
- `build` never checks names or values: a name or value holding CR LF splits the header
  (header injection), and controls or characters a field cannot carry are written as is.
- `Preference` is declared frozen but holds a plain `dict`, so it can be changed through
  `params` and cannot be hashed.
- There are no typed answers to the questions a server actually asks (is `respond-async`
  set, what is `wait` as a number, `return`, `handling`), no help to build
  `Preference-Applied` from what was honoured, and nothing about `Vary: Prefer`.

## Sources (fetched 2026-10-13)

- RFC 7240, https://www.rfc-editor.org/rfc/rfc7240.txt (sha256
  2cde510338babf6ad937e0bcb31989bb9a664ab1567d4b41cb143fe9740ae16e): section 2 (ABNF,
  empty values, case rules, several fields, first instance wins, Vary), 2.1 examples,
  section 3 (Preference-Applied carries no parameters), section 4 (respond-async,
  return, wait, handling and their mutual exclusion).
- RFC 7240 errata, https://www.rfc-editor.org/errata/rfc7240: 4439 (verified, the grammar
  reuses the RFC 9110 `parameter` and drops the undefined `word`), 4316 (verified,
  `delay-seconds` instead of `delta-seconds`), 4625 (reported, Preference-Applied with the
  same element rule), 4955 (reported, `Prefer: Lenient` names a preference `lenient`, it
  is not `handling=lenient`), 4317 (rejected, commas separate preferences).
- RFC 8144, https://www.rfc-editor.org/rfc/rfc8144.txt (sha256
  94783f18336fee8fc830af3e930180aaa3a3dce597fe3eb8b0d4561abb607e0a): updates RFC 7240
  for WebDAV and registers `depth-noroot`; no syntax change.
- RFC 9110, https://www.rfc-editor.org/rfc/rfc9110.txt (sha256
  21c1cdce6ab0e5509b04d84a28000836c7a087cf786efe6f04877ebfff47232a): 5.3 combining
  field lines, 5.5 field values (CR, LF, NUL), 5.6.1 lists (sender and recipient rules),
  5.6.2 tokens, 5.6.3 whitespace (a sender must not generate BWS), 5.6.4 quoted strings,
  5.6.6 parameters, 10.2.3 `delay-seconds = 1*DIGIT`, 12.5.5 Vary.
- IANA HTTP Preferences registry,
  https://www.iana.org/assignments/http-parameters/http-parameters.xml (registry
  `preferences`, file updated 2025-10-02): the registered names, used only as a fact list.

The RFC text is not committed: `tests/upstream/MANIFEST.json` records URL, size, sha256
and licence, `scripts/fetch_upstream.py` fetches it into the ignored `tests/upstream/`
folder, and the test that parses every `Prefer` and `Preference-Applied` example of the
RFC skips while it is absent.

Where the sources disagree or are silent:

- The original ABNF allows BWS around `=` and uses `word`, which RFC 7230 never defined.
  The verified erratum 4439 replaces it with the RFC 9110 `parameter` (no whitespace
  around `=`). The tolerant parser accepts BWS, as a recipient must; the strict parser
  rejects it, as a sender must not generate it.
- `return=minimal, return=representation`: section 4.2 says such a request can be treated
  as if neither was sent, while section 2 says the first instance is the one considered.
  The library applies the first-wins rule (it is the general one and needs no knowledge
  of each preference) and documents the alternative.
- Repeated parameters inside one preference: no rule. The first one wins, as for
  preferences.
- Malformed input: the RFC only says unknown preferences are ignored without error. The
  tolerant parser drops a malformed list member, or a malformed parameter of a valid
  preference, and keeps the rest.
- Very long `wait` values: `delay-seconds` has no upper bound. Values longer than 100
  digits (after leading zeros) are reported as no wait preference rather than spending
  quadratic time on the conversion; an absent `wait` and a huge one mean the same thing.

## Ranked improvements

1. **Correct tolerant parser.** A real quoted-string scanner (quoted-pair, obs-text),
   tokens per RFC 9110, OWS limited to SP and HTAB, BWS accepted around `=`, empty values
   mapped to `None`, CR, LF and NUL replaced by SP before parsing (the option RFC 9110
   5.5 allows), first preference and first parameter win, malformed members dropped, and
   any iterable of field values accepted and joined with a comma.
2. **Strict parser.** `parse(value, strict=True)` follows the sender grammar (errata 4439
   and RFC 9110 5.6.1.1): no empty list elements, no BWS, valid quoted strings, no
   repeated preference, and raises `PreferError` with the field index and position.
3. **Validated model and safe builder.** `Preference` checks its name and parameter names
   are tokens and its values fit in a quoted string, lower-cases names, maps `""` to
   `None`, and stores parameters in an immutable, hashable mapping, so a bad value fails
   where it is created, not when the header is sent. `build` emits tokens bare, quotes and
   escapes the rest, refuses anything that could split a header, and with `applied=True`
   refuses parameters (section 3).
4. **Typed accessors.** `parse` returns `Preferences`, an immutable sequence with
   case-insensitive `get` and `in`, plus `respond_async`, `return_`, `wait` and
   `handling` typed with `Literal` values, and `applied(...)` to build the
   `Preference-Applied` list from the names a server honoured.
5. **Vary helper.** `vary(current)` adds `Prefer` to an existing `Vary` value once,
   leaves `*` alone, and checks the field names it keeps.
6. **Command line checker.** `preferhdr 'respond-async, wait=10'` (or header lines on
   stdin) prints the preferences and exits non-zero when the value breaks the grammar.
7. **Contracts.** RFC examples from the fetched text, cited vectors, a seeded round trip
   (`parse(build(p), strict=True) == p`), README examples executed, typing checked with
   mypy, installed-wheel end-to-end test, mutation run.
8. **Packaging.** Keywords, classifiers, console script, sdist without fetched files.

Deferred: per-preference value validation for registered extensions such as the OData
ones (each has its own grammar and they change over time).

## Results

- Every one of the 17 `Prefer` and `Preference-Applied` example lines in the fetched RFC
  text parses in strict mode and round trips through `build`.
- Gates: `ruff format --check .`, `ruff check .`, `mypy --strict src tests` and `pytest`
  (with the installed-wheel end-to-end test, `PREFERHDR_E2E=1`) all pass.
- Mutation run: 51 hand-written mutants across every module (grammar, model, scanner,
  parser, accessors, builder, Vary helper, command line, error pickling). Four survived
  the first run: a constant `Params` hash, `Preference.__eq__` answering `False` instead
  of deferring to the other operand, escaped quotes ignored and `;` taken as a member
  boundary while skipping a malformed member. Each now has a test that kills it.
- Independent review: no high-severity finding. Fixed, each with a regression test in
  `tests/test_review_regressions.py`: the command line printed its error before the
  preferences (and the README test compared the streams merged); a README example did
  not pass `mypy --strict`; the CHANGELOG claimed any `build` output passes strict
  parsing (an empty one does not); stdin lost folded header lines (now joined with SP,
  RFC 9112 section 5.2) and read past the end of the header section; bytes gave a
  misleading `TypeError`; names folded case beyond ASCII (Kelvin sign matched `k`); a
  stray DQUOTE inside a malformed token swallowed the members after it; values could
  carry U+0085, a line break to `str.splitlines` (C1 controls are now refused, a
  documented deviation); an empty strict value reported its end as the position;
  `Params` did not compare equal to a mapping spelled in another case. Documented
  instead of changed: repeated parameters in strict mode, and the `handling` duplicate
  case next to `return`.
- Final mutation run after the review: 62 mutants (the first set updated to the changed
  code plus mutants on every review fix), run with bytecode writing off so a restored
  file can never be shadowed by a stale cache; all 62 make the suite fail.
- The installed-wheel end-to-end test passes (248 tests with `PREFERHDR_E2E=1`).
