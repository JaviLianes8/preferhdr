"""The tolerant parser: what a server reads from any Prefer value, never raising."""

from __future__ import annotations

import pytest

from preferhdr import Preference, Preferences, parse


def test_respond_async_is_a_bare_token() -> None:
    assert parse("respond-async") == (Preference("respond-async"),)


def test_the_result_is_a_preferences_sequence() -> None:
    assert type(parse("a")) is Preferences


def test_a_valued_preference_keeps_its_value() -> None:
    assert parse("return=minimal") == (Preference("return", "minimal"),)


def test_quoted_value_is_unquoted_with_quoted_pairs_resolved() -> None:
    assert parse(r'foo="a\"b\\c"') == (Preference("foo", 'a"b\\c'),)


def test_a_preference_carries_its_parameters_in_order() -> None:
    (pref,) = parse("foo=bar; baz=qux; lenient")
    assert pref == Preference("foo", "bar", {"baz": "qux", "lenient": None})
    assert list(pref.params) == ["baz", "lenient"]


def test_quoted_values_may_hold_commas_and_semicolons() -> None:
    (pref,) = parse('foo="a, b; c"; note="x, y"')
    assert pref == Preference("foo", "a, b; c", {"note": "x, y"})


def test_names_are_lower_cased_and_values_are_not() -> None:
    assert parse("Return=Minimal; Foo=Bar") == (Preference("return", "Minimal", {"foo": "Bar"}),)


def test_several_field_values_are_one_list() -> None:
    assert parse(["respond-async, wait=100", "handling=lenient"]) == parse(
        "respond-async, wait=100, handling=lenient"
    )


def test_any_iterable_of_field_values_is_accepted() -> None:
    assert parse(iter(["a", "b"])) == (Preference("a"), Preference("b"))


def test_an_empty_value_is_no_value() -> None:
    assert parse('foo=""; bar=""') == parse("foo; bar") == parse("foo=; bar=")


def test_the_first_of_a_repeated_preference_wins() -> None:
    assert parse("return=minimal, Return=representation") == (Preference("return", "minimal"),)


def test_the_first_wins_across_field_values() -> None:
    assert parse(["wait=5", "wait=9"]) == (Preference("wait", "5"),)


def test_the_first_of_a_repeated_parameter_wins() -> None:
    (pref,) = parse("foo; a=1; A=2")
    assert dict(pref.params) == {"a": "1"}


def test_bad_whitespace_around_equals_is_accepted() -> None:
    assert parse("wait \t= 10 ; a = 1") == (Preference("wait", "10", {"a": "1"}),)


def test_only_space_and_tab_count_as_whitespace() -> None:
    assert parse("\x0bwait=1, \xa0a, \N{EM SPACE}c, b") == (Preference("b"),)


def test_empty_list_elements_and_parameters_are_ignored() -> None:
    assert parse(" , a;; ;b , ,") == (Preference("a", None, {"b": None}),)


@pytest.mark.parametrize("value", ["", "   ", ",", " , ,\t"])
def test_a_value_without_members_gives_nothing(value: str) -> None:
    assert parse(value) == ()


def test_no_field_values_give_nothing() -> None:
    assert parse([]) == ()


@pytest.mark.parametrize(
    "member",
    ["a b", "fo@o", "=1", "a=b c", 'a="x"y', "a=@", '"q"', "a=\x01", "[x]"],
)
def test_a_malformed_member_is_skipped_and_the_rest_kept(member: str) -> None:
    assert parse(f"first, {member}, last") == (Preference("first"), Preference("last"))


@pytest.mark.parametrize("param", ["x y", "x=@", 'x="a"b', "@", "x=a b", 'x="\x7f"'])
def test_a_malformed_parameter_is_skipped_and_the_preference_kept(param: str) -> None:
    assert parse(f"keep=1; a=1; {param}; b=2, next") == (
        Preference("keep", "1", {"a": "1", "b": "2"}),
        Preference("next"),
    )


def test_a_quoted_comma_inside_a_skipped_member_does_not_split_it() -> None:
    assert parse('a b="x, y", c') == (Preference("c"),)


def test_an_unterminated_quote_swallows_the_rest_of_its_field_only() -> None:
    assert parse(['a="open, b', "c"]) == (Preference("c"),)


def test_cr_lf_and_nul_read_as_spaces() -> None:
    assert parse('a=1\r\n, b;\0c, d="x\ny"') == (
        Preference("a", "1"),
        Preference("b", None, {"c": None}),
        Preference("d", "x y"),
    )


def test_a_header_injection_attempt_cannot_add_a_field() -> None:
    prefs = parse("return=minimal\r\nSet-Cookie: a=1")
    assert prefs == ()


def test_obs_text_is_kept_opaque_in_quoted_strings() -> None:
    assert parse('a="caf\xe9"') == (Preference("a", "caf\xe9"),)


def test_characters_above_latin1_are_malformed() -> None:
    assert parse('a="€", b') == (Preference("b"),)


def test_a_quoted_pair_may_escape_any_text_character() -> None:
    assert parse(r'a="\a\ \	"') == (Preference("a", "a \t"),)


def test_a_quoted_pair_cannot_escape_a_control() -> None:
    assert parse('a="\\\x01", b') == (Preference("b"),)


def test_a_backslash_ending_the_field_is_unterminated() -> None:
    assert parse('b, a="x\\') == (Preference("b"),)


def test_a_field_value_that_is_not_a_string_is_a_type_error() -> None:
    with pytest.raises(TypeError):
        parse([b"a"])  # type: ignore[list-item]
