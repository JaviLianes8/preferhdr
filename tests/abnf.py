"""A small ABNF (RFC 5234) to regular expression compiler, for rules read from RFC text.

It covers what the Prefer grammar uses: rule names, quoted literals, ``%x`` values and
ranges, concatenation, ``/``, groups, ``[ ]`` and ``*`` repetition. Rules may not be
recursive. The core rules of RFC 5234 appendix B.1 are written here by hand.
"""

from __future__ import annotations

import re

CORE = {
    "ALPHA": "%x41-5A / %x61-7A",
    "DIGIT": "%x30-39",
    "DQUOTE": "%x22",
    "HTAB": "%x09",
    "SP": "%x20",
    "VCHAR": "%x21-7E",
}
_TOKEN = re.compile(r'\s*(%x[0-9A-Fa-f]+(?:-[0-9A-Fa-f]+)?|"[^"]*"|\d*\*\d*|[\w-]+|[()\[\]/])')


def read_rule(text: str, name: str) -> str:
    """The definition of rule ``name`` as written in an RFC body, comments removed."""
    lines = text.splitlines()
    pattern = re.compile(rf"^( +){re.escape(name)} *= *(.*)$")
    for index, line in enumerate(lines):
        match = pattern.match(line)
        if not match:
            continue
        parts = [match.group(2)]
        indent = len(match.group(1))
        for more in lines[index + 1 :]:
            stripped = more.strip()
            if not stripped or len(more) - len(more.lstrip()) <= indent or "=" in stripped[:20]:
                break
            parts.append(stripped)
        joined = " ".join(_uncomment(part) for part in parts)
        return " ".join(joined.split())
    raise LookupError(name)


def _uncomment(line: str) -> str:
    """Drop an ABNF comment: a ``;`` outside a quoted literal and the rest of the line."""
    quoted = False
    for index, ch in enumerate(line):
        quoted ^= ch == '"'
        if ch == ";" and not quoted:
            return line[:index].strip()
    return line.strip()


def _char(code: int) -> str:
    return re.escape(chr(code)) if code > 0x20 else f"\\x{code:02x}"


class Compiler:
    """Compile a set of rules into regular expressions, one rule at a time."""

    def __init__(self, rules: dict[str, str]) -> None:
        self.rules = {**CORE, **rules}

    def regex(self, name: str) -> str:
        self.items = _TOKEN.findall(self.rules[name])
        self.at = 0
        out = self._alternation()
        assert self.at == len(self.items), (name, self.items[self.at :])
        return out

    def _peek(self) -> str:
        return self.items[self.at] if self.at < len(self.items) else ""

    def _alternation(self) -> str:
        options = [self._concatenation()]
        while self._peek() == "/":
            self.at += 1
            options.append(self._concatenation())
        return options[0] if len(options) == 1 else "(?:" + "|".join(options) + ")"

    def _concatenation(self) -> str:
        parts = []
        while self._peek() not in ("", "/", ")", "]"):
            parts.append(self._repetition())
        return "".join(parts)

    def _repetition(self) -> str:
        item = self._peek()
        if "*" in item and not item.startswith('"'):
            self.at += 1
            low, high = item.split("*")
            return f"(?:{self._element()}){{{low or 0},{high}}}"
        return self._element()

    def _element(self) -> str:
        item = self._peek()
        self.at += 1
        if item in ("(", "["):
            inner = self._alternation()
            closing = self._peek()
            assert closing == {"(": ")", "[": "]"}[item], self.items
            self.at += 1
            return f"(?:{inner})" + ("?" if item == "[" else "")
        if item.startswith('"'):
            return "".join(_char(ord(ch)) for ch in item[1:-1])
        if item.startswith("%x"):
            low, _, high = item[2:].partition("-")
            first = int(low, 16)
            last = int(high, 16) if high else first
            return f"[{_char(first)}-{_char(last)}]" if high else _char(first)
        saved = (self.items, self.at)
        inner = self.regex(item)
        self.items, self.at = saved
        return f"(?:{inner})"
