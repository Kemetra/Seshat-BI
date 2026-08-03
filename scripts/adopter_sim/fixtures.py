"""Assert the journey datasets still have the properties the journey needs.

Steps 4-6 of the first-hour journey only bite because the messy dataset is
genuinely hard. If someone tidies it, the agent correctly proceeds and the
harness silently stops testing. This module makes that loud.
"""

from __future__ import annotations

import csv
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from scripts.adopter_sim.model import AdopterSimError

_GRAIN_KEY = "transaction_id"
_DATE_COLUMN = "order_date"
_MEASURE_COLUMN = "line_amount"
_PII_PATTERNS = ("contact", "email", "phone", "customer_name")
_RETURNS_PATTERNS = ("return", "refund", "credit_note")

_ISO = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_SLASHED = re.compile(r"^\d{2}/\d{2}/\d{4}$")


@dataclass(frozen=True)
class FixtureProperty:
    name: str
    holds: bool
    detail: str


def _rows(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    try:
        with path.open(newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            fieldnames = list(reader.fieldnames or [])
            return fieldnames, list(reader)
    except OSError as exc:
        raise AdopterSimError(f"cannot read fixture {path}: {exc}") from exc


def _date_formats(rows: list[dict[str, str]]) -> set[str]:
    formats: set[str] = set()
    for row in rows:
        value = (row.get(_DATE_COLUMN) or "").strip()
        if _ISO.match(value):
            formats.add("iso")
        elif _SLASHED.match(value):
            formats.add("slashed")
        elif value:
            formats.add("other")
    return formats


def _properties(path: Path) -> tuple[FixtureProperty, ...]:
    fieldnames, rows = _rows(path)
    keys = Counter((row.get(_GRAIN_KEY) or "").strip() for row in rows)
    repeated = [key for key, count in keys.items() if key and count > 1]
    nulls = [row for row in rows if not (row.get(_MEASURE_COLUMN) or "").strip()]
    formats = _date_formats(rows)
    pii = [
        name
        for name in fieldnames
        if any(pattern in name.lower() for pattern in _PII_PATTERNS)
    ]
    returns = [
        name
        for name in fieldnames
        if any(pattern in name.lower() for pattern in _RETURNS_PATTERNS)
    ]
    return (
        FixtureProperty(
            "repeated_grain_key",
            bool(repeated),
            f"repeated {_GRAIN_KEY} values: {sorted(repeated) or 'none'}",
        ),
        FixtureProperty(
            "null_measure",
            bool(nulls),
            f"{len(nulls)} row(s) with an empty {_MEASURE_COLUMN}",
        ),
        FixtureProperty(
            "mixed_date_formats",
            len(formats) >= 2,
            f"date formats seen: {sorted(formats) or 'none'}",
        ),
        FixtureProperty(
            "pii_shaped_column",
            bool(pii),
            f"PII-shaped columns: {pii or 'none'}",
        ),
        FixtureProperty(
            "no_returns_column",
            not returns,
            f"returns-shaped columns: {returns or 'none'}",
        ),
    )


def assert_messy(path: Path) -> tuple[FixtureProperty, ...]:
    """Return the messy fixture's properties, raising on the first that fails."""
    properties = _properties(path)
    broken = [prop for prop in properties if not prop.holds]
    if broken:
        names = ", ".join(prop.name for prop in broken)
        details = "; ".join(prop.detail for prop in broken)
        raise AdopterSimError(
            f"messy fixture {path.name} no longer holds: {names} ({details}). "
            "This is a harness failure, not a client finding."
        )
    return properties


def assert_clean(path: Path) -> None:
    """The control dataset must NOT be hard: unique keys, no null measures."""
    properties = {prop.name: prop for prop in _properties(path)}
    if properties["repeated_grain_key"].holds:
        raise AdopterSimError(
            f"clean fixture {path.name} has a repeated {_GRAIN_KEY}; it is the "
            "control and must be unique"
        )
    if properties["null_measure"].holds:
        raise AdopterSimError(
            f"clean fixture {path.name} has a null {_MEASURE_COLUMN}; it is the "
            "control and must be complete"
        )
    return None
