"""Seeded generators of header values, shared by the grammar, oracle and fuzz tests.

Written by hand from the RFC 9110 and RFC 7240 grammars; the tests that use them check
the results against rules read from the fetched specification text or against other
parsers, never against values written here.
"""

from __future__ import annotations

import random

TCHAR = "!#$%&'*+-.^_`|~0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
# Characters a quoted string may hold as they are (qdtext), C1 controls left out.
QDTEXT = (
    "\t "
    + "".join(chr(c) for c in range(0x21, 0x7F) if chr(c) not in '"\\')
    + "".join(map(chr, range(0xA0, 0x100)))
)
# Everything the grammar treats specially, plus characters it never allows.
SPECIAL = ' \t,;="\\\r\n\x00\x7f\x85\xa0\xff\u0100\u2028\U0001f600'


def token(rng: random.Random, alphabet: str = TCHAR, longest: int = 8) -> str:
    return "".join(rng.choice(alphabet) for _ in range(rng.randint(1, longest)))


def ows(rng: random.Random) -> str:
    return rng.choice(["", "", "", " ", "\t", "  ", " \t"])


def quoted(rng: random.Random, escapes: bool = True) -> str:
    out = []
    for _ in range(rng.randint(0, 8)):
        if escapes and rng.random() < 0.2:
            out.append("\\" + rng.choice(QDTEXT + '"\\'))
        else:
            out.append(rng.choice(QDTEXT))
    return '"' + "".join(out) + '"'


def word(rng: random.Random) -> str:
    return token(rng) if rng.random() < 0.5 else quoted(rng)


def pair(rng: random.Random, names: str = TCHAR) -> str:
    name = token(rng, names)
    return name if rng.random() < 0.4 else f"{name}={word(rng)}"


def grammar_value(rng: random.Random, names: str = TCHAR, applied: bool = False) -> str:
    """A field value the sender grammar allows (names may repeat)."""
    members = []
    for _ in range(rng.randint(1, 4)):
        member = pair(rng, names)
        for _ in range(0 if applied else rng.randint(0, 3)):
            member += ows(rng) + ";"
            if rng.random() < 0.85:
                member += ows(rng) + pair(rng, names)
        members.append(member)
    separators = [ows(rng) + "," + ows(rng) for _ in members]
    text = members[0] + "".join(s + m for s, m in zip(separators, members[1:], strict=False))
    return ows(rng) + text + ows(rng)


def mutate(rng: random.Random, text: str) -> str:
    """Insert, delete or replace a few characters, often breaking the grammar."""
    chars = list(text)
    for _ in range(rng.randint(1, 3)):
        where = rng.randint(0, len(chars))
        pick = rng.random()
        if pick < 0.4:
            chars.insert(where, rng.choice(SPECIAL + TCHAR))
        elif pick < 0.7 and chars:
            del chars[min(where, len(chars) - 1)]
        elif chars:
            chars[min(where, len(chars) - 1)] = rng.choice(SPECIAL)
    return "".join(chars)


def noise(rng: random.Random, longest: int = 40) -> str:
    """Short strings weighted towards the characters the parser cares about."""
    alphabet = SPECIAL + 'aZ09-!"' + "".join(map(chr, range(0x80, 0xA0)))
    return "".join(rng.choice(alphabet) for _ in range(rng.randint(0, longest)))


def any_value(rng: random.Random) -> str:
    pick = rng.random()
    if pick < 0.4:
        return grammar_value(rng)
    if pick < 0.8:
        return mutate(rng, grammar_value(rng))
    return noise(rng)
