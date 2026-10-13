"""Regression tests for the findings of the independent review."""

from __future__ import annotations

import io
import os
import subprocess
import sys
from pathlib import Path

import pytest

from preferhdr import Preference, Preferences, PreferError, build, parse, vary
from preferhdr._cli import main

SRC = Path(__file__).resolve().parents[1] / "src"


def _stdin(monkeypatch: pytest.MonkeyPatch, data: bytes) -> None:
    monkeypatch.setattr(sys, "stdin", io.TextIOWrapper(io.BytesIO(data)))


def test_cli_prints_the_preferences_before_the_error() -> None:
    # One pipe for both streams shows the order a terminal shows.
    env = {**os.environ, "PYTHONPATH": str(SRC)}
    run = subprocess.run(
        [sys.executable, "-m", "preferhdr", "wait = 10"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        env=env,
        check=False,
    )
    assert run.returncode == 1
    assert run.stdout.splitlines() == [
        "wait=10",
        "invalid: whitespace before '=' at position 4 of field 0",
    ]


def test_cli_joins_folded_header_lines_with_a_space(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _stdin(monkeypatch, b"Prefer: a,\r\n b;\r\n\tc=1\r\nHost: x\r\n")
    assert main([]) == 0
    assert capsys.readouterr().out.splitlines() == ["a", "b; c=1"]


def test_cli_stops_at_the_end_of_the_header_section(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _stdin(monkeypatch, b"POST / HTTP/1.1\r\nPrefer: a\r\n\r\nPrefer: b\r\n")
    assert main([]) == 0
    assert capsys.readouterr().out == "a\n"


@pytest.mark.parametrize("value", [b"a", bytearray(b"a")])
def test_bytes_are_refused_with_a_clear_message(value: bytes) -> None:
    with pytest.raises(TypeError, match="not bytes"):
        parse(value)  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="not bytes"):
        vary(value)  # type: ignore[arg-type]


def test_names_fold_case_in_ascii_only() -> None:
    prefs = parse("k; s=1")
    kelvin, long_s = chr(0x212A), chr(0x017F)
    assert prefs.get(kelvin) is None
    assert kelvin not in prefs
    assert long_s not in prefs[0].params
    with pytest.raises(KeyError):
        prefs[0].params[long_s]
    assert prefs.applied(kelvin) == ()


def test_params_compare_equal_to_a_mapping_in_any_case() -> None:
    params = Preference("a", None, {"b": "y"}).params
    assert params == {"B": "y"}
    assert params != {"B": "y", "b": "y"}
    assert params != {chr(0x212A): "y"}
    assert params != {"b": "z"}
    assert params != [("b", "y")]  # type: ignore[comparison-overlap]


@pytest.mark.parametrize(
    ("value", "kept"),
    [('a"b, c', "c"), ('a=b"c, d', "d"), ('x; p=v"w, e', "e"), ('f; q"r; s, g', "g")],
)
def test_a_stray_quote_inside_a_token_does_not_swallow_the_rest(value: str, kept: str) -> None:
    assert parse(value)[-1] == Preference(kept)


def test_a_stray_quote_inside_a_parameter_keeps_the_preference() -> None:
    assert parse('x=1; p=v"w; q=2, y') == (Preference("x", "1", {"q": "2"}), Preference("y"))


def test_a_quote_after_equals_still_protects_its_commas() -> None:
    assert parse('a b="x, y", c') == (Preference("c"),)
    assert parse('a b= "x, y", c') == (Preference("c"),)


@pytest.mark.parametrize("ch", ["\x80", "\x85", "\x9f"])
def test_c1_controls_are_refused_everywhere(ch: str) -> None:
    with pytest.raises(PreferError, match="cannot carry"):
        Preference("a", f"x{ch}Set-Cookie: y")
    assert parse(f'a="x{ch}y", b') == (Preference("b"),)
    with pytest.raises(PreferError, match="invalid character"):
        parse(f'a="x{ch}"', strict=True)


def test_no_built_value_contains_a_python_line_break() -> None:
    text = "".join(map(chr, range(0x20, 0x7F))) + "".join(map(chr, range(0xA0, 0x100)))
    assert len(build([Preference("a", text + "\t")]).splitlines()) == 1


def test_an_empty_strict_value_reports_where_the_element_starts() -> None:
    with pytest.raises(PreferError) as caught:
        parse("   ", strict=True)
    assert caught.value.position == 0
    with pytest.raises(PreferError) as caught:
        parse("a,  ", strict=True)
    assert caught.value.position == 2


def test_building_nothing_is_not_a_valid_field_value() -> None:
    assert build(Preferences()) == ""
    with pytest.raises(PreferError, match="empty list element"):
        parse(build([]), strict=True)


def test_an_escaped_quote_keeps_a_skipped_string_open() -> None:
    assert parse('a b="\\", y, z", c') == (Preference("c"),)
