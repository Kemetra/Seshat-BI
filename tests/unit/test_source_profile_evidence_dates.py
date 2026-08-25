from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).parents[2]
SOURCE_TEMPLATE = ROOT / "templates" / "source-profile.md"
MAPPINGS = ROOT / "mappings"
LABELS = (
    "Primary reporting-date column",
    "Observed coverage start",
    "Observed coverage end",
    "Coverage evidence",
)


def _text(scope: str) -> str:
    return (MAPPINGS / scope / "source-profile.md").read_text(encoding="utf-8")


def _value(text: str, label: str) -> str:
    match = re.search(rf"^\|\s*{re.escape(label)}\s*\|\s*(.*?)\s*\|$", text, re.M)
    assert match is not None, f"missing reporting-date fact {label!r}"
    return match.group(1)


def test_source_profile_template_declares_reporting_date_coverage() -> None:
    text = SOURCE_TEMPLATE.read_text(encoding="utf-8")

    for label in LABELS:
        assert f"| {label} |" in text
    assert "GAP --" in text
    assert "Profiled on" in text
    assert "must not substitute" in text


def test_temporal_profiles_record_committed_coverage_facts() -> None:
    expected = {
        "demo_sample_orders": ("order_date", "2026-01-02", "2026-01-13"),
        "finance_gl_actuals": ("posting_date", "2024-01-01", "2025-12-31"),
        "retail_store_sales": ("transaction_date", "2022-01-01", "2025-01-18"),
    }

    for scope, (column, start, end) in expected.items():
        text = _text(scope)
        assert column in _value(text, "Primary reporting-date column")
        assert _value(text, "Observed coverage start") == start
        assert _value(text, "Observed coverage end") == end
        evidence = _value(text, "Coverage evidence")
        assert evidence != "GAP"
        assert "committed" in evidence.lower()


def test_quarter_grain_budget_records_calendar_date_gap() -> None:
    text = _text("finance_gl_budget")

    for label in LABELS[:3]:
        assert _value(text, label).startswith("GAP --")
    evidence = _value(text, "Coverage evidence").lower()
    assert "fiscal-quarter grain" in evidence
    assert "no calendar date column" in evidence
