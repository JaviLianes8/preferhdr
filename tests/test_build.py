from preferhdr import Preference, build, parse


def test_build_a_bare_token() -> None:
    assert build([Preference("respond-async")]) == "respond-async"


def test_build_a_valued_preference() -> None:
    assert build([Preference("return", "minimal")]) == "return=minimal"


def test_build_quotes_a_value_that_is_not_a_token() -> None:
    assert build([Preference("foo", "bar baz")]) == 'foo="bar baz"'


def test_build_escapes_quotes_in_a_value() -> None:
    assert build([Preference("foo", 'a"b')]) == r'foo="a\"b"'


def test_build_emits_parameters() -> None:
    pref = Preference("foo", "bar", {"baz": "qux", "lenient": None})
    assert build([pref]) == "foo=bar; baz=qux; lenient"


def test_build_joins_multiple_preferences() -> None:
    prefs = [Preference("respond-async"), Preference("wait", "10")]
    assert build(prefs) == "respond-async, wait=10"


def test_build_of_nothing_is_empty() -> None:
    assert build([]) == ""


def test_round_trip_through_parse_and_build() -> None:
    header = 'respond-async, wait=10, return=minimal; note="a, b"'
    assert build(parse(header)) == header
