"""Seeded round trip: whatever the builder writes, the strict parser reads back unchanged."""

from __future__ import annotations

import random

from preferhdr import Preference, build, parse

TCHARS = "!#$%&'*+-.^_`|~0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
TEXT = "\t" + "".join(map(chr, range(0x20, 0x7F))) + "".join(map(chr, range(0xA0, 0x100)))


def _token(rng: random.Random) -> str:
    return "".join(rng.choice(TCHARS) for _ in range(rng.randint(1, 8)))


def _value(rng: random.Random) -> str | None:
    pick = rng.random()
    if pick < 0.2:
        return None
    if pick < 0.5:
        return _token(rng)
    return "".join(rng.choice(TEXT) for _ in range(rng.randint(0, 10)))


def _preferences(rng: random.Random) -> list[Preference]:
    prefs: dict[str, Preference] = {}
    for _ in range(rng.randint(1, 5)):
        params = {_token(rng).lower(): _value(rng) for _ in range(rng.randint(0, 3))}
        pref = Preference(_token(rng), _value(rng), params)
        prefs.setdefault(pref.token, pref)
    return list(prefs.values())


def test_build_then_strict_parse_is_the_identity() -> None:
    rng = random.Random(7240)
    for _ in range(2000):
        prefs = _preferences(rng)
        header = build(prefs)
        assert parse(header, strict=True) == tuple(prefs), header
        assert parse(header) == tuple(prefs), header


def test_preference_applied_round_trips_without_parameters() -> None:
    rng = random.Random(3)
    for _ in range(500):
        prefs = [Preference(p.token, p.value) for p in _preferences(rng)]
        header = build(prefs, applied=True)
        assert parse(header, strict=True, applied=True) == tuple(prefs), header


def test_parse_then_build_is_stable() -> None:
    rng = random.Random(9110)
    for _ in range(500):
        once = build(parse(build(_preferences(rng))))
        assert build(parse(once)) == once
