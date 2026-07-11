"""Discriminating integration test: the multi-engine dialect must actually reach
the CLI's live SQL, not just exist as a tested-in-isolation fragment.

CONFIRMED DEFECT (final whole-branch review): `_run_validate` and
`_run_value_check` computed the active engine's ``dialect`` but never passed it
to ``run_live_checks`` / ``check_expected_value`` -- both defaulted silently to
Postgres, so setting ``ANALYTICS_DB_ENGINE=sqlserver`` still emitted Postgres SQL
(``FILTER (WHERE ...)``, ``count(DISTINCT (...))``, double-quoted identifiers) at
the real CLI call sites. test_dialect.py alone could never catch this: it only
exercises Dialect methods directly, never the CLI wiring that is supposed to
thread ``dialect`` through.

This test sets ``ANALYTICS_DB_ENGINE=sqlserver``, monkeypatches the same seams
test_cli_context.py / test_cli_value_check.py already use (``_make_runner``,
``_load_targets``, ``_ensure_driver``), and asserts the SQL a fake runner
actually receives is in SQL-Server dialect -- not Postgres.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from seshat.cli import _safe_target_label
from seshat.cli import main as main_under_test

pytestmark = pytest.mark.unit


def _setup_sqlserver_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ANALYTICS_DB_ENGINE", "sqlserver")
    monkeypatch.setenv("ANALYTICS_DB_HOST", "sqlhost")
    monkeypatch.setenv("ANALYTICS_DB_USER", "svc")
    monkeypatch.setenv("ANALYTICS_DB_PASSWORD", "hunter2")
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setattr("seshat.cli._ensure_driver", lambda: True)


def test_safe_target_label_sqlserver_odbc_string_never_echoes_credentials() -> None:
    """CONFIRMED DEFECT (advisor-flagged, adjacent to R4): `_safe_target_label`
    special-cased "a string config" as "a Postgres DSN, split on '@'", but the
    SQL-Server ODBC keyword string is ALSO a bare string with no '@' delimiter
    -- so the pre-fix code returned the config UNCHANGED, printing
    `PWD={...}`/`UID={...}` verbatim on the "running against ..." status line.
    Non-Postgres string configs must fall back to the engine-only label (same
    posture already used for the MySQL/Snowflake kwargs-dict configs)."""
    odbc = (
        "DRIVER={ODBC Driver 18 for SQL Server};SERVER=h,1433;"
        "UID={svc};PWD={hunter2};Encrypt=yes"
    )
    label = _safe_target_label("sqlserver", odbc)
    assert "hunter2" not in label
    assert "PWD=" not in label
    assert "UID=" not in label
    assert label == "sqlserver"


def test_safe_target_label_postgres_dsn_unchanged() -> None:
    # Regression guard: the Postgres DSN behavior (host-only label) is UNCHANGED.
    assert _safe_target_label("postgres", "postgresql://u:p@h:5432/db") == "h:5432/db"
    assert _safe_target_label("postgres", "postgresql://h:5432/db") == (
        "postgresql://h:5432/db"
    )


def test_validate_sqlserver_engine_emits_sqlserver_sql_not_postgres(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """`retail validate` with ANALYTICS_DB_ENGINE=sqlserver must generate
    SQL-Server-dialect SQL (bracket-quoted identifiers, COUNT(CASE WHEN...))
    at the real runner call site, not Postgres SQL (double-quote identifiers,
    FILTER (WHERE ...), count(DISTINCT (...)))."""
    _setup_sqlserver_env(monkeypatch)

    from seshat.validate import (
        DateCoverageTarget,
        OrphanTarget,
        PkTarget,
        ReconcileTarget,
        ValidationTargets,
    )

    fake_targets = ValidationTargets(
        pk=PkTarget(table="silver.t", pk_columns=("a",)),
        date_coverage=DateCoverageTarget(
            fact="gold.f",
            fact_date="date_sk",
            date_dim="gold.dim_date",
            dim_date="date_sk",
        ),
        orphans=OrphanTarget(fact="gold.f", fks=()),
        reconcile=ReconcileTarget(silver="silver.t", gold="gold.f", measures=()),
    )
    monkeypatch.setattr("seshat.cli._load_targets", lambda path: fake_targets)

    captured_sql: list[str] = []

    class FakeRunner:
        def run(self, sql: str, params: tuple = ()) -> list[tuple]:
            captured_sql.append(sql)
            if "(SELECT COUNT(*) FROM (SELECT DISTINCT" in sql:
                return [(5, 5, 0)]
            return [(0,)]

    monkeypatch.setattr("seshat.cli._make_runner", lambda config: FakeRunner())

    rc = main_under_test(["validate", "--source-map", "mappings/t/source-map.yaml"])
    assert rc == 0
    assert captured_sql

    joined = " ".join(captured_sql)
    # Discriminating positive assertions: SQL-Server-only forms.
    assert "COUNT(CASE" in joined
    assert "[" in joined
    # Discriminating negative assertions: these are the Postgres-only forms
    # that leaked out when the dialect wasn't threaded through.
    assert "FILTER (WHERE" not in joined
    assert "count(DISTINCT (" not in joined

    # Adjacent credential-leak guard: the "running against ..." status line
    # (printed via _safe_target_label) must never echo the ODBC PWD=/UID=.
    err = capsys.readouterr().err
    assert "hunter2" not in err


_RATIO_CONTRACT = """\
name: "DiscountedTransactionRate"
binds_to:
  gold_table: "gold.fct_sales_rss"
  columns: ["discount_applied"]
definition:
  additive: false
  numerator:
    aggregation: count_rows
    filter:
      - column: discount_applied
        op: is_true
  denominator:
    aggregation: count_rows
    filter:
      - column: discount_applied
        op: is_not_null
  expected_value:
    value: "0.5037"
    tolerance_abs: "0.0001"
    aggregation: ratio
"""


def _write_contract(metrics_dir: Path, name: str, body: str) -> None:
    d = metrics_dir / "retail_store_sales" / "metrics"
    d.mkdir(parents=True, exist_ok=True)
    (d / f"{name}.yaml").write_text(body, encoding="utf-8")


def test_value_check_sqlserver_engine_emits_sqlserver_sql_not_postgres(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """`retail value-check` with ANALYTICS_DB_ENGINE=sqlserver must generate
    SQL-Server-dialect SQL for the ratio numerator/denominator filters built
    via `_filter_to_sql` -- bracket-quoted identifiers, not the hardcoded
    Postgres double-quote form from `seshat.identifiers.quote_identifier`
    (FIX 4: the ratio-filter quoter must be dialect-aware)."""
    _setup_sqlserver_env(monkeypatch)
    _write_contract(tmp_path, "DiscountedTransactionRate", _RATIO_CONTRACT)

    captured_sql: list[str] = []

    class FakeRunner:
        def run(self, sql: str, params: tuple = ()) -> list[tuple]:
            captured_sql.append(sql)
            if "IS NOT NULL" in sql:
                return [(8376,)]
            return [(4219,)]

    monkeypatch.setattr("seshat.cli._make_runner", lambda config: FakeRunner())

    rc = main_under_test(
        ["value-check", "--repo", str(tmp_path), "--metrics-dir", str(tmp_path)]
    )
    assert rc == 0
    assert captured_sql

    joined = " ".join(captured_sql)
    assert "[discount_applied]" in joined
    assert '"discount_applied"' not in joined
    # Pin Fix 3 (check_expected_value dialect threading): the GOLD TABLE itself
    # must be bracket-quoted by the SqlServer dialect, not ANSI double-quoted by
    # the Postgres fallback. Without dialect=dialect at the call site, the table
    # would render "gold"."fct_sales_rss" (Postgres) even though the filter
    # column is bracketed -- a mixed-dialect statement. This assertion fails if
    # Fix 3 is reverted, closing the coverage gap the final review flagged.
    assert "[gold].[fct_sales_rss]" in joined
    assert '"gold"."fct_sales_rss"' not in joined

    err = capsys.readouterr().err
    assert "hunter2" not in err


def test_validate_postgres_engine_unchanged(monkeypatch: pytest.MonkeyPatch) -> None:
    """Regression guard: engine unset (default postgres) must stay byte-identical
    -- FILTER (WHERE ...), count(DISTINCT (...)), double-quoted identifiers."""
    monkeypatch.delenv("ANALYTICS_DB_ENGINE", raising=False)
    monkeypatch.setenv("DATABASE_URL", "postgresql://u:p@h:5432/db")
    monkeypatch.setattr("seshat.cli._ensure_driver", lambda: True)

    from seshat.validate import (
        DateCoverageTarget,
        OrphanTarget,
        PkTarget,
        ReconcileTarget,
        ValidationTargets,
    )

    fake_targets = ValidationTargets(
        pk=PkTarget(table="silver.t", pk_columns=("a",)),
        date_coverage=DateCoverageTarget(
            fact="gold.f",
            fact_date="date_sk",
            date_dim="gold.dim_date",
            dim_date="date_sk",
        ),
        orphans=OrphanTarget(fact="gold.f", fks=()),
        reconcile=ReconcileTarget(silver="silver.t", gold="gold.f", measures=()),
    )
    monkeypatch.setattr("seshat.cli._load_targets", lambda path: fake_targets)

    captured_sql: list[str] = []

    class FakeRunner:
        def run(self, sql: str, params: tuple = ()) -> list[tuple]:
            captured_sql.append(sql)
            if "DISTINCT (a)" in sql or "count(DISTINCT" in sql:
                return [(5, 5, 0)]
            return [(0,)]

    monkeypatch.setattr("seshat.cli._make_runner", lambda dsn: FakeRunner())

    rc = main_under_test(["validate", "--source-map", "mappings/t/source-map.yaml"])
    assert rc == 0
    joined = " ".join(captured_sql)
    assert "FILTER (WHERE" in joined
    assert "count(DISTINCT (" in joined
    assert '"a"' in joined
