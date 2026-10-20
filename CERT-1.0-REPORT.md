# preferhdr 1.0.0 certification report

The 1.0.0 certification bar (19 items) applied to preferhdr. PyPI has 0.2.0 only, and its
wheel (sha256 `51b2f72d...519c29`, as listed by https://pypi.org/pypi/preferhdr/json) holds
modules byte for byte equal to `main` at 920592c, so every change listed here is a change
against the PyPI release.

Progress:
- [x] Branch `release/1.0.0` from `main` (920592c, same code as PyPI 0.2.0)
- [x] API review and 1.0.0 changes (item 1)
- [x] Errors, typing, docstrings and doctests (items 2 to 5)
- [x] Ground truth: specifications, errata and registry fetched live, reference parsers (item 7)
- [x] Contract, fuzz and hostile input tests (items 6, 9)
- [x] Docs: README, GUIDE, CHANGELOG (items 11, 12)
- [x] Packaging, e2e and upgrade from PyPI 0.2.0, every Python (items 8, 10, 13, 14)
- [x] Gates (item 15)
- [x] Author mutation round (item 18)
- [ ] Five QA lenses (item 19): round 1 to 9 findings fixed, re-verification pending
- [ ] Independent reviewer (item 16)
- [ ] Merge and publish (item 17), left to the maintainer

## Scorecard

| # | Item | Result |
| --- | --- | --- |
| 1 | Public API reviewed for stability | PASS: six names, signatures and defaults kept from 0.2.0 and pinned in `tests/test_contract_api.py`; every behaviour change in CHANGELOG and GUIDE |
| 2 | `__all__` exact, no private imports in docs | PASS |
| 3 | Docstrings with runnable examples, doctests | PASS: 13 doctests; README (10 outputs, 2 command runs) and GUIDE (3 blocks) run as tests |
| 4 | Typed end to end | PASS: `mypy --strict src tests`, `py.typed`, revealed types checked from a consumer snippet |
| 5 | Typed, documented, bounded errors | PASS: `PreferError` (a `ValueError`) with `message`, `position`, `field`; `TypeError` for wrong types; messages quote at most 40 characters |
| 6 | Contract tests of every public name | PASS |
| 7 | Real ground truth | PASS: five fetched sources with a hash manifest, a grammar oracle compiled from their ABNF, the standard library, parse-prefer-header 1.0.0 run with Node.js, PyPI 0.2.0 |
| 8 | Real e2e from the wheel | PASS: wheel installed in a fresh venv over PyPI 0.2.0 (upgrade in place), driven from an empty folder, CLI by subprocess |
| 9 | Seeded fuzz, no crash, hang or blowup | PASS |
| 10 | Supported Pythons | PASS: CPython 3.10.19, 3.11.14, 3.12.12, 3.13.11, 3.14.2, 3.14.2 free-threaded, last run at c418230 |
| 11 | README and `twine check` | PASS: `twine check --strict` on wheel and sdist |
| 12 | Dated CHANGELOG section | PASS: 1.0.0, 2026-10-19 |
| 13 | pyproject 1.0.0, Production/Stable | PASS |
| 14 | sdist and wheel contents | PASS |
| 15 | Gates each exit 0 | PASS: see Gates |
| 16 | Independent reviewer | pending |
| 17 | PR and trace guard | PR #3 from `release/1.0.0`, trace guard CLEAN; merge and publish left to the maintainer |
| 18 | Contracts bite (mutations) | PASS: author 36 mutants, 34 killed, 1 equivalent, 1 survivor killed by a new contract |
| 19 | Five independent QA lenses | pending |

## API review (item 1)

Kept: `parse`, `build`, `vary`, `Preference`, `Preferences` and `PreferError` with the
signatures, parameter names, keyword-only flags and defaults of 0.2.0, now pinned by
`tests/test_contract_api.py`. Changed, all in the CHANGELOG and the GUIDE: `parse(None)`
gives empty `Preferences` (a request without the header needs no special case);
`Preferences.get` and `Preferences.applied` raise `TypeError` for a name that is not a
`str` (0.2.0 answered `None` or skipped it silently); `TypeError` messages name the type;
every message quotes at most 40 characters of the input; the public classes report
`preferhdr` as their module and a pickled `Preference` stores its parameters as a plain
`dict`, so no pickle names a private module (pickles written by 0.2.0 still load, checked
against the real 0.2.0); the command exits 1 without a traceback when its output pipe
closes and cuts argparse's echo of a huge unknown argument; `python -m preferhdr` no longer
runs the command on import.

Defects found in 0.2.0 and fixed: `get(1)` returned `None` and `applied(1)` dropped the
name silently; error messages quoted the whole input (a 1 MB name gave a 1 MB message);
a closed output pipe ended the command with a traceback; importing `preferhdr.__main__`
ran the command; pickles referenced `preferhdr._model`.

## Ground truth (item 7)

Fetched on 2026-10-19 by `scripts/fetch_upstream.py` into the ignored `tests/upstream`
folder and fetched again on another machine in the gate run (same sha256);
`tests/upstream/MANIFEST.json` records URL, size, sha256, date and licence, and the tests
check the hash before reading. Nothing fetched is committed or shipped.

- RFC 9110 (https://www.rfc-editor.org/rfc/rfc9110.txt) and verified erratum 4439 of RFC
  7240 (https://www.rfc-editor.org/errata/rfc7240), `tests/test_spec_grammar.py`: the
  `token`, `tchar`, `OWS`, `quoted-string`, `qdtext`, `quoted-pair`, `obs-text` and
  `parameter` rules and the corrected `preference` rule are read from the texts and
  compiled by `tests/abnf.py` into regular expressions (the RFC 5234 core rules and the
  `1#element` expansion, itself checked against the RFC text, are the only parts written
  by hand). Strict mode accepts exactly that grammar (minus the documented C1 exception,
  plus the repeated-preference check) on 36,000 generated values in three seeds and on
  5,500 `Preference-Applied` values (reported erratum 4625); `tchar` and the quoted-string
  character sets match code point by code point up to U+02FF.
- RFC 7240 (https://www.rfc-editor.org/rfc/rfc7240.txt): its 17 example headers parse
  strictly and round trip; the `return`, `handling` and `wait` rules of section 4 are read
  from the text and checked against the typed properties; `delay-seconds` is read from RFC
  9110 (verified erratum 4316).
- RFC 8144 (https://www.rfc-editor.org/rfc/rfc8144.txt): every example header parses
  strictly and builds back to the same text.
- IANA HTTP Preferences registry
  (https://www.iana.org/assignments/http-parameters/preferences.csv, 13 entries): every
  registered name reads, builds and round trips in both modes; the values the registry
  lists for `return` and `handling` equal the `Literal` types of the properties.
- Errata page: the statuses of all six errata are read and asserted (4439 and 4316
  verified, 4625, 4955 and 5282 reported, 4317 rejected), and the examples of 4955 and
  4317 are cut from the page and checked.
- Independent parsers (`tests/test_oracles.py`): Python's `urllib.request.parse_http_list`
  with `email.message.Message.get_params` agree on 12,000 valid values (three seeds),
  given RFC 7240's rules for empty segments, name case and first-wins; their misreading of
  an escaped DQUOTE is asserted precisely. parse-prefer-header 1.0.0
  (https://www.npmjs.com/package/parse-prefer-header, run with Node.js) agrees on 15,000
  values within the shapes it can represent; its three differences are asserted.
- PyPI 0.2.0 as an oracle (`tests/test_upgrade.py`, `PREFERHDR_V02`): 88,000 parse, property, `get`, `applied` and `build` calls
  and 40,000 `Preference` and `vary` calls give the same results, error families, positions
  and short messages; the documented changes are checked case by case, and pickles
  written by the real 0.2.0 load.

## Fuzz and hostile input (item 9)

`tests/test_fuzz.py`: three seeds of 8,000 inputs (grammar values, mutated values,
noise, random Unicode) per property: the tolerant parser never raises and its output
builds into a strictly valid value that reads back the same; strict mode raises only
`PreferError` with a position inside the field and a short message, and agrees with the
tolerant parser whenever it accepts; any name and value either build safely or raise a
bounded `PreferError`; `vary` lists `Prefer` once and is idempotent.
`tests/test_hostile.py`: thirteen input shapes timed at 50,000 and 200,000 characters
through both parsers, both header kinds, `wait` and `build` (linear: under 9 times for 4
times the input); 1 MB in every error path gives a message under 600 characters; types with
100,000-character names are cut; 100,000 preferences build and read back.

## Packaging, e2e and Pythons (items 8, 10, 13, 14)

At 97aa23f on the laptop (fresh `git archive` of the pushed head), CPython 3.14.2, with the
fetched sources, the Node.js reference, the 0.2.0 oracle, `PREFERHDR_E2E=1` and
`PREFERHDR_E2E_PYPI=1`: 344 passed, 0 skipped (the same run at 462c9dd on Elena's PC: 340
passed). The e2e test builds the wheel and sdist,
inspects both (`py.typed`, `__main__`, entry point, LICENSE in the wheel; GUIDE,
CHANGELOG, LICENSE, the manifest and the scripts in the sdist; no fetched files, no
`node_modules`, no certification notes; Production/Stable classifier; no runtime
requirement), installs `preferhdr==0.2.0` from PyPI into a fresh venv, then upgrades it
in place with the built wheel, and drives the installed package from an empty folder with
`-I` and the `preferhdr` command by subprocess. `twine check --strict` passes on both files.

Every interpreter available here from `requires-python` up, the built wheel installed in a
fresh venv and the sdist's own suite run with `src` removed (fetched sources, Node.js
reference and 0.2.0 oracle present): CPython 3.10.19, 3.11.14, 3.12.12, 3.13.11, 3.14.2 and
3.14.2 free-threaded, 330 passed and 1 skipped each (at 97aa23f) (the e2e test, which needs the source
tree and ran above). 3.8 and 3.9 are installed but below `requires-python`.

## Gates (item 15)

At 97aa23f on the laptop, each command on its own: `ruff format --check .`, `ruff check .`,
`mypy --strict src`, `mypy --strict src tests` and `pytest` (344 passed) exit 0.

At c418230 (code as in 6ca8123, the round 3 fix) on the laptop, from a fresh `git archive`
with the fetched sources (hashes checked), the Node.js reference and the 0.2.0 oracle:
`ruff format --check .`, `ruff check .`, `mypy --strict src`, `mypy --strict src tests` exit
0; `pytest` with `PREFERHDR_E2E=1`, `PREFERHDR_E2E_PYPI=1` and `PREFERHDR_V02` gives 392
passed, 0 skipped (wheel and sdist built and inspected, upgrade in place from PyPI 0.2.0,
command by subprocess); `twine check --strict` passes on both files. The built wheel in a
fresh venv per interpreter with the sdist's suite (`src` removed): CPython 3.10.19 377
passed and 2 skipped (the e2e test and the `StrEnum` case, which needs 3.11), 3.11.14,
3.12.12, 3.13.11, 3.14.2 and 3.14.2 free-threaded 378 passed and 1 skipped each (the e2e
test).

## Author mutation round (item 18)

36 mutants over every module, each applied alone to a fresh copy of the pushed head (9bd482e)
on Elena's PC, the full suite (fetched sources, Node.js reference, 0.2.0 oracle) run with `-x`
and a 300 s per-test limit. 34 killed at once; M08 is equivalent; M36 survived and is now
killed by a new contract (checked by re-running the mutant).

| Mutant | Change | Result |
| --- | --- | --- |
| M01 | tchar admits '/' | killed: `tests/test_spec_grammar.py::test_tchar_is_the_rfc_9110_rule` |
| M02 | C1 controls admitted as text | killed: `tests/test_review_regressions.py::test_c1_controls_are_refused_everywhere[\x80]` |
| M03 | off by one in the message cut | killed: `tests/test_contract_api.py::test_messages_quote_at_most_forty_characters` |
| M04 | empty value kept as an empty string | killed: `src/preferhdr/__init__.py::preferhdr.Preference` |
| M05 | names not lower-cased | killed: `src/preferhdr/__init__.py::preferhdr.Preference` |
| M06 | whitespace before = check inverted | killed: `src/preferhdr/_parse.py::preferhdr._parse.parse` |
| M07 | whitespace after = accepted in strict mode | killed: `tests/test_spec_grammar.py::test_strict_mode_accepts_exactly_the_grammar[1]` |
| M08 | trailing backslash handling | survived, equivalent: both paths raise the same error at the opening quote |
| M09 | Preference-Applied parameters accepted in strict mode | killed: `src/preferhdr/_parse.py::preferhdr._parse.parse` |
| M10 | applied keeps parameters | killed: `src/preferhdr/_parse.py::preferhdr._parse.parse` |
| M11 | NUL not read as space | killed: `tests/test_parse.py::test_cr_lf_and_nul_read_as_spaces` |
| M12 | trailing empty element accepted | killed: `tests/test_review_regressions.py::test_an_empty_strict_value_reports_where_the_element_starts` |
| M13 | quote closing allows reopening in skip | killed: `tests/test_upgrade.py::test_parse_answers_as_0_2_0[1]` |
| M14 | escape ignored when skipping | killed: `tests/test_review_regressions.py::test_an_escaped_quote_keeps_a_skipped_string_open` |
| M15 | last repeated parameter wins | killed: `tests/test_docs.py::test_every_guide_example_runs_and_prints_its_comments` |
| M16 | repeated preference accepted in strict mode | killed: `tests/test_cli.py::test_several_values_are_one_list` |
| M17 | wrong field index | killed: `src/preferhdr/__init__.py::preferhdr.PreferError` |
| M18 | str iterated per char | killed: `src/preferhdr/__init__.py::preferhdr.Preferences.applied` |
| M19 | respond-async with a value counts | killed: `src/preferhdr/__init__.py::preferhdr.Preferences.respond_async` |
| M20 | return value case-folded | killed: `src/preferhdr/__init__.py::preferhdr.Preferences.return_` |
| M21 | wait digit limit off by one | killed: `tests/test_prefs.py::test_wait_reads_delay_seconds[wait=<100 nines>]` |
| M22 | applied keeps parameters | killed: `src/preferhdr/__init__.py::preferhdr.Preferences.applied` |
| M23 | handling lenient lost | killed: `src/preferhdr/__init__.py::preferhdr.Preferences.handling` |
| M24 | repeated preference not detected | killed: `tests/test_build.py::test_a_repeated_preference_is_rejected` |
| M25 | applied parameter check inverted | killed: `src/preferhdr/_build.py::preferhdr._build.build` |
| M26 | separator changed | killed: `src/preferhdr/__init__.py::preferhdr.Preferences.applied` |
| M27 | backslash not escaped when quoting | killed: `tests/test_build.py::test_build_escapes_quotes_and_backslashes` |
| M28 | wildcard only seen first | killed: `tests/test_vary.py::test_a_wildcard_already_covers_prefer` |
| M29 | prefer match case-sensitive | killed: `src/preferhdr/_vary.py::preferhdr._vary.vary` |
| M30 | repeated parameter accepted by Preference | killed: `tests/test_model.py::test_a_parameter_named_twice_is_rejected` |
| M31 | pickle names the private mapping | killed: `tests/test_contract_api.py::test_public_classes_live_in_the_package_and_pickle_there` |
| M32 | pickle drops the field | killed: `tests/test_contract_api.py::test_public_classes_live_in_the_package_and_pickle_there` |
| M33 | closed pipe reported as success | killed: `tests/test_contract_api.py::test_a_closed_output_pipe_exits_1_without_a_traceback` |
| M34 | header section does not end at the empty line | killed: `tests/test_review_regressions.py::test_cli_stops_at_the_end_of_the_header_section` |
| M35 | usage error not cut | killed: `tests/test_contract_api.py::test_a_huge_unknown_argument_is_cut_in_the_usage_error` |
| M36 | bytes name passes the type check | survived; contract added (`tests/test_contract_api.py::test_bytes_names_and_values_are_type_errors`), now killed |

## QA lenses (item 19)

### Round 1 (on 98ff9b8)

Lenses a (API and docs), c (adversarial), d (packaging) and e (contract strength, its
own 84 mutants: 77 killed, 3 proven equivalent, 4 survivors) reported these findings.
Every one is fixed in 03aef1a; none is disputed. Each behaviour finding got a test in
`tests/test_qa_regressions.py` that failed on 98ff9b8 (or, for the mutation findings,
that fails on the reported mutant, checked by applying each mutant) before the fix.

| Finding | Lens | Fix |
| --- | --- | --- |
| A1: README said an unterminated quote drops its member even inside a parameter value | a | README reworded (member, or only the parameter); GUIDE table row added; both cases pinned by `test_an_unterminated_quote_drops_what_it_belongs_to_and_the_rest` |
| A2: GUIDE upgrade list missed the argparse cut and the `__main__` import change | a | both added to the list |
| D1: sdist exclude listed `.gitignore`, which hatchling ships anyway | d | the line is removed from `pyproject.toml` |
| D2: `scripts/fetch_upstream.py` sent readers to the README for the npm install | d | it points to CONTRIBUTING.md, which has the command |
| F1 (c): the command joined folded lines in quadratic time | c | pieces are collected and joined once; `test_folded_header_lines_are_joined_in_linear_time` (ratio 18.7 before, linear after) |
| F2 (c): a `str` Enum was written as `Ret.MINIMAL` | c | every accepted `str` is turned into a plain `str` (`_grammar.exact`) before it is checked or stored; `test_str_enums_are_written_as_their_values` (mixin and `StrEnum`) |
| F3 (c): a `str` subclass overriding `__iter__`, `lower`, `split` or `strip` passed the checks and split a built header | c | same fix, applied to names, values, parameters, `parse` fields, `vary` values and lookups; `test_a_str_subclass_is_checked_by_its_real_characters` and three more tests with a subclass overriding every method used |
| F1-M4 (e): equality ignoring parameters survived | e | `test_preferences_differing_only_in_parameters_are_unequal` |
| F2-M6 (e): order-dependent parameter hash survived | e | `test_parameter_order_changes_neither_equality_nor_hash` |
| F3-G3 (e): message cut at 41 characters survived | e | `test_messages_cut_exactly_after_forty_characters` |
| F4-S5 (e): stray-quote reopening caught only by the opt-in 0.2.0 oracle | e | `test_a_quote_after_a_closed_string_does_not_open_another` in the default suite |

The two `str` subclass changes and the linear folding are listed under Fixed in the
CHANGELOG and in the GUIDE upgrade notes (0.2.0 behaved the same way).

Gates at 03aef1a on Elena's PC (fresh `git archive`, CPython 3.14.2, fetched sources and
the Node.js reference present): `ruff format --check .`, `ruff check .`,
`mypy --strict src`, `mypy --strict src tests` and `pytest` each exit 0 (358 passed, 7
opt-in skips); with `PREFERHDR_E2E=1`, `PREFERHDR_E2E_PYPI=1` and `PREFERHDR_V02` (0.2.0
from PyPI): 365 passed, 0 skipped.

### Round 2 (on d94fe1b)

Lens a confirmed A1 and A2 fixed, lens c confirmed F1 to F3 fixed, and lens e confirmed
its four round 1 survivors killed. Their new findings are all fixed in d5480f8, which
adds `tests/test_qa_regressions_r2.py`; none is disputed. Every new test failed on
d94fe1b (the F4 tests) or fails on the reported mutant (checked by applying each of A2,
A4, L1, L4 and L5 in turn), and passes on the fix.

| Finding | Lens | Fix |
| --- | --- | --- |
| A3: the CHANGELOG and GUIDE said 0.2.0 wrote a `str` Enum as `Ret.MINIMAL` on every Python | a | both now say "on Python 3.11 and later": 0.2.0 from PyPI gives `return=minimal` on 3.10.19 and `return=Ret.MINIMAL` on 3.11.14, 3.12.12 and 3.13.11 (run in this round; the change came with 3.11, not 3.12 as the finding guessed) |
| F4 (c): a subclass of the private parameter mapping, or of `Preference` overriding `__str__`, got CR LF into `build` (or an undocumented `KeyError`) | c | `Preference` rebuilds any parameters whose type is not exactly the private class, reading what a subclass stores unless it overrides `items()`; `build` re-creates a `Preference` subclass from its fields (checked again) and writes it with the library's own code. Tests: `test_a_params_subclass_*`, `test_build_writes_a_preference_subclass_by_its_checked_fields`, `test_build_checks_a_preference_subclass_that_skips_its_checks`, `test_build_applies_its_rules_to_a_preference_subclass`; listed under Fixed in the CHANGELOG and in the GUIDE upgrade notes |
| N1-A4 (e): no test of non-`str` parameter keys | e | `test_a_key_that_is_not_a_str_is_absent_from_the_parameters` |
| N2-L5 (e): no folded line after another header | e | `test_a_folded_line_belongs_to_the_field_just_above_it`, `test_a_folded_prefer_line_after_another_header_reads_whole` |
| N3-A2 (e): no non-ASCII lookup through a subclass lying about `isascii` | e | `test_a_lookup_does_not_trust_a_subclass_that_lies_about_isascii` (U+212A) |
| N4-L1 (e): no whitespace-only folded line | e | `test_a_blank_folded_line_adds_nothing`, `test_a_blank_folded_line_does_not_move_error_positions` |
| N5-L4 (e): no HTAB after the colon | e | `test_a_tab_after_the_colon_is_not_part_of_the_value` |

Gates on the round 2 fix, on Elena's PC (the working tree packed as committed, CPython
3.14.2, fetched sources and the Node.js reference present): `ruff format --check .`,
`ruff check .`, `mypy --strict src`, `mypy --strict src tests` and `pytest` each exit 0
(375 passed, 7 opt-in skips).

### Round 3 (on a0898f7)

Lens c confirmed F4 fixed (and F2, F3 still pass) on 3.11.5, 3.13 and 3.14.2; lens e
confirmed its five round 2 survivors killed and ran 27 new probes on the code changed in
round 2 (21 killed; of the 6 survivors Q2 is equivalent, the other five are below). Every finding is fixed in
6ca8123, which adds `tests/test_qa_regressions_r3.py`; none is disputed. The F5 and F6
tests failed on a0898f7; the mutation tests fail on the reported mutants (P8, P9, B10,
B11 and B4 applied one at a time to the fix: each is killed by the tests named below).

| Finding | Lens | Fix |
| --- | --- | --- |
| F5 (c): the raw-storage shortcut in the parameter mapping ignored the mapping a subclass shows, so a subclass that never filled the storage raised `AttributeError`, one overriding `__iter__` and `__getitem__` was written from hidden storage, and one with non-dict storage raised `AttributeError` | c | the storage is read directly only when it is a plain `dict` in the instance and the subclass overrides none of `items`, `__iter__` and `__getitem__`; otherwise the mapping is read through `items()`, and a `KeyError` or `AttributeError` raised while reading it becomes `TypeError` ("params could not be read as a mapping"). Tests: `test_a_params_subclass_that_never_fills_its_storage_is_read_as_a_mapping`, `test_a_params_subclass_is_written_from_what_it_shows`, `test_a_params_subclass_that_cannot_be_read_is_a_type_error`; listed under Fixed in the CHANGELOG and in the GUIDE upgrade notes |
| F6 (c): `str(preference)`, and so `build`, took quadratic time in the number of parameters | c | the parts are collected in a list and joined once; `test_a_preference_with_many_parameters_is_written_in_linear_time` (100k against 400k parameters, ratio 11.7 on a0898f7, bound 9); listed under Fixed in the CHANGELOG and in the GUIDE upgrade notes (0.2.0 had the same loop) |
| R3-P8 (e): skipping the value check on raw storage survived | e | `test_values_in_the_raw_storage_of_a_params_subclass_are_checked` (`Preference` and `build`) |
| R3-P9 (e): skipping the repeat check on raw storage survived | e | `test_repeated_names_in_the_raw_storage_of_a_params_subclass_are_rejected` |
| R3-B10 and B11 (e): moving the repeat check in `build` above the subclass rebuild, or adding a raw `str.lower` repeat check, survived | e | `test_build_rejects_a_repeat_whichever_spelling_comes_first` (both orders), `test_build_checks_a_preference_subclass_before_looking_for_repeats` (U+212A gives "is not a token") |
| R3-B4 (e): rebuilding with `dict(pref.params)` survived | e | `test_build_writes_the_params_subclass_of_a_preference_subclass` (raw storage and an `items()` override inside a check-skipping `Preference` subclass), plus the `TypeError` test above through `build` |

Gates on 6ca8123, on Elena's PC (`git archive` of the commit plus the fetched sources,
fresh venv, CPython 3.14.2): `ruff format --check .`, `ruff check .`, `mypy --strict src`,
`mypy --strict src tests` and `pytest --timeout=300` each exit 0 (385 passed, 7 opt-in
skips).

### Round 4 (on 5483f69)

Lenses a and e reported the findings below; every one is fixed in the commit that adds
`tests/test_qa_regressions_r4.py`, and none is disputed. The A1 and A2 tests failed on
5483f69 and pass on the fix; the M12 test passes on 5483f69 and fails on the reported
mutant (the `isinstance(other, Mapping)` guard deleted from the parameter mapping's
`__eq__`: five of its seven cases raise `TypeError`).

| Finding | Lens | Fix |
| --- | --- | --- |
| A1: a type name longer than 40 characters was cut without the length note the CHANGELOG promises | a | the type name is cut like names and values, with "(N characters)"; `test_a_long_type_name_is_cut_with_its_length`, `test_a_type_name_of_forty_characters_is_shown_whole` |
| A2: parameters given as a `dict` subclass were read through `dict.items()`, which skips the subclass's lookups, so a key its lookup rejects was accepted and the stored value replaced the value the lookup gives | a | a `dict` subclass that keeps a built-in `items()` is read through its own iteration and lookups (an overridden `items()` is still honoured; a plain `dict` reads as before), so the documented `TypeError` holds; `test_a_dict_subclass_whose_lookup_rejects_its_keys_is_a_type_error`, `test_a_dict_subclass_is_read_through_its_lookups` (`dict` and `OrderedDict` subclasses), `test_a_dict_subclass_is_read_through_its_iteration`, `test_a_dict_subclass_that_overrides_items_is_read_through_items`, `test_a_plain_dict_is_read_as_it_is`; the change against 0.2.0 is listed under Fixed in the CHANGELOG and in the GUIDE upgrade notes |
| F1-M12 (e): no contract pinned parameter equality against non-mappings | e | `test_parameters_never_equal_a_non_mapping` (`None`, `5`, `"x"`, `["x"]`, a list of pairs, `bytes`, `object()`; `==` and `!=` in both orders give `False` and `True`, never raise) |

Gates on 55c6ace, on this PC (CPython 3.13.2): `ruff format --check .`, `ruff check .`,
`mypy --strict src`, `mypy --strict src tests` and `pytest --timeout=300` each exit 0
(400 passed, 7 opt-in skips).

### Round 5 (on 652c7c6)

Lens e ran its own mutation sweep of 31 mutants on the parameter mapping's `__eq__`, the
type name in messages, `_pairs` and `_builtin`: 23 killed, 2 equivalent, 6 surviving. It
confirmed F1-M12 from round 4 fixed. Every survivor is fixed below by a contract in
`tests/test_qa_regressions_r5.py`; none is disputed and no behaviour changed, so the
CHANGELOG is unchanged. Each new test passes on 652c7c6, and each of the six mutants, applied
alone, fails exactly the test named for it.

| Finding | Lens | Fix |
| --- | --- | --- |
| F2-M12b: the parameter mapping returning `False` instead of `NotImplemented` for a non-mapping survived | e | `test_parameters_leave_a_non_mapping_comparison_to_the_other_side` (`mock.ANY` and an always-equal object: `==` is `True`, `!=` is `False`) |
| F3-T2: the cut boundary of a type name (41 characters) was not pinned | e | `test_a_type_name_of_forty_one_characters_is_cut` (exact message) |
| F4-T8: keeping the tail instead of the head of a long type name survived | e | `test_a_long_type_name_keeps_its_head` (40 `H` then 60 `T`, exact message) |
| F5-T6: naming a type by `__qualname__` survived | e | `test_a_nested_type_is_named_without_its_enclosing_class` |
| F6-T7: naming a type by `value.__class__` survived | e | `test_a_type_is_named_by_its_real_class_not_the_one_it_claims` (a `__class__` property that claims `int`) |
| F7-P18: weakening the raw-storage fast path of `_pairs` from `type(raw) is dict` to `isinstance` survived | e | `test_a_params_subclass_storing_a_dict_subclass_is_read_through_its_lookups` (a `Params` subclass whose storage is a `dict` subclass overriding `__getitem__`) |

The side note on `Preference(mock.Mock(spec=str))` is outside lens e and is left to lens c.

Gates on 4bf7452, on the laptop (fresh clone from GitHub, fresh venv, CPython 3.14.6):
`ruff format --check .`, `ruff check .`, `mypy --strict src`, `mypy --strict src tests` and
`pytest --timeout=300` each exit 0 (414 tests collected; the opt-in tests skip without the
fetched sources).

### Round 6 (on ca32c98)

Lens e confirmed the six round 5 findings fixed (each earlier mutant, applied alone, fails
its new test) and swept 10 new mutants on the type name in messages, the parameter mapping's
`__eq__`, `_pairs` and `_builtin`: 8 killed, 2 surviving. Both survivors are fixed below by
contracts; none is disputed and no behaviour changed, so the CHANGELOG is unchanged. Every
new or tightened test passes on ca32c98, and each of the two mutants, applied alone, fails
the tests named for it.

| Finding | Lens | Fix |
| --- | --- | --- |
| F8-N3: dropping the early `None in keys` rejection from the parameter mapping's `__eq__` survived (a mapping with a key no parameter can have was read, and its lookup errors escaped) | e | `test_parameters_differ_from_a_mapping_with_a_key_no_parameter_can_have` (keys `5`, `"é"` and `b"x"` in a mapping whose lookup always raises: `==` is `False`, `!=` is `True`, no value is read), `test_parameters_differ_from_a_mapping_with_keys_equal_after_folding` |
| F9-N10: naming the mapping's type instead of the error's in "params could not be read as a mapping (...)" survived | e | `test_unreadable_params_name_the_error_that_stopped_the_read` (a mapping whose lookup misses a key it lists: `KeyError`; a `dict` subclass whose `items()` raises: `AttributeError`; exact messages); the three tests in `tests/test_qa_regressions_r3.py` and `tests/test_qa_regressions_r4.py` that matched only the prefix now assert the exact message |

The tests are in `tests/test_qa_regressions_r6.py` and in the tightened r3 and r4 tests,
commit aa1f789.

Gates on aa1f789, on this PC (CPython 3.13.2): `ruff format --check .`, `ruff check .`,
`mypy --strict src`, `mypy --strict src tests` and `pytest --timeout=300` each exit 0
(420 tests collected: 414 passed, 6 opt-in skips without the fetched sources).

### Round 7 (on 0f24e81)

Lens e confirmed the two round 6 findings fixed (each earlier mutant, applied alone, fails
its new test) and swept 10 new mutants: 8 killed, 2 surviving. Both survivors are fixed
below by contracts; none is disputed and no behaviour changed. GUIDE and CHANGELOG now say
that an error other than `KeyError` or `AttributeError` raised inside a parameter mapping
propagates unchanged, as it did in 0.2.0. The new tests pass on 0f24e81, and each of the
two mutants, applied alone, fails the test named for it.

| Finding | Lens | Fix |
| --- | --- | --- |
| F10-Q3: folding the other mapping's keys with `str.lower` instead of the library's own folding in the parameter mapping's `__eq__` survived (a `str` subclass overriding `lower()` compared unequal) | e | `test_parameters_equal_a_mapping_keyed_by_a_str_subclass_with_the_same_text` (a key whose subclass overrides `lower()` and `__str__`: `==` is `True`, `!=` is `False`, and parameters built from that mapping are equal too) |
| F11-Q8: wrapping every `LookupError` (not just `KeyError`) from a parameter mapping in "params could not be read as a mapping" survived | e | `test_other_errors_from_a_params_mapping_propagate_unchanged` (`IndexError`, a bare `LookupError`, `ValueError` and `RuntimeError` from the mapping's lookup propagate as the same object and type) |

The tests are in `tests/test_qa_regressions_r7.py`, commit f51990d.

Gates on f51990d, on this PC (CPython 3.13.2): `ruff format --check .`, `ruff check .`,
`mypy --strict src`, `mypy --strict src tests` and `pytest --timeout=300` each exit 0
(425 tests collected: 419 passed, 6 opt-in skips without the fetched sources).

### Round 8 (on be15f63)

Lens e confirmed the two round 7 findings fixed (each earlier mutant, applied alone, fails
its new test) and swept 10 new mutants on the parameter mapping's `__eq__` and `_pairs`:
7 killed, 3 surviving. All three are fixed below; none is disputed. Two were real
disagreements between equality and construction, so equality changed and the CHANGELOG
says so: comparing parameters with a mapping now reads that mapping through the same
helper construction uses (`_entries`, one deferred lookup per listed key), so
`params == m` agrees with `Preference(..., m).params == params`. It still judges the keys
before reading any value, and now also answers `False` without reading values when the
number of keys differs. The new tests fail on be15f63 (except the pin of F14, which holds
there), and each of the three mutants, re-applied to the new code, fails them.

| Finding | Lens | Fix |
| --- | --- | --- |
| F12-R2: `__eq__` read a `dict` subclass through `items()` (its storage) while construction reads it through its own lookups, so `params == d` and `Preference(..., d).params == params` disagreed | e | equality reads the other mapping as construction does; `test_parameters_read_a_dict_subclass_the_way_construction_reads_it` (a `dict` subclass whose lookup disagrees with its storage: both comparisons are `False`) |
| F13-R4: `__eq__` checked the folded keys against `len(other)` while construction counts the keys the mapping lists, so a mapping whose `len()` disagrees with its iteration compared unequal to parameters built from it | e | equality counts the listed keys; `test_parameters_count_the_keys_a_mapping_lists_not_its_length` (iterates one key, `len()` says 2: both comparisons are `True`), `test_parameters_differ_from_a_mapping_with_another_number_of_keys` (no value is read) |
| F14-R6: chaining the inner error of "params could not be read as a mapping" survived | e | `test_an_unreadable_params_mapping_hides_the_inner_error` (exact message, `__cause__` is `None`, `__suppress_context__` is `True`) |

The tests are in `tests/test_qa_regressions_r8.py`, commit f8dedba.

Gates on f8dedba: on Elena's PC (CPython 3.14, a fresh clone from GitHub and a fresh venv)
`ruff format --check .`, `ruff check .`, `mypy --strict src`, `mypy --strict src tests` and
`pytest --timeout=300` each exit 0; on this PC (CPython 3.13.2) `pytest --timeout=300` gives
424 passed and 7 skips (the opt-in tests without the fetched sources).

### Round 9 (on 2f50827)

Lens e confirmed F12, F13 and F14 fixed (their mutants fail the round 8 tests) and swept
35 new mutants on the reworked parameter equality and `_entries`: 27 killed, 1 equivalent
(building the compared dict from the entries in reverse: once the fold check passes the
keys are distinct and dict equality ignores order), 7 surviving. All seven were missing
pins, not wrong behaviour, so no code changed; each is fixed by a test below and none is
disputed. For G2 the contract was decided as the current behaviour: an error raised while
reading the other mapping's values propagates unchanged, as the standard `Mapping`
equality lets it through (checked: `Mapping.__eq__` of two such mappings raises the inner
`KeyError`); the CHANGELOG now says so. Each of the seven mutants, applied alone to
2f50827, fails at least one new test; the new tests pass on 2f50827.

| Finding | Lens | Fix |
| --- | --- | --- |
| G1-S2-S5: the fold-duplicate check in parameter equality was unpinned (the only test compared against one parameter, so the count check answered first) | e | `test_two_keys_that_fold_together_differ_from_as_many_parameters` (two parameters against two keys that fold together, whose values raise if read) |
| G2-S8: what equality does when the other mapping's lookup fails was unpinned | e | contract: the error propagates unchanged, written in the CHANGELOG; `test_comparing_with_an_unreadable_mapping_lets_its_error_through` (`==` and `!=` raise `KeyError('inner')`) |
| G3-S21: a parameter mapping subclass whose storage is a `dict` subclass was unpinned | e | `test_storage_held_in_a_dict_subclass_is_read_through_the_lookups` (storage holds an upper-case key the lookup cannot find: `TypeError`) |
| G4-S24: a subclass overriding only `__iter__` was unpinned | e | `test_a_subclass_overriding_only_iteration_is_read_through_it` |
| G5-S25: a subclass overriding only `__getitem__` was unpinned | e | `test_a_subclass_overriding_only_lookup_is_read_through_it` |
| G6-S20: the storage branch taking its keys from the storage was unpinned | e | `test_inherited_storage_is_read_for_both_its_keys_and_its_values` (a class property shadows the instance storage) |
| G7-S35: the order of parameters read through an overridden `items()` was unpinned | e | `test_parameters_keep_the_order_of_an_overridden_items` (a mapping and a `dict` subclass whose `items()` order differs from their iteration or storage order) |

The tests are in `tests/test_qa_regressions_r9.py`, commit 5526a0c.

### Disputed findings

None in rounds 1 to 9.
