"""The public API is typed: mypy infers the documented types and rejects wrong ones."""

from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

import pytest

SRC = Path(__file__).resolve().parents[1] / "src"

SNIPPET = """
from preferhdr import Preference, Preferences, build, parse, vary
prefs = parse(["respond-async", "wait=10"], strict=True)
reveal_type(prefs)
reveal_type(prefs.return_)
reveal_type(prefs.handling)
reveal_type(prefs.wait)
reveal_type(prefs.get("wait"))
reveal_type(prefs[0].params)
reveal_type(build(prefs.applied("wait"), applied=True))
reveal_type(vary(None))
assert "wait" in prefs
parse(b"wait=1")
parse("wait=1", True)
Preference("a", 5)
build(["a"])
prefs.wait = 3
"""


@pytest.fixture(scope="module")
def mypy_output(tmp_path_factory: pytest.TempPathFactory) -> str:
    folder = tmp_path_factory.mktemp("typing")
    target = folder / "snippet.py"
    target.write_text(SNIPPET, encoding="utf-8")
    config = folder / "mypy.ini"
    config.write_text(f"[mypy]\nmypy_path = {SRC.as_posix()}\n", encoding="utf-8")
    cache = str(folder / "cache")
    args = ["--strict", "--config-file", str(config), "--cache-dir", cache, str(target)]
    try:
        from mypy import api
    except ImportError:
        # The interpreter running pytest may lack mypy while the one on PATH has it.
        program = shutil.which("mypy")
        if program is None:
            pytest.skip("mypy is not installed")
        result = subprocess.run([program, *args], capture_output=True, text=True, check=False)
        return result.stdout + result.stderr
    out, err, _ = api.run(args)
    return str(out) + str(err)


def test_the_api_has_the_documented_types(mypy_output: str) -> None:
    assert [_revealed(mypy_output, line) for line in range(4, 12)] == [
        "preferhdr._prefs.Preferences",
        "Literal['minimal'] | Literal['representation'] | None",
        "Literal['strict'] | Literal['lenient'] | None",
        "int | None",
        "preferhdr._model.Preference | None",
        "Mapping[str, str | None]",
        "str",
        "str",
    ]


def test_misuse_is_rejected_and_name_lookup_type_checks(mypy_output: str) -> None:
    expected = (
        (13, "arg-type"),
        (14, "call-arg"),
        (15, "arg-type"),
        (16, "list-item"),
        (17, "misc"),
    )
    for line, code in expected:
        assert re.search(rf"snippet\.py:{line}: error: .*\[{code}\]", mypy_output), mypy_output
    assert mypy_output.count(": error: ") == len(expected), mypy_output


def _revealed(output: str, line: int) -> str:
    match = re.search(rf"snippet\.py:{line}: note: Revealed type is \"(.+)\"", output)
    assert match, output
    # Older mypy releases spell builtins with their module prefix.
    return re.sub(r"\b(builtins|typing|collections\.abc)\.", "", match.group(1))
