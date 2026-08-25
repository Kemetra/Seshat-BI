from __future__ import annotations

import re
from pathlib import Path

import pytest


ROOT = Path(__file__).parents[2]
SUMMARY = ROOT / "templates" / "handoff" / "answerability-summary.md"
PUBLISH_READY = ROOT / "docs" / "readiness" / "publish-ready.md"


def _section(name: str) -> str:
    text = SUMMARY.read_text(encoding="utf-8")
    match = re.search(
        rf"^## {re.escape(name)}\s*$\n(.*?)(?=^## |\Z)",
        text,
        re.M | re.S,
    )
    assert match is not None, f"missing section {name!r}"
    return match.group(1)


def test_answerability_summary_names_three_authoritative_dates() -> None:
    section = _section("Evidence dates")

    assert section.count("| **") == 3
    assert "Observed coverage end" in section
    assert "last_checked_at" in section
    assert "stage: publish_ready" in section
    assert "GAP --" in section
    assert "calendar days" in section


@pytest.mark.parametrize(
    "token",
    (
        "fresh",
        "stale",
        "current",
        "outdated",
        "acceptable",
        "unacceptable",
        "confidence",
        "health score",
    ),
)
def test_evidence_dates_section_has_no_age_judgment(token: str) -> None:
    assert token not in _section("Evidence dates").lower()


def test_evidence_dates_section_is_generic() -> None:
    section = _section("Evidence dates")

    assert "c086" not in section.lower()
    assert "retail_store_sales" not in section.lower()
    assert re.search(r"\b20\d{2}-\d{2}-\d{2}\b", section) is None


def test_gap_suppresses_dependent_calendar_arithmetic() -> None:
    section = _section("Evidence dates")

    assert "omit its dependent arithmetic" in section
    assert "cannot calculate <named difference>" in section
    assert "absent or malformed" in section


def test_publish_ready_routes_each_evidence_date_to_its_authority() -> None:
    text = PUBLISH_READY.read_text(encoding="utf-8")

    assert "Observed coverage end" in text
    assert "last_checked_at" in text
    assert "publish_ready" in text
    assert "optional" in text.lower()
    assert "does not change" in text.lower()
