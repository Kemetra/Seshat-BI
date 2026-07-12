"""Contract oracle for the Layer-A portfolio survey artifact."""

from __future__ import annotations

from pathlib import Path
import re

import pytest


FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "portfolio-survey"


def validate_portfolio_survey(text: str) -> list[str]:
    """Return contract violations for a filled portfolio survey."""
    violations: list[str] = []
    required_fields = (
        "Status",
        "Source kind",
        "Source identity",
        "Reachable tables total",
        "Surveyed tables total",
    )
    values: dict[str, str] = {}
    for field in required_fields:
        match = re.search(rf"^\*\*{re.escape(field)}\*\*:\s*(.+)$", text, re.MULTILINE)
        if match is None:
            violations.append(f"missing required field: {field}")
        else:
            values[field] = match.group(1).strip()

    table_count = len(re.findall(r"^## Table:\s+\S", text, re.MULTILINE))
    for field in ("Reachable tables total", "Surveyed tables total"):
        if field not in values:
            continue
        try:
            declared_count = int(values[field])
        except ValueError:
            violations.append(f"{field} must be an integer")
            continue
        if declared_count != table_count:
            violations.append(
                f"{field} declares {declared_count}, but {table_count} table sections exist"
            )

    forbidden_patterns = {
        "value-backed uniqueness": r"\b(?:measured\s+)?uniqueness\s*:",
        "value-backed missingness": r"\b(?:measured\s+)?missingness\s*:",
        "measured date coverage": r"\bdate\s+coverage\s*:",
        "source sample": r"\b(?:raw|masked)?\s*sample\s*:",
        "returns population": r"\breturns(?:-column)?\s+population\s*:",
        "raw suspected PII": r"\braw\s+suspected\s+pii\s+value\s*:",
        "database URL": r"\b(?:postgres(?:ql)?|mysql|mssql|sqlserver|snowflake)://",
        "database environment variable": r"\b(?:DATABASE_URL|ANALYTICS_DB_[A-Z0-9_]+)\s*=",
    }
    for label, pattern in forbidden_patterns.items():
        if re.search(pattern, text, re.IGNORECASE):
            violations.append(f"forbidden {label}")

    return violations


def _valid_survey() -> str:
    return """# Portfolio Survey: synthetic

**Status**: warning
**Source kind**: db-schema
**Source identity**: analytics
**Reachable tables total**: 1
**Surveyed tables total**: 1

## Coverage limits
- none

## Candidate domain evidence
- order-shaped column names suggest sales; hint only

## Candidate first-scope tables
- analytics.orders because metadata declares an order identifier

## Table: analytics.orders
**Columns**:
| Column | Declared type |
|--------|---------------|
| order_id | bigint |
**Declared PK**: order_id (declared metadata; candidate only)
**Declared FKs**: none declared
**Candidate grain hint**: one row per order_id (unverified metadata hint)
**Approx row count**: [PENDING LIVE PROFILE] estimate unavailable: permission denied
**Date hints**: order_date name/type hint only
**PII suspicion hints**: customer_email name hint; no values inspected
**Structural role hint**: candidate fact
**Unavailable**: approximate row count: permission denied; grant metadata permission
"""


def test_valid_survey_parses() -> None:
    assert validate_portfolio_survey(_valid_survey()) == []


@pytest.mark.parametrize(
    "forbidden",
    [
        "measured uniqueness: 99.9%",
        "measured missingness: 3%",
        "date coverage: 2024-01-01 to 2024-12-31",
        "masked sample: a***@example.com",
        "returns population: 42 rows",
        "postgresql://user:secret@db.example/retail",
        "DATABASE_URL=postgresql://user:secret@db/retail",
        "raw suspected PII value: alice@example.com",
    ],
)
def test_value_measurement_or_secret_fails_closed(forbidden: str) -> None:
    assert validate_portfolio_survey(_valid_survey() + "\n" + forbidden)


def test_silently_omitted_reachable_table_fails_closed() -> None:
    text = _valid_survey().replace(
        "**Reachable tables total**: 1", "**Reachable tables total**: 2"
    )
    assert validate_portfolio_survey(text)


@pytest.mark.parametrize(
    "fixture",
    [
        FIXTURES / "db-schema" / "survey.md",
        FIXTURES / "file-folder" / "survey.md",
    ],
)
def test_golden_surveys_satisfy_metadata_only_contract(fixture: Path) -> None:
    text = fixture.read_text(encoding="utf-8")
    assert validate_portfolio_survey(text) == []
    assert "hint" in text.lower()
    assert "ruling" not in text.lower()
    if "[PENDING LIVE PROFILE]" in text:
        assert "Unavailable" in text
