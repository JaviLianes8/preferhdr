"""The 1.0.0 surface: signatures, types, modules and the behaviour changed for 1.0.0."""

from __future__ import annotations

import dataclasses
import importlib
import inspect
import os
import pickle
import subprocess
import sys
from pathlib import Path

import pytest

import preferhdr
from preferhdr import Preference, Preferences, PreferError, build, parse, vary
from preferhdr._cli import main

SRC = Path(__file__).resolve().parents[1] / "src"

SIGNATURES = {
    "parse": "(value: 'str | Iterable[str] | None', *, strict: 'bool' = False, "
    "applied: 'bool' = False) -> 'Preferences'",
    "build": "(prefs: 'Iterable[Preference]', *, applied: 'bool' = False) -> 'str'",
    "vary": "(current: 'str | Iterable[str] | None' = None) -> 'str'",
    "Preference": "(token: 'str', value: 'str | None' = None, "
    "params: 'Mapping[str, str | None]' = <factory>) -> None",
    "PreferError": "(message: 'str', position: 'int | None' = None, field: 'int | None' = None)",
    "Preferences": "(prefs: 'Iterable[Preference]' = ()) -> 'Preferences'",
}


@pytest.mark.parametrize("name", sorted(SIGNATURES))
def test_signatures_are_the_ones_promised(name: str) -> None:
    assert str(inspect.signature(getattr(preferhdr, name))) == SIGNATURES[name]


def test_the_public_classes_and_their_members() -> None:
    assert issubclass(PreferError, ValueError)
    assert issubclass(Preferences, tuple)
    assert [f.name for f in dataclasses.fields(Preference)] == ["token", "value", "params"]
    assert Preference.__dataclass_params__.frozen  # type: ignore[attr-defined]
    for prop in ("respond_async", "return_", "wait", "handling"):
        assert isinstance(vars(Preferences)[prop], property)
    assert callable(Preferences.get)
    assert callable(Preferences.applied)
    error = PreferError("m", 1, 2)
    assert (error.message, error.position, error.field) == ("m", 1, 2)
    assert str(PreferError("m", None, 2)) == "m"
    assert str(PreferError("m", 3)) == "m at position 3"


def test_public_classes_live_in_the_package_and_pickle_there() -> None:
    for cls in (PreferError, Preference, Preferences):
        assert cls.__module__ == "preferhdr"
    prefs = parse("wait=1; a, return=minimal")
    for thing in (prefs, prefs[0], PreferError("m", 1, 0)):
        data = pickle.dumps(thing)
        assert b"preferhdr._" not in data
        copy = pickle.loads(data)
        assert type(copy) is type(thing)
        assert repr(copy) == repr(thing)


def test_a_missing_header_gives_no_preferences() -> None:
    prefs = parse(None)
    assert prefs == () and isinstance(prefs, Preferences)
    assert parse(None, strict=True) == ()
    assert parse(None, strict=True, applied=True) == ()


@pytest.mark.parametrize("bad", [1, None, b"a", ("a",)])
def test_lookups_with_a_name_that_is_not_a_str_are_type_errors(bad: object) -> None:
    prefs = parse("a, b")
    with pytest.raises(TypeError, match="preference names must be str"):
        prefs.get(bad)  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="preference names must be str"):
        prefs.applied("a", bad)  # type: ignore[arg-type]
    assert (bad in prefs) is False


def test_type_error_messages_name_the_type() -> None:
    with pytest.raises(TypeError, match=r"^expected a str or an iterable of str, not int$"):
        parse(5)  # type: ignore[arg-type]
    with pytest.raises(TypeError, match=r"^params must be a mapping, not list$"):
        Preference("a", None, [("b", None)])  # type: ignore[arg-type]
    with pytest.raises(TypeError, match=r"^expected Preference, not str$"):
        build(["a"])  # type: ignore[list-item]
    with pytest.raises(TypeError, match=r"^Vary values must be str, not int$"):
        vary([1])  # type: ignore[list-item]


def test_messages_quote_at_most_forty_characters() -> None:
    with pytest.raises(PreferError) as caught:
        Preference("a" * 41 + "@")
    assert str(caught.value) == f"preference name {'a' * 40!r}... (42 characters) is not a token"
    with pytest.raises(PreferError) as caught:
        Preference("a" * 39 + "@")
    assert str(caught.value) == f"preference name {'a' * 39 + '@'!r} is not a token"


def test_importing_the_main_module_does_not_run_the_command() -> None:
    sys.modules.pop("preferhdr.__main__", None)
    module = importlib.import_module("preferhdr.__main__")
    assert module.main is main


def _run(*args: str) -> subprocess.CompletedProcess[str]:
    env = {**os.environ, "PYTHONPATH": str(SRC)}
    return subprocess.run(
        [sys.executable, "-m", "preferhdr", *args],
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )


def test_a_huge_unknown_argument_is_cut_in_the_usage_error() -> None:
    run = _run("--" + "x" * 10_000)
    assert run.returncode == 2
    assert len(run.stderr) < 600
    assert run.stderr.rstrip().endswith("...")


def test_a_closed_output_pipe_exits_1_without_a_traceback() -> None:
    env = {**os.environ, "PYTHONPATH": str(SRC)}
    # Far more output than any pipe buffer holds, so the writer meets the closed pipe.
    request = "\n".join(f"p{i}=1" for i in range(200_000)).encode("ascii")
    with subprocess.Popen(
        [sys.executable, "-m", "preferhdr"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
    ) as proc:
        assert proc.stdin is not None and proc.stdout is not None and proc.stderr is not None
        proc.stdin.write(request)
        proc.stdin.close()
        proc.stdout.read(10)
        proc.stdout.close()
        err = proc.stderr.read()
        assert proc.wait(timeout=120) == 1
    assert b"Traceback" not in err
