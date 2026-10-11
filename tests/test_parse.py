from preferhdr import Preference, parse


def test_respond_async_is_a_bare_token() -> None:
    assert parse("respond-async") == [Preference("respond-async")]


def test_return_minimal_has_a_value() -> None:
    assert parse("return=minimal") == [Preference("return", "minimal")]


def test_return_representation_has_a_value() -> None:
    assert parse("return=representation") == [Preference("return", "representation")]


def test_wait_keeps_its_number_as_a_string() -> None:
    assert parse("wait=10") == [Preference("wait", "10")]


def test_handling_strict_has_a_value() -> None:
    assert parse("handling=strict") == [Preference("handling", "strict")]


def test_quoted_value_is_unquoted() -> None:
    assert parse('foo="bar baz"') == [Preference("foo", "bar baz")]


def test_quoted_value_keeps_escaped_characters() -> None:
    assert parse(r'foo="a\"b"') == [Preference("foo", 'a"b')]


def test_a_preference_carries_its_parameters() -> None:
    result = parse("foo=bar; baz=qux; lenient")
    assert result == [Preference("foo", "bar", {"baz": "qux", "lenient": None})]


def test_parameter_value_may_be_quoted_and_hold_a_comma() -> None:
    result = parse('foo=bar; note="a, b"')
    assert result == [Preference("foo", "bar", {"note": "a, b"})]


def test_multiple_comma_separated_preferences() -> None:
    result = parse("respond-async, wait=10, handling=lenient")
    assert result == [
        Preference("respond-async"),
        Preference("wait", "10"),
        Preference("handling", "lenient"),
    ]


def test_names_are_lower_cased() -> None:
    assert parse("Respond-Async") == [Preference("respond-async")]


def test_surrounding_whitespace_is_ignored() -> None:
    assert parse("  return = minimal  ") == [Preference("return", "minimal")]


def test_empty_entries_are_tolerated() -> None:
    assert parse("respond-async, , wait=10") == [
        Preference("respond-async"),
        Preference("wait", "10"),
    ]


def test_an_empty_header_yields_no_preferences() -> None:
    assert parse("") == []
    assert parse("   ") == []
