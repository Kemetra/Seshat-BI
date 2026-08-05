"""TDD tests for S9 -- the one Phase-5 ORDER violation that is invisible to both
the static gate and the database.

The silver build order mandates junk-row filters (`WHERE col NOT IN (..., '')`)
run BEFORE the `''`->NULL conversion. Invert the two and the filter becomes DEAD:
once `''` is NULL, `NULL NOT IN (...)` evaluates to NULL, so the junk rows survive
into silver. Postgres raises nothing (the SQL is valid), and before this rule no
checker looked at construct order at all -- the migration passed `seshat check`
with every S rule reporting coverage state `evaluated`.

Fixtures are built in tmp_path (never the real repo tree) and the rule reads
comment-stripped text, so a pattern inside a `--` comment must not fire.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from seshat.core import RuleContext, Severity
from seshat.rules.sql import s9_junk_filter_before_nulling

pytestmark = pytest.mark.unit


def _write(tmp_path: Path, rel: str, content: str) -> str:
    dest = tmp_path / rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(content, encoding="utf-8")
    return rel


def _ctx(tmp_path: Path, *rels: str) -> RuleContext:
    return RuleContext(repo_root=tmp_path, tracked_files=tuple(rels))


def test_s9_flags_junk_filter_after_nulling(tmp_path: Path) -> None:
    rel = _write(
        tmp_path,
        "warehouse/migrations/0001_silver.sql",
        "CREATE TABLE silver.s AS\n"
        "WITH nulled AS (\n"
        "  SELECT NULLIF(trim(category), '') AS category FROM bronze.b\n"
        ")\n"
        "SELECT category FROM nulled WHERE category NOT IN ('JUNK_A', '');\n",
    )
    findings = list(s9_junk_filter_before_nulling(_ctx(tmp_path, rel)))
    assert len(findings) == 1, (
        f"a junk filter running after ''->NULL is dead and must flag, got: {findings}"
    )
    f = findings[0]
    assert f.rule_id == "S9"
    assert f.severity is Severity.WARNING
    assert "category" in f.message
    assert f.locator.endswith(":5"), (
        f"the locator must point at the dead filter's line, got: {f.locator}"
    )


def test_s9_clean_when_junk_filter_precedes_nulling(tmp_path: Path) -> None:
    # The MANDATED order: filter first (while '' still matches), then null.
    rel = _write(
        tmp_path,
        "warehouse/migrations/0001_silver.sql",
        "CREATE TABLE silver.s AS\n"
        "WITH filtered AS (\n"
        "  SELECT category FROM bronze.b WHERE category NOT IN ('JUNK_A', '')\n"
        ")\n"
        "SELECT NULLIF(trim(category), '') AS category FROM filtered;\n",
    )
    findings = list(s9_junk_filter_before_nulling(_ctx(tmp_path, rel)))
    assert findings == [], f"the correct order must be clean, got: {findings}"


def test_s9_clean_when_filter_does_not_target_the_empty_string(tmp_path: Path) -> None:
    # A filter listing only real junk values is not made dead by ''->NULL --
    # a NULL category simply is not one of the listed values either way.
    rel = _write(
        tmp_path,
        "warehouse/migrations/0001_silver.sql",
        "SELECT NULLIF(trim(category), '') AS category FROM bronze.b\n"
        "WHERE category NOT IN ('JUNK_A', 'JUNK_B');\n",
    )
    findings = list(s9_junk_filter_before_nulling(_ctx(tmp_path, rel)))
    assert findings == [], (
        f"no empty-string element means the filter is not dead, got: {findings}"
    )


def test_s9_clean_when_filter_targets_a_different_column(tmp_path: Path) -> None:
    rel = _write(
        tmp_path,
        "warehouse/migrations/0001_silver.sql",
        "SELECT NULLIF(trim(category), '') AS category FROM bronze.b\n"
        "WHERE payment_method NOT IN ('JUNK_A', '');\n",
    )
    findings = list(s9_junk_filter_before_nulling(_ctx(tmp_path, rel)))
    assert findings == [], (
        f"nulling category cannot kill a filter on payment_method, got: {findings}"
    )


def test_s9_ignores_a_commented_out_filter(tmp_path: Path) -> None:
    rel = _write(
        tmp_path,
        "warehouse/migrations/0001_silver.sql",
        "SELECT NULLIF(trim(category), '') AS category FROM bronze.b;\n"
        "-- WHERE category NOT IN ('JUNK_A', '')  (dropped: profile found no junk)\n",
    )
    findings = list(s9_junk_filter_before_nulling(_ctx(tmp_path, rel)))
    assert findings == [], (
        f"a filter inside a -- comment is not code and must not fire, got: {findings}"
    )


def test_s9_exempts_test_fixtures(tmp_path: Path) -> None:
    rel = _write(
        tmp_path,
        "tests/fixtures/bad.sql",
        "SELECT NULLIF(trim(category), '') AS category FROM bronze.b\n"
        "WHERE category NOT IN ('JUNK_A', '');\n",
    )
    findings = list(s9_junk_filter_before_nulling(_ctx(tmp_path, rel)))
    assert findings == [], "tests/ fixtures are exempt from the live scan"
