"""Strict mode accepts exactly the grammar read from the fetched specification text.

The rules come from RFC 9110 (https://www.rfc-editor.org/rfc/rfc9110.txt) and verified
erratum 4439 of RFC 7240 (https://www.rfc-editor.org/errata/rfc7240), both fetched by
``python scripts/fetch_upstream.py`` (2026-10-19) and checked against the manifest; the
tests skip while they are absent. ``tests/abnf.py`` compiles the rules into regular
expressions; only the list expansion and the documented C1 exception are written here.
"""

from __future__ import annotations

import html
import random
import re

import pytest
from abnf import Compiler, read_rule
from conftest import read_upstream
from generators import TCHAR as TCHARS
from generators import any_value, grammar_value, mutate, noise

from preferhdr import PreferError, parse
from preferhdr._grammar import TCHAR, is_text_char

RFC9110_RULES = [
    *("token", "tchar", "OWS", "BWS", "quoted-string", "qdtext", "quoted-pair"),
    *("obs-text", "parameter", "parameter-name", "parameter-value"),
]


def _erratum_4439() -> dict[str, str]:
    page = html.unescape(re.sub(r"<[^>]+>", " ", read_upstream("rfc7240-errata.html")))
    text = " ".join(page.split())
    entry = text.split("Errata-ID: 4439", 1)[1].split("Errata-ID:", 1)[0]
    assert "Status: Verified" in entry
    fixed = entry.split("It should say:", 1)[1].split("Notes:", 1)[0].strip()
    assert fixed == (
        'preference = preference-parameter *( OWS ";" [ OWS preference-parameter ] ) '
        "preference-parameter = parameter / token"
    )
    first, second = fixed.split(" preference-parameter = ")
    return {"preference": first.split(" = ", 1)[1], "preference-parameter": second}


@pytest.fixture(scope="module")
def grammar() -> Compiler:
    text = read_upstream("rfc9110.txt")
    rules = {name: read_rule(text, name) for name in RFC9110_RULES}
    assert rules["obs-text"] == "%x80-FF"
    # Documented exception: values never hold the C1 controls U+0080 to U+009F.
    rules["obs-text"] = "%xA0-FF"
    return Compiler({**rules, **_erratum_4439()})


def _list(grammar: Compiler, member: str) -> re.Pattern[str]:
    text = read_upstream("rfc9110.txt")
    # RFC 9110 section 5.6.1: 1#element => element *( OWS "," OWS element ).
    assert '1#element => element *( OWS "," OWS element )' in " ".join(text.split())
    element, ows = grammar.regex(member), grammar.regex("OWS")
    return re.compile(f"{ows}{element}(?:{ows},{ows}{element})*{ows}")


@pytest.fixture(scope="module")
def field_regex(grammar: Compiler) -> re.Pattern[str]:
    return _list(grammar, "preference")


def _chars(regex: str) -> set[str]:
    return {chr(c) for c in range(0x300) if re.fullmatch(regex, chr(c))}


def test_tchar_is_the_rfc_9110_rule(grammar: Compiler) -> None:
    assert _chars(grammar.regex("tchar")) == set(TCHAR)


def test_quoted_text_is_the_rfc_9110_rule_without_c1_controls(grammar: Compiler) -> None:
    pair_chars = {
        ch[1]
        for ch in map("\\{}".format, map(chr, range(0x300)))
        if re.fullmatch(grammar.regex("quoted-pair"), ch)
    }
    plain = _chars(grammar.regex("qdtext"))
    assert pair_chars == plain | {'"', "\\"}
    assert pair_chars == {chr(c) for c in range(0x300) if is_text_char(chr(c))}


def _strict_ok(value: str, applied: bool) -> bool:
    try:
        parse(value, strict=True, applied=applied)
    except PreferError:
        return False
    return True


def _check(values: list[str], field_regex: re.Pattern[str], applied: bool = False) -> int:
    accepted = 0
    for value in values:
        grammatical = field_regex.fullmatch(value) is not None
        if grammatical:
            names = _members(value)
            # Strict mode also refuses a repeated preference, which a sender SHOULD NOT send.
            grammatical = len(names) == len(set(names))
        assert _strict_ok(value, applied) == grammatical, repr(value)
        accepted += grammatical
    return accepted


def _members(value: str) -> list[str]:
    """The lower-cased name of each list member (only called on grammatical values)."""
    names, in_quotes, escaped, start = [], False, False, True
    for index, ch in enumerate(value):
        if escaped:
            escaped = False
        elif in_quotes:
            escaped = ch == "\\"
            in_quotes = ch != '"'
        elif ch == '"':
            in_quotes = True
        elif ch == ",":
            start = True
        elif start and ch in TCHARS:
            match = re.compile(f"[{re.escape(TCHARS)}]+").match(value, index)
            assert match is not None
            names.append(match.group(0).lower())
            start = False
    return names


@pytest.mark.parametrize("seed", [1, 2, 3])
def test_strict_mode_accepts_exactly_the_grammar(seed: int, field_regex: re.Pattern[str]) -> None:
    rng = random.Random(seed)
    values = [any_value(rng) for _ in range(6000)]
    values += [mutate(rng, grammar_value(rng, "aAbB-")) for _ in range(2000)]
    values += [grammar_value(rng, "aAbB") for _ in range(2000)]
    values += [noise(rng, 12) for _ in range(2000)]
    accepted = _check(values, field_regex)
    # Both sides of the boundary are exercised.
    assert 3000 < accepted < len(values) - 3000


def test_preference_applied_follows_erratum_4625(grammar: Compiler) -> None:
    # Reported erratum 4625: applied-pref = preference-parameter, so no parameters.
    applied = _list(grammar, "preference-parameter")
    rng = random.Random(4625)
    values = [grammar_value(rng, "aAbB", applied=True) for _ in range(1500)]
    values += [mutate(rng, grammar_value(rng, applied=rng.random() < 0.7)) for _ in range(4000)]
    accepted = _check(values, applied, applied=True)
    assert 1500 < accepted < len(values) - 1500
