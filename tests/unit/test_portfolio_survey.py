"""Contract oracle for the Layer-A portfolio survey artifact."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "portfolio-survey"
VALID_SURVEY = FIXTURES / "db-schema" / "survey.md"

REQUIRED_FIELDS = (
    "Status",
    "Source kind",
    "Source identity",
    "Reachable tables total",
    "Surveyed tables total",
)
COUNT_FIELDS = ("Reachable tables total", "Surveyed tables total")
FORBIDDEN_PATTERNS = {
    "value-backed uniqueness": r"\b(?:measured\s+)?uniqueness\s*:",
    "value-backed missingness": r"\b(?:measured\s+)?missingness\s*:",
    "measured date coverage": r"\bdate\s+coverage\s*:",
    "source sample": r"\b(?:raw|masked)?\s*sample\s*:",
    "returns population": r"\breturns(?:-column)?\s+population\s*:",
    "raw suspected PII": r"\braw\s+suspected\s+pii\s+value\s*:",
    "database URL": r"\b(?:postgres(?:ql)?|mysql|mssql|sqlserver|snowflake)://",
    "database environment variable": r"\b(?:DATABASE_URL|ANALYTICS_DB_[A-Z0-9_]+)\s*=",
}


def validate_portfolio_survey(text: str) -> list[str]:
    """Return contract violations for a filled portfolio survey."""
    values, violations = _required_values(text)
    violations.extend(_count_violations(text, values))
    violations.extend(_forbidden_violations(text))
    return violations


def _required_values(text: str) -> tuple[dict[str, str], list[str]]:
    values: dict[str, str] = {}
    violations: list[str] = []
    for field in REQUIRED_FIELDS:
        match = re.search(rf"^\*\*{re.escape(field)}\*\*:\s*(.+)$", text, re.MULTILINE)
        if match is None:
            violations.append(f"missing required field: {field}")
        else:
            values[field] = match.group(1).strip()
    return values, violations


def _count_violations(text: str, values: dict[str, str]) -> list[str]:
    table_count = len(re.findall(r"^## Table:\s+\S", text, re.MULTILINE))
    candidates = (
        _count_violation(field, values.get(field), table_count)
        for field in COUNT_FIELDS
    )
    return [violation for violation in candidates if violation is not None]


def _count_violation(field: str, value: str | None, table_count: int) -> str | None:
    if value is None:
        return None
    try:
        declared_count = int(value)
    except ValueError:
        return f"{field} must be an integer"
    if declared_count == table_count:
        return None
    return f"{field} declares {declared_count}, but {table_count} table sections exist"


def _forbidden_violations(text: str) -> list[str]:
    return [
        f"forbidden {label}"
        for label, pattern in FORBIDDEN_PATTERNS.items()
        if re.search(pattern, text, re.IGNORECASE)
    ]


def test_valid_survey_parses() -> None:
    text = VALID_SURVEY.read_text(encoding="utf-8")
    assert validate_portfolio_survey(text) == []


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
    text = VALID_SURVEY.read_text(encoding="utf-8")
    assert validate_portfolio_survey(text + "\n" + forbidden)


def test_silently_omitted_reachable_table_fails_closed() -> None:
    text = VALID_SURVEY.read_text(encoding="utf-8").replace(
        "**Reachable tables total**: 5", "**Reachable tables total**: 6"
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
