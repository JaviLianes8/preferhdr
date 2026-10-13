"""Command line checker: print the preferences in a header and flag grammar errors."""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections.abc import Sequence

from ._errors import PreferError
from ._parse import parse

_HEADER_LINE = re.compile(r"^([!#$%&'*+\-.^_`|~0-9A-Za-z]+):(.*)$")


def _from_lines(text: str, applied: bool) -> list[str]:
    """Field values from stdin: matching header lines when there are any, else every line."""
    wanted = "preference-applied" if applied else "prefer"
    lines = [line.rstrip("\r") for line in text.split("\n")]
    headers = [m for m in map(_HEADER_LINE.match, lines) if m]
    if headers:
        return [m.group(2).strip(" \t") for m in headers if m.group(1).lower() == wanted]
    return [line for line in lines if line.strip(" \t")]


def main(argv: Sequence[str] | None = None) -> int:
    """Run the checker; returns 0 when every value is valid, 1 when one is not."""
    cli = argparse.ArgumentParser(
        prog="preferhdr",
        description="Parse Prefer (or Preference-Applied) header values and check them "
        "against the RFC 7240 grammar. Without VALUE, read header lines or values on stdin.",
    )
    cli.add_argument("values", nargs="*", metavar="VALUE", help="a field value")
    cli.add_argument("--applied", action="store_true", help="read Preference-Applied")
    cli.add_argument("--json", action="store_true", help="print JSON instead of one per line")
    args = cli.parse_args(argv)
    if args.values:
        values = list(args.values)
    else:
        # Header bytes are opaque octets (RFC 9110 obs-text), so they are read as Latin-1.
        values = _from_lines(sys.stdin.buffer.read().decode("latin-1"), args.applied)
    if not values:
        print("no field value found", file=sys.stderr)
        return 1
    status = 0
    try:
        parse(values, strict=True, applied=args.applied)
    except PreferError as error:
        print(f"invalid: {error}", file=sys.stderr)
        status = 1
    prefs = parse(values, applied=args.applied)
    if args.json:
        rows = [{"token": p.token, "value": p.value, "params": dict(p.params)} for p in prefs]
        print(json.dumps(rows, indent=2))
    else:
        for pref in prefs:
            print(pref)
    return status


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
