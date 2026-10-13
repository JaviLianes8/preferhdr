"""Build the wheel, install it in a throwaway venv and drive the installed package.

Slow and needs the build backend, so it runs only with PREFERHDR_E2E=1.
"""

from __future__ import annotations

import os
import subprocess
import sys
import venv
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

pytestmark = pytest.mark.skipif(
    os.environ.get("PREFERHDR_E2E") != "1", reason="set PREFERHDR_E2E=1 to build and install"
)

PROGRAM = r"""
import importlib.metadata, importlib.resources, pickle
import preferhdr
from preferhdr import Preference, PreferError, Preferences, build, parse, vary

assert "site-packages" in preferhdr.__file__, preferhdr.__file__
assert importlib.metadata.version("preferhdr") == preferhdr.__version__
assert importlib.resources.files("preferhdr").joinpath("py.typed").is_file()
prefs = parse(["Respond-Async, wait=10, , bad member", 'return=minimal; foo="a, b"', "wait=99"])
assert isinstance(prefs, Preferences)
assert (prefs.respond_async, prefs.wait, prefs.return_) == (True, 10, "minimal"), prefs
assert prefs.get("RETURN").params["foo"] == "a, b"
assert parse('foo=""; bar') == (Preference("foo", None, {"bar": None}),)
try:
    parse(["a", "b =1"], strict=True)
except PreferError as error:
    copy = pickle.loads(pickle.dumps(error))
    assert (copy.position, copy.field) == (1, 1), (copy.position, copy.field)
else:
    raise AssertionError("strict accepted whitespace before =")
try:
    Preference("return", "minimal\r\nSet-Cookie: a=1")
except PreferError:
    pass
else:
    raise AssertionError("a CR LF value was accepted")
assert build(prefs.applied("return", "wait"), applied=True) == "wait=10, return=minimal"
assert parse(build(prefs), strict=True) == prefs
assert vary("Accept") == "Accept, Prefer"
print("e2e ok")
"""


def _run(
    *cmd: str | Path, cwd: Path | None = None, stdin: str | None = None
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [str(c) for c in cmd], cwd=cwd, capture_output=True, text=True, input=stdin, check=False
    )


def test_installed_wheel_end_to_end(tmp_path: Path) -> None:
    dist = tmp_path / "dist"
    built = _run(sys.executable, "-m", "build", "--outdir", dist, ROOT)
    assert built.returncode == 0, built.stderr
    (wheel,) = dist.glob("preferhdr-*.whl")
    (sdist,) = dist.glob("preferhdr-*.tar.gz")
    names = zipfile.ZipFile(wheel).namelist()
    assert "preferhdr/py.typed" in names
    assert "preferhdr/__main__.py" in names
    assert not any(name.startswith("tests/") for name in names)
    assert any(name.endswith("entry_points.txt") for name in names)
    listing = _run(sys.executable, "-m", "tarfile", "-l", sdist).stdout
    assert "IMPROVEMENTS-round" not in listing
    assert "tests/upstream/MANIFEST.json" in listing
    assert "rfc7240.txt" not in listing
    assert "tests/test_rfc_examples.py" in listing
    assert "scripts/fetch_upstream.py" in listing

    env_dir = tmp_path / "venv"
    venv.create(env_dir, with_pip=True)
    bindir = env_dir / ("Scripts" if sys.platform == "win32" else "bin")
    python = bindir / "python"
    installed = _run(python, "-m", "pip", "install", "-q", wheel)
    assert installed.returncode == 0, installed.stderr

    # Run from an empty folder so the source tree cannot shadow the install.
    work = tmp_path / "work"
    work.mkdir()
    result = _run(python, "-I", "-c", PROGRAM, cwd=work)
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "e2e ok"

    script = bindir / ("preferhdr.exe" if sys.platform == "win32" else "preferhdr")
    request = "POST /foo HTTP/1.1\nHost: example.org\nPrefer: respond-async, wait=100\n"
    checked = _run(script, cwd=work, stdin=request + "Prefer: handling =lenient\n")
    assert checked.returncode == 1, checked.stderr
    assert checked.stdout.splitlines() == ["respond-async", "wait=100", "handling=lenient"]
    assert "whitespace before '=' at position 8 of field 1" in checked.stderr
    module = _run(python, "-I", "-m", "preferhdr", "--json", "return=minimal", cwd=work)
    assert module.returncode == 0, module.stderr
    assert '"value": "minimal"' in module.stdout
