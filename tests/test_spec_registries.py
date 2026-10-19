"""The registered preferences, the RFC 8144 examples and the errata, read from fetched text.

Sources, fetched by ``python scripts/fetch_upstream.py`` on 2026-10-19 and checked against
the manifest (the tests skip while they are absent):
https://www.iana.org/assignments/http-parameters/preferences.csv,
https://www.rfc-editor.org/rfc/rfc7240.txt, https://www.rfc-editor.org/rfc/rfc8144.txt,
https://www.rfc-editor.org/rfc/rfc9110.txt and https://www.rfc-editor.org/errata/rfc7240.
"""

from __future__ import annotations

import csv
import html
import io
import re
import typing

from abnf import read_rule
from conftest import read_upstream

from preferhdr import Preference, Preferences, build, parse

EXAMPLE = re.compile(r"^ +(Prefer|Preference-Applied): (.*)$", flags=re.MULTILINE)


def _registry() -> list[dict[str, str]]:
    return list(csv.DictReader(io.StringIO(read_upstream("iana-preferences.csv"))))


def test_every_registered_preference_reads_builds_and_round_trips() -> None:
    rows = _registry()
    assert len(rows) >= 13
    for row in rows:
        name = row["Preference"]
        for value in (name, name.upper(), f"{name}=1; x", f'a, {name}="v w"'):
            prefs = parse(value, strict=True)
            assert name in prefs, value
            assert parse(build(prefs), strict=True) == prefs
        assert Preference(name.upper()).token == name


def _choices(row: dict[str, str]) -> set[str]:
    return set(re.findall(r'"([a-z]+)"', row["Value"]))


def test_the_typed_properties_cover_the_values_the_registry_lists() -> None:
    rows = {row["Preference"]: row for row in _registry()}
    hints = typing.get_type_hints(Preferences.return_.fget)
    assert _choices(rows["return"]) == set(typing.get_args(typing.get_args(hints["return"])[0]))
    hints = typing.get_type_hints(Preferences.handling.fget)
    assert _choices(rows["handling"]) == set(typing.get_args(typing.get_args(hints["return"])[0]))
    for name in ("return", "handling"):
        for choice in _choices(rows[name]):
            prop = "return_" if name == "return" else name
            assert getattr(parse(f"{name}={choice}"), prop) == choice
            assert getattr(parse(f'{name}="{choice}"'), prop) == choice
            assert getattr(parse(f"{name}={choice.upper()}"), prop) is None
    assert rows["respond-async"]["Value"] == ""
    assert parse("respond-async").respond_async is True


def test_the_preference_rules_of_rfc_7240_section_4() -> None:
    text = read_upstream("rfc7240.txt")
    assert read_rule(text, "return") == '"return" BWS "=" BWS ("representation" / "minimal")'
    assert read_rule(text, "handling") == '"handling" BWS "=" BWS ("strict" / "lenient")'
    assert read_rule(text, "wait") == '"wait" BWS "=" BWS delta-seconds'
    # Verified erratum 4316 names the rule delay-seconds, which RFC 9110 defines.
    assert read_rule(read_upstream("rfc9110.txt"), "delay-seconds") == "1*DIGIT"
    for digits in ("0", "7", "0100", "86400", "9" * 100):
        assert parse(f"wait={digits}").wait == int(digits)
    for other in ("-1", "1.5", "1e3", "+1", "\xb2", " ", "9" * 101):
        assert parse(f'wait="{other}"').wait is None


def test_every_example_header_in_rfc_8144_is_valid() -> None:
    examples = EXAMPLE.findall(read_upstream("rfc8144.txt"))
    assert len(examples) >= 6
    for name, value in examples:
        applied = name == "Preference-Applied"
        prefs = parse(value, strict=True, applied=applied)
        assert prefs, value
        assert build(prefs, applied=applied) == value.strip()
    assert parse("return=minimal, depth-noroot").get("depth-noroot") == Preference("depth-noroot")


def _errata() -> dict[str, str]:
    page = html.unescape(re.sub(r"<[^>]+>", " ", read_upstream("rfc7240-errata.html")))
    entries = " ".join(page.split()).split("Errata-ID: ")[1:]
    return {entry.split()[0]: entry for entry in entries}


def test_the_errata_this_library_follows_have_the_status_it_claims() -> None:
    errata = _errata()
    assert set(errata) == {"4439", "4316", "4625", "4955", "5282", "4317"}
    statuses = {key: entry.split("Status: ", 1)[1].split()[0] for key, entry in errata.items()}
    assert statuses == {
        "4439": "Verified",
        "4316": "Verified",
        "4625": "Reported",
        "4955": "Reported",
        "5282": "Reported",
        "4317": "Rejected",
    }


def test_erratum_4955_prefer_lenient_names_a_preference() -> None:
    entry = _errata()["4955"]
    assert "Prefer: Lenient" in entry
    assert 'Prefer: Handling="lenient"' in entry
    assert parse("Lenient").handling is None
    assert parse('Handling="lenient"').handling == "lenient"


def test_rejected_erratum_4317_commas_separate_preferences() -> None:
    entry = _errata()["4317"]
    assert "The commas are separating multiple preferences in a single header" in entry
    for value in re.findall(r"Prefer: ([^P]+?)(?= Prefer:| It should say)", entry):
        assert len(parse(value.strip(), strict=True)) == value.count(",") + 1, value
