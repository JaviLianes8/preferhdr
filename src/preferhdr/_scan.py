"""Scan one field value into raw preferences, tolerantly or against the sender grammar."""

from __future__ import annotations

from ._errors import PreferError
from ._grammar import TCHAR, is_text_char

# (name, value, parameters in order, offset where the member starts)
Raw = tuple[str, "str | None", list[tuple[str, "str | None"]], int]
_OWS = " \t"


class _Malformed(Exception):
    def __init__(self, message: str, position: int) -> None:
        super().__init__(message)
        self.message = message
        self.position = position


class _Scanner:
    def __init__(self, text: str, strict: bool, applied: bool) -> None:
        self.text = text
        self.pos = 0
        self.strict = strict
        self.applied = applied

    def peek(self) -> str:
        return self.text[self.pos] if self.pos < len(self.text) else ""

    def skip_ows(self) -> int:
        start = self.pos
        while self.pos < len(self.text) and self.text[self.pos] in _OWS:
            self.pos += 1
        return self.pos - start

    def fail(self, message: str, position: int | None = None) -> _Malformed:
        return _Malformed(message, self.pos if position is None else position)

    def token(self) -> str:
        start = self.pos
        while self.pos < len(self.text) and self.text[self.pos] in TCHAR:
            self.pos += 1
        if self.pos == start:
            raise self.fail("expected a token")
        return self.text[start : self.pos]

    def quoted(self) -> str:
        start = self.pos
        self.pos += 1
        out: list[str] = []
        while self.pos < len(self.text):
            ch = self.text[self.pos]
            if ch == '"':
                self.pos += 1
                return "".join(out)
            if ch == "\\":
                if self.pos + 1 == len(self.text):
                    break
                self.pos += 1
                ch = self.text[self.pos]
            if not is_text_char(ch):
                raise self.fail("invalid character in quoted string")
            out.append(ch)
            self.pos += 1
        raise self.fail("unterminated quoted string", start)

    def at_stop(self) -> bool:
        return self.pos >= len(self.text) or self.text[self.pos] in ";,"

    def pair(self) -> tuple[str, str | None]:
        name = self.token().lower()
        before = self.skip_ows()
        value: str | None = None
        if self.peek() == "=":
            if before and self.strict:
                raise self.fail("whitespace before '='", self.pos - before)
            self.pos += 1
            value = self.word()
            self.skip_ows()
        if not self.at_stop():
            raise self.fail("unexpected character")
        return name, value or None

    def word(self) -> str:
        after = self.skip_ows()
        if after and self.strict:
            raise self.fail("whitespace after '='", self.pos - after)
        if self.peek() == '"':
            return self.quoted()
        if self.peek() in TCHAR:
            return self.token()
        if self.strict:
            raise self.fail("expected a token or quoted string after '='")
        return ""

    def skip_to(self, start: int, stops: str) -> None:
        """Resume after a malformed segment: next top-level stop, quoted strings skipped."""
        self.pos = start
        in_quotes = False
        while self.pos < len(self.text):
            ch = self.text[self.pos]
            if in_quotes and ch == "\\":
                self.pos += 1
            elif ch == '"':
                in_quotes = not in_quotes
            elif ch in stops and not in_quotes:
                return
            self.pos += 1

    def member(self) -> Raw:
        start = self.pos
        name, value = self.pair()
        params: list[tuple[str, str | None]] = []
        while self.peek() == ";":
            if self.applied and self.strict:
                raise self.fail("Preference-Applied takes no parameters")
            self.pos += 1
            self.skip_ows()
            if self.at_stop():
                continue
            param_start = self.pos
            try:
                params.append(self.pair())
            except _Malformed:
                if self.strict:
                    raise
                self.skip_to(param_start, ";,")
        return name, value, [] if self.applied else params, start


def scan_field(text: str, *, strict: bool, applied: bool) -> list[Raw]:
    """Return the members of one field value; strict mode raises ``PreferError``."""
    if not strict:
        # RFC 9110 section 5.5 lets a recipient replace CR, LF and NUL with SP.
        text = text.replace("\r", " ").replace("\n", " ").replace("\0", " ")
    scanner = _Scanner(text, strict, applied)
    members: list[Raw] = []
    need_member = True
    try:
        while True:
            scanner.skip_ows()
            if not scanner.peek():
                if need_member and strict:
                    raise scanner.fail("empty list element")
                return members
            if scanner.peek() == ",":
                if strict:
                    raise scanner.fail("empty list element")
                scanner.pos += 1
                continue
            start = scanner.pos
            try:
                members.append(scanner.member())
            except _Malformed:
                if strict:
                    raise
                scanner.skip_to(start, ",")
            need_member = scanner.peek() == ","
            scanner.pos += 1
    except _Malformed as error:
        raise PreferError(error.message, error.position) from None
