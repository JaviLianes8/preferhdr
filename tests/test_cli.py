"""The command line checker prints preferences and exits non-zero on grammar errors."""

from __future__ import annotations

import io
import json
import sys

import pytest

from preferhdr._cli import main


def _stdin(monkeypatch: pytest.MonkeyPatch, data: bytes) -> None:
    monkeypatch.setattr(sys, "stdin", io.TextIOWrapper(io.BytesIO(data)))


def test_a_valid_value_prints_one_preference_per_line(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(['respond-async, Wait=10, return=minimal; foo="a b"']) == 0
    out, err = capsys.readouterr()
    assert out.splitlines() == ["respond-async", "wait=10", 'return=minimal; foo="a b"']
    assert err == ""


def test_an_invalid_value_exits_1_and_still_prints(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["a, b =1, c"]) == 1
    out, err = capsys.readouterr()
    assert out.splitlines() == ["a", "b=1", "c"]
    assert err == "invalid: whitespace before '=' at position 4 of field 0\n"


def test_several_values_are_one_list(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["wait=1", "wait=2"]) == 1
    out, err = capsys.readouterr()
    assert out == "wait=1\n"
    assert "repeated preference 'wait' at position 0 of field 1" in err


def test_json_output(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["--json", "return=minimal; x, respond-async"]) == 0
    rows = json.loads(capsys.readouterr().out)
    assert rows == [
        {"token": "return", "value": "minimal", "params": {"x": None}},
        {"token": "respond-async", "value": None, "params": {}},
    ]


def test_applied_rejects_parameters(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["--applied", "return=minimal; x"]) == 1
    out, err = capsys.readouterr()
    assert out == "return=minimal\n"
    assert "takes no parameters" in err


def test_stdin_header_lines_pick_the_prefer_fields(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    request = b"POST /foo HTTP/1.1\r\nHost: example.org\r\nPrefer: respond-async, wait=100\r\n"
    _stdin(monkeypatch, request + b"prefer:handling=lenient\r\nDate: Tue, 20 Dec 2011\r\n\r\n")
    assert main([]) == 0
    assert capsys.readouterr().out.splitlines() == ["respond-async", "wait=100", "handling=lenient"]


def test_stdin_preference_applied_lines(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _stdin(monkeypatch, b"HTTP/1.1 200 OK\nPrefer: wait=1\nPreference-Applied: return=minimal\n")
    assert main(["--applied"]) == 0
    assert capsys.readouterr().out == "return=minimal\n"


def test_stdin_bare_values_one_per_line(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _stdin(monkeypatch, b'return=minimal\n\n foo="caf\xe9"\n')
    assert main([]) == 0
    assert capsys.readouterr().out.splitlines() == ["return=minimal", 'foo="caf\xe9"']


def test_stdin_without_a_prefer_field_exits_1(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _stdin(monkeypatch, b"HTTP/1.1 200 OK\nContent-Type: text/plain\n\n")
    assert main([]) == 1
    out, err = capsys.readouterr()
    assert (out, err) == ("", "no field value found\n")


def test_empty_stdin_exits_1(monkeypatch: pytest.MonkeyPatch) -> None:
    _stdin(monkeypatch, b"")
    assert main([]) == 1


def test_bad_options_exit_2() -> None:
    with pytest.raises(SystemExit) as caught:
        main(["--nope"])
    assert caught.value.code == 2
