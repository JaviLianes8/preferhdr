"""Seeded fuzzing: hostile input never crashes, hangs or leaks, and the promises hold."""

from __future__ import annotations

import random

import pytest
from generators import any_value, noise

from preferhdr import Preference, PreferError, build, parse, vary


def _unicode(rng: random.Random) -> str:
    return "".join(
        chr(rng.choice([rng.randint(0, 0x2FF), rng.randint(0, 0x10FFFF)]))
        for _ in range(rng.randint(0, 30))
    )


def _inputs(rng: random.Random, count: int) -> list[str]:
    makers = [any_value, noise, _unicode]
    return [rng.choice(makers)(rng) for _ in range(count)]


@pytest.mark.parametrize("seed", [11, 12, 13])
def test_tolerant_parsing_never_raises_and_its_output_is_valid(seed: int) -> None:
    rng = random.Random(seed)
    for value in _inputs(rng, 8000):
        prefs = parse(value)
        names = [pref.token for pref in prefs]
        assert len(names) == len(set(names))
        header = build(prefs)
        assert header == "" or parse(header, strict=True) == prefs
        assert parse(header) == prefs
        assert "\r" not in header and "\n" not in header
        applied = parse(value, applied=True)
        assert all(not pref.params for pref in applied)
        assert [p.token for p in applied] == names


@pytest.mark.parametrize("seed", [21, 22, 23])
def test_strict_parsing_raises_only_prefer_error_with_a_bounded_message(seed: int) -> None:
    rng = random.Random(seed)
    for value in _inputs(rng, 8000):
        values = [value, any_value(rng)]
        for applied in (False, True):
            try:
                prefs = parse(values, strict=True, applied=applied)
            except PreferError as error:
                assert error.field in (0, 1)
                assert error.position is not None
                assert 0 <= error.position <= len(values[error.field])
                assert len(str(error)) < 120
                continue
            # What strict mode accepts, the tolerant parser reads the same way.
            assert parse(values, applied=applied) == prefs


@pytest.mark.parametrize("seed", [31, 32])
def test_building_from_any_names_and_values_is_safe(seed: int) -> None:
    rng = random.Random(seed)
    for _ in range(8000):
        name, value = rng.choice([noise, _unicode])(rng), _unicode(rng)
        try:
            pref = Preference(name, value, {rng.choice(["x", name]): value})
        except PreferError as error:
            assert len(str(error)) < 600  # 40 characters, each escaped to at most 10
            continue
        header = build([pref])
        assert parse(header, strict=True) == (pref,)
        assert str(pref) == header


@pytest.mark.parametrize("seed", [41, 42])
def test_vary_never_lists_prefer_twice(seed: int) -> None:
    rng = random.Random(seed)
    for _ in range(5000):
        current = rng.choice([noise, any_value, _unicode])(rng)
        try:
            out = vary(current)
        except PreferError as error:
            assert len(str(error)) < 600
            continue
        members = [m.strip() for m in out.split(",")]
        assert out == "*" or [m.lower() for m in members].count("prefer") == 1
        assert vary(out) == out
