"""The PyPI release 0.2.0 as an oracle: 1.0.0 answers the same, except where documented.

Set PREFERHDR_V02 to a folder holding the 0.2.0 package (for example the unpacked wheel:
``pip download preferhdr==0.2.0 --no-deps`` and unzip it); the test skips otherwise.
"""

from __future__ import annotations

import importlib.util
import os
import pickle
import random
import subprocess
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest
from generators import any_value, noise, token

import preferhdr


@pytest.fixture(scope="module")
def old() -> ModuleType:
    folder = os.environ.get("PREFERHDR_V02")
    if not folder:
        pytest.skip("set PREFERHDR_V02 to the unpacked 0.2.0 release")
    init = Path(folder) / "preferhdr" / "__init__.py"
    spec = importlib.util.spec_from_file_location(
        "preferhdr_v02", init, submodule_search_locations=[str(init.parent)]
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["preferhdr_v02"] = module
    spec.loader.exec_module(module)
    assert module.__version__ == "0.2.0"
    return module


def _outcome(module: ModuleType, call: str, *args: Any, **kwargs: Any) -> object:
    try:
        result = eval(call, {"m": module, "args": args, "kwargs": kwargs})
    except (TypeError, ValueError) as error:
        family = "PreferError" if type(error).__name__ == "PreferError" else type(error).__name__
        where = (getattr(error, "position", None), getattr(error, "field", None))
        # 1.0.0 cuts quoted input to 40 characters; shorter messages are unchanged.
        message = str(error) if len(str(error)) < 60 else None
        return family, where, message
    if isinstance(result, tuple):
        return [(p.token, p.value, dict(p.params)) for p in result], repr(result)
    if hasattr(result, "token"):
        return result.token, result.value, dict(result.params), repr(result)
    return result


def _same(old: ModuleType, call: str, *args: Any, **kwargs: Any) -> None:
    before = _outcome(old, call, *args, **kwargs)
    assert before == _outcome(preferhdr, call, *args, **kwargs), (call, args, kwargs)


@pytest.mark.parametrize("seed", [1, 2])
def test_parse_answers_as_0_2_0(old: ModuleType, seed: int) -> None:
    rng = random.Random(seed)
    for _ in range(4000):
        value = any_value(rng)
        values = [value, any_value(rng)] if rng.random() < 0.3 else value
        for strict in (False, True):
            for applied in (False, True):
                _same(old, "m.parse(*args, **kwargs)", values, strict=strict, applied=applied)
        prefs = "m.parse(args[0])"
        for prop in ("respond_async", "return_", "wait", "handling"):
            _same(old, f"{prefs}.{prop}", value)
        name = token(rng)
        _same(old, f"{prefs}.get(args[1])", value, name)
        _same(old, f"m.build({prefs}.applied(args[1]), applied=True)", value, name)
        _same(old, f"m.build({prefs})", value)


@pytest.mark.parametrize("seed", [1, 2])
def test_preference_and_vary_answer_as_0_2_0(old: ModuleType, seed: int) -> None:
    rng = random.Random(seed)
    for _ in range(4000):
        name, value, other = noise(rng, 6), noise(rng, 10), token(rng)
        _same(old, "str(m.Preference(*args))", name, value)
        _same(old, "str(m.Preference(*args))", other, value)
        _same(old, "str(m.Preference(args[0], None, {args[1]: args[2]}))", other, name, value)
        _same(old, "m.vary(args[0])", noise(rng, 12))
        _same(old, "m.vary(list(args))", other, noise(rng, 6))


def test_the_documented_changes(old: ModuleType) -> None:
    assert preferhdr.parse(None) == ()
    with pytest.raises(TypeError):
        old.parse(None)
    for call in ("m.parse('a').get(1)", "m.parse('a').applied(1)", "m.parse(1)"):
        assert _outcome(preferhdr, call)[0] == "TypeError"  # type: ignore[index]
    assert old.parse("a").get(1) is None
    assert old.parse("a").applied(1) == ()
    long = "x" * 100 + "\r"
    with pytest.raises(old.PreferError) as before:
        old.Preference(long)
    with pytest.raises(preferhdr.PreferError) as after:
        preferhdr.Preference(long)
    assert len(str(before.value)) > 100 > len(str(after.value))
    assert old.Preference.__module__ == "preferhdr_v02._model"
    assert preferhdr.Preference.__module__ == "preferhdr"


def test_pickles_written_by_0_2_0_load(old: ModuleType) -> None:
    program = (
        "import pickle, sys; from preferhdr import parse, PreferError;"
        "prefs = parse('wait=1; a=\"x y\", return=minimal');"
        "sys.stdout.write(pickle.dumps((prefs, prefs[0], PreferError('m', 1, 0))).hex())"
    )
    folder = os.environ["PREFERHDR_V02"]
    done = subprocess.run(
        [sys.executable, "-I", "-c", f"import sys; sys.path.insert(0, {folder!r}); {program}"],
        capture_output=True,
        text=True,
        check=True,
    )
    data = bytes.fromhex(done.stdout)
    assert b"preferhdr._model" in data
    prefs, first, error = pickle.loads(data)
    assert prefs == preferhdr.parse('wait=1; a="x y", return=minimal')
    assert isinstance(prefs, preferhdr.Preferences)
    assert first == prefs[0] and first.params["A"] == "x y"
    assert isinstance(error, preferhdr.PreferError)
    assert (error.message, error.position, error.field) == ("m", 1, 0)
