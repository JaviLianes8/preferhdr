"""Independent parsers as oracles: Python's standard library and parse-prefer-header.

Neither is a dependency. The standard library pair is ``urllib.request.parse_http_list``
(comma lists with quoted strings) and ``email.message.Message.get_params`` (``;``
parameters). parse-prefer-header 1.0.0 is an RFC 7240 parser for Node.js, run with
``node``; the test skips without it: ``npm install --prefix tests/upstream
parse-prefer-header@1.0.0`` (the folder is ignored by git). Each known difference is
asserted precisely, so a change on either side shows.
"""

from __future__ import annotations

import json
import random
import shutil
import subprocess
from email.message import Message
from pathlib import Path
from urllib.request import parse_http_list

import pytest
from conftest import UPSTREAM
from generators import TCHAR, grammar_value, token

from preferhdr import build, parse

ROOT = Path(__file__).resolve().parents[1]
# email reads a name ending in "*" or "*<digits>" as an RFC 2231 section, so none here.
NAMES = TCHAR.replace("*", "")
Row = tuple[str, "str | None", list[tuple[str, "str | None"]]]


def _ours(value: str) -> list[Row]:
    return [(p.token, p.value, list(p.params.items())) for p in parse(value, strict=True)]


def _stdlib(value: str) -> list[Row]:
    rows: list[Row] = []
    for element in parse_http_list(value):
        message = Message()
        message["X-Prefer"] = "x; " + element
        params = message.get_params(header="x-prefer")
        assert params is not None
        (name, first), *rest = params[1:]
        kept: dict[str, str | None] = {}
        for key, param in rest:
            # email keeps empty segments and the case of names without a value; RFC 7240
            # ignores the first and compares names without case, and the first one wins.
            if key:
                kept.setdefault(key.lower(), param or None)
        rows.append((name.lower(), first or None, list(kept.items())))
    return rows


def _corpus(seed: int, names: str) -> list[str]:
    rng = random.Random(seed)
    out: list[str] = []
    while len(out) < 4000:
        value = grammar_value(rng, names)
        built = build(parse(value))
        for text in (value, built):
            # email misreads an escaped DQUOTE (asserted below), so leave those out here.
            if '\\"' not in text and parse(text) and _strict(text):
                out.append(text)
    return out


def _strict(value: str) -> bool:
    try:
        parse(value, strict=True)
    except ValueError:
        return False
    return True


@pytest.mark.parametrize(("seed", "names"), [(1, "abcdefgh"), (2, NAMES), (3, "aAbB-.!")])
def test_the_standard_library_reads_every_valid_value_the_same(seed: int, names: str) -> None:
    for value in _corpus(seed, names):
        assert _ours(value) == _stdlib(value), value


def test_the_standard_library_misreads_an_escaped_quote() -> None:
    value = 'a="x\\"y"; b=1'
    assert _ours(value) == [("a", 'x"y', [("b", "1")])]
    assert _stdlib(value) == [("a", '"x"y"; b=1', [])]


def _node(values: list[str]) -> list[dict[str, object]]:
    node = shutil.which("node")
    package = UPSTREAM / "node_modules" / "parse-prefer-header" / "package.json"
    if node is None or not package.is_file():
        pytest.skip("node or parse-prefer-header is missing")
    assert json.loads(package.read_text(encoding="utf-8"))["version"] == "1.0.0"
    script = str(ROOT / "scripts" / "prefer_oracle.js")
    data = json.dumps(values).encode("utf-8")
    done = subprocess.run([node, script, str(UPSTREAM)], input=data, capture_output=True)
    assert done.returncode == 0, done.stderr
    result: list[dict[str, object]] = json.loads(done.stdout.decode("utf-8"))
    return result


def _camel(name: str) -> str:
    first, *rest = name.split("-")
    return first + "".join(word.capitalize() for word in rest)


def _expected(value: str) -> dict[str, object]:
    """Our reading in the shape parse-prefer-header gives: flat camel-case keys."""
    out: dict[str, object] = {}
    for pref in parse(value):
        out.setdefault(_camel(pref.token), pref.value or True)
        for name, param in pref.params.items():
            out.setdefault(_camel(f"{pref.token}-{name}"), param or True)
    return out


def _word_name(rng: random.Random) -> str:
    return "-".join(token(rng, "abcdefghij", 5) for _ in range(rng.randint(1, 3)))


def _node_corpus(rng: random.Random) -> str:
    # It splits on every DQUOTE and keeps escapes, so values hold neither; names are
    # lower-case words, which its camel-case keys keep apart; preferences are unique.
    names: list[str] = []
    while len(names) < rng.randint(1, 4):
        name = _word_name(rng)
        if name not in names:
            names.append(name)
    members = []
    for name in names:
        member = name if rng.random() < 0.3 else f"{name}={_plain(rng)}"
        for _ in range(rng.randint(0, 3)):
            param = _word_name(rng)
            member += f"; {param}" if rng.random() < 0.3 else f"; {param}={_plain(rng)}"
        members.append(member)
    return ", ".join(members)


def _plain(rng: random.Random) -> str:
    if rng.random() < 0.5:
        return token(rng)
    text = "".join(rng.choice("abc ,;=-/") for _ in range(rng.randint(1, 8)))
    return f'"{text}"'


@pytest.mark.parametrize("seed", [1, 2, 3])
def test_parse_prefer_header_reads_every_value_the_same(seed: int) -> None:
    rng = random.Random(seed)
    values = [_node_corpus(rng) for _ in range(5000)]
    assert all(_strict(value) for value in values)
    assert _node(values) == [_expected(value) for value in values]


def test_parse_prefer_header_differences() -> None:
    values = ['a="x\\"y"', "a=1, a=2; b", "Return=Minimal", 'a=""', "respond-async"]
    assert _node(values) == [
        {},  # an escaped DQUOTE leaves its quote count odd, and it drops the whole value
        {"a": "1", "aB": True},  # it keeps parameters of a repeated preference
        {"return": "Minimal"},
        {"a": True},
        {"respondAsync": True},
    ]
    assert [_expected(value) for value in values] == [
        {"a": 'x"y'},
        {"a": "1"},
        {"return": "Minimal"},
        {"a": True},
        {"respondAsync": True},
    ]
