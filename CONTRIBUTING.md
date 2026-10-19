# Contributing

Thanks for taking the time. This project keeps a small, predictable shape.

## Setup

```
pip install -r requirements-dev.txt
```

## Before you open a pull request

- Keep public API in `src/preferhdr/__init__.py`; internals live in `_`-prefixed modules.
- Add a test for the behaviour you change. Tests inject time, disk and network; they
  never touch the real thing.
- Run `scripts/check.ps1` (format, lint, types, tests) and make sure it passes.
- `python scripts/fetch_upstream.py` fetches the RFC texts, the errata page and the IANA
  registry that the ground-truth tests read (they are not committed; those tests skip
  without them). `npm install --prefix tests/upstream parse-prefer-header@1.0.0` adds the
  JavaScript reference parser, `PREFERHDR_V02=<unpacked 0.2.0 wheel>` compares with the
  previous release, and `PREFERHDR_E2E=1` builds the wheel and drives the installed
  package (add `PREFERHDR_E2E_PYPI=1` to upgrade from the PyPI release in place).
- One logical change per commit, imperative subject line.

Open an issue first if the change is large or shifts the public API.
