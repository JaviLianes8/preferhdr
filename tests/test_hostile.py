"""Huge and adversarial input: linear time, bounded messages, no recursion."""

from __future__ import annotations

import contextlib
import time
from collections.abc import Callable

import pytest

from preferhdr import Preference, PreferError, build, parse, vary

SHAPES: dict[str, Callable[[int], str]] = {
    "commas": lambda n: "," * n,
    "members": lambda n: "a," * (n // 2),
    "distinct members": lambda n: ",".join(f"p{i}" for i in range(n // 7)),
    "parameters": lambda n: "a" + ";b=1" * (n // 4),
    "semicolons": lambda n: "a" + ";" * n,
    "unterminated quote": lambda n: 'a="' + "x" * n,
    "escapes": lambda n: 'a="' + "\\," * (n // 2),
    "stray quotes": lambda n: 'a"b,' * (n // 4),
    "bad members": lambda n: '@ ;x=",' * (n // 6),
    "whitespace": lambda n: "a" + " \t" * (n // 2) + "=1",
    "long token": lambda n: "a" * n,
    "long wait": lambda n: "wait=" + "9" * n,
    "equals": lambda n: "a" + "=" * n,
}


def _seconds(work: Callable[[], object]) -> float:
    best = float("inf")
    for _ in range(3):
        start = time.perf_counter()
        work()
        best = min(best, time.perf_counter() - start)
    return best


@pytest.mark.parametrize("shape", sorted(SHAPES))
def test_parsing_is_linear(shape: str) -> None:
    small, large = SHAPES[shape](50_000), SHAPES[shape](200_000)

    def everything(text: str) -> Callable[[], object]:
        def run() -> object:
            prefs = parse(text)
            for applied in (False, True):
                with contextlib.suppress(PreferError):
                    parse(text, strict=True, applied=applied)
            return prefs.wait, build(prefs), parse(text, applied=True)

        return run

    ratio = _seconds(everything(large)) / max(_seconds(everything(small)), 1e-4)
    # Four times the input; quadratic work would take about sixteen times as long.
    assert ratio < 9, (shape, ratio)


def test_a_megabyte_in_every_error_path_gives_a_short_message() -> None:
    huge = "\x01" * 1_000_000
    checks: list[Callable[[], object]] = [
        lambda: Preference(huge),
        lambda: Preference("a", huge),
        lambda: Preference("a", None, {huge: None}),
        lambda: Preference("a", None, {"b": huge}),
        lambda: vary(huge),
        lambda: build([Preference("a" * 1_000_000)] * 2),
        lambda: build([Preference("a" * 1_000_000, None, {"b": None})], applied=True),
        lambda: parse("a" * 1_000_000 + huge, strict=True),
    ]
    for check in checks:
        with pytest.raises(PreferError) as error:
            check()
        assert len(str(error.value)) < 600


@pytest.mark.parametrize(
    "bad",
    [b"a", bytearray(b"a"), 1, 2.5, object(), ["a", 1], [b"a"]],
    ids=lambda bad: type(bad).__name__,
)
def test_wrong_types_raise_type_error_with_a_short_message(bad: object) -> None:
    with pytest.raises(TypeError) as error:
        parse(bad)  # type: ignore[arg-type]
    assert len(str(error.value)) < 100


def test_a_type_with_a_huge_name_is_cut_in_messages() -> None:
    odd = type("X" * 100_000, (), {})()
    for check in (lambda: parse(odd), lambda: Preference(odd), lambda: vary([odd])):
        with pytest.raises(TypeError) as error:
            check()
        assert len(str(error.value)) < 120


def test_a_hundred_thousand_preferences_build_and_read_back() -> None:
    prefs = [Preference(f"p{i}", str(i), {"q": "a b"}) for i in range(100_000)]
    header = build(prefs)
    assert parse(header, strict=True) == tuple(prefs)
