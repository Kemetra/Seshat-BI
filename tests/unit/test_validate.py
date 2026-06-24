"""TDD tests for the retail validate live-validator surface (feature 004).

The four live checks are driver-free: they run against a QueryRunner Protocol
(`run(sql, params) -> list[tuple]`), so a tiny fake runner exercises them with
no database and no psycopg2. The whole suite runs with psycopg2 ABSENT (dev deps
carry no driver) -- that the tests pass at all is the proof the logic is
driver-free.

Live findings are Severity.ERROR (proven defects), unlike the static rules'
WARNING (suspect patterns).
"""

from __future__ import annotations

import pytest

from retail.core import Severity
from retail.validate import (
    DateCoverageTarget,
    OrphanTarget,
    PkTarget,
    ReconcileTarget,
    check_date_coverage,
    check_orphan_fks,
    check_pk_uniqueness,
    check_reconciliation,
)

pytestmark = pytest.mark.unit


class FakeRunner:
    """A QueryRunner whose results are scripted per-call (FIFO).

    Each entry in `results` is the row list returned by the next `run(...)`.
    Records the SQL it was asked to run for optional assertion.
    """

    def __init__(self, results: list[list[tuple]]) -> None:
        self._results = list(results)
        self.calls: list[str] = []

    def run(self, sql: str, params: tuple = ()) -> list[tuple]:
        self.calls.append(sql)
        return self._results.pop(0) if self._results else []


# ---------------------------------------------------------------------------
# PK uniqueness (RC2)
# ---------------------------------------------------------------------------


def test_pk_uniqueness_clean() -> None:
    # rows == distinct == 246916, 0 null -> no finding
    runner = FakeRunner([[(246916, 246916, 0)]])
    target = PkTarget(table="silver.sales_c086", pk_columns=("invoice_no", "line_no"))
    findings = list(check_pk_uniqueness(runner, target))
    assert findings == []


def test_pk_uniqueness_duplicate_is_error() -> None:
    runner = FakeRunner([[(246916, 246900, 0)]])  # 16 dupes
    target = PkTarget(table="silver.sales_c086", pk_columns=("invoice_no", "line_no"))
    findings = list(check_pk_uniqueness(runner, target))
    assert len(findings) == 1
    assert findings[0].severity == Severity.ERROR
    assert "RC2" in findings[0].message


def test_pk_uniqueness_null_pk_is_error() -> None:
    runner = FakeRunner([[(246916, 246916, 5)]])  # 5 null pk
    target = PkTarget(table="silver.sales_c086", pk_columns=("invoice_no", "line_no"))
    findings = list(check_pk_uniqueness(runner, target))
    assert len(findings) == 1
    assert findings[0].severity == Severity.ERROR


# ---------------------------------------------------------------------------
# Date coverage (RC15 live half)
# ---------------------------------------------------------------------------


def test_date_coverage_clean() -> None:
    runner = FakeRunner([[(0,)]])  # 0 fact dates missing from dim_date
    target = DateCoverageTarget(
        fact="gold.fct_sales",
        fact_date="sale_date",
        date_dim="gold.dim_date",
        dim_date="full_date",
    )
    findings = list(check_date_coverage(runner, target))
    assert findings == []


def test_date_coverage_gap_is_error() -> None:
    runner = FakeRunner([[(2,)]])  # 2 fact dates missing
    target = DateCoverageTarget(
        fact="gold.fct_sales",
        fact_date="sale_date",
        date_dim="gold.dim_date",
        dim_date="full_date",
    )
    findings = list(check_date_coverage(runner, target))
    assert len(findings) == 1
    assert findings[0].severity == Severity.ERROR
    assert "RC15" in findings[0].message
    assert "2" in findings[0].message


# ---------------------------------------------------------------------------
# Orphan FKs (RC16)
# ---------------------------------------------------------------------------


def test_orphan_fks_clean() -> None:
    # one query per FK, each returns 0 orphans
    runner = FakeRunner([[(0,)], [(0,)]])
    target = OrphanTarget(
        fact="gold.fct_sales",
        fks=(
            ("product_sk", "gold.dim_product", "product_sk"),
            ("customer_sk", "gold.dim_customer", "customer_sk"),
        ),
    )
    findings = list(check_orphan_fks(runner, target))
    assert findings == []


def test_orphan_fks_defect_is_error_per_fk() -> None:
    runner = FakeRunner([[(0,)], [(7,)]])  # second FK has 7 orphans
    target = OrphanTarget(
        fact="gold.fct_sales",
        fks=(
            ("product_sk", "gold.dim_product", "product_sk"),
            ("customer_sk", "gold.dim_customer", "customer_sk"),
        ),
    )
    findings = list(check_orphan_fks(runner, target))
    assert len(findings) == 1
    assert findings[0].severity == Severity.ERROR
    assert "RC16" in findings[0].message
    assert "customer_sk" in findings[0].message


# ---------------------------------------------------------------------------
# Cross-layer reconciliation (RC16)
# ---------------------------------------------------------------------------


def test_reconciliation_clean_penny_exact() -> None:
    # one query per measure: returns (silver_total, gold_total)
    runner = FakeRunner([[("38804001.54", "38804001.54")]])
    target = ReconcileTarget(
        silver="silver.sales_c086",
        gold="gold.fct_sales",
        measures=("sales_amount",),
    )
    findings = list(check_reconciliation(runner, target))
    assert findings == []


def test_reconciliation_mismatch_is_error() -> None:
    runner = FakeRunner([[("38804001.54", "38804000.00")]])  # 1.54 gap
    target = ReconcileTarget(
        silver="silver.sales_c086",
        gold="gold.fct_sales",
        measures=("sales_amount",),
    )
    findings = list(check_reconciliation(runner, target))
    assert len(findings) == 1
    assert findings[0].severity == Severity.ERROR
    assert "RC16" in findings[0].message
    assert "sales_amount" in findings[0].message


def test_reconciliation_null_total_is_error_not_crash() -> None:
    runner = FakeRunner([[(None, "100.00")]])  # silver total NULL
    target = ReconcileTarget(
        silver="silver.sales_c086",
        gold="gold.fct_sales",
        measures=("sales_amount",),
    )
    findings = list(check_reconciliation(runner, target))
    assert len(findings) == 1
    assert findings[0].severity == Severity.ERROR


# ---------------------------------------------------------------------------
# Driver-free guard: importing validate + cli must not require psycopg2
# ---------------------------------------------------------------------------


def test_resolve_dsn_prefers_database_url() -> None:
    from retail.validate import resolve_dsn

    env = {"DATABASE_URL": "postgresql://u:p@somehost:5432/db?sslmode=require"}
    dsn = resolve_dsn(env)
    assert dsn == "postgresql://u:p@somehost:5432/db?sslmode=require"


def test_resolve_dsn_builds_from_analytics_db_parts() -> None:
    from retail.validate import resolve_dsn

    env = {
        "ANALYTICS_DB_HOST": "local.example",
        "ANALYTICS_DB_PORT": "5432",
        "ANALYTICS_DB_NAME": "warehouse",
        "ANALYTICS_DB_USER": "reader",
        "ANALYTICS_DB_PASSWORD": "secret",
        "ANALYTICS_DB_SSLMODE": "require",
    }
    dsn = resolve_dsn(env)
    # any provider/host -> a standard postgres DSN; host-agnostic by construction
    assert dsn.startswith("postgresql://reader:")
    assert "@local.example:5432/warehouse" in dsn
    assert "sslmode=require" in dsn


def test_resolve_dsn_local_no_ssl_no_password() -> None:
    from retail.validate import resolve_dsn

    # a local DB: no password, no sslmode -> still a valid DSN
    env = {
        "ANALYTICS_DB_HOST": "localhost",
        "ANALYTICS_DB_NAME": "dev",
        "ANALYTICS_DB_USER": "me",
    }
    dsn = resolve_dsn(env)
    assert "@localhost" in dsn and "/dev" in dsn and dsn.startswith("postgresql://me")


def test_resolve_dsn_missing_config_returns_none() -> None:
    from retail.validate import resolve_dsn

    # no DATABASE_URL and no host -> cannot resolve -> None (handler errors clearly)
    assert resolve_dsn({}) is None


def test_validate_imports_without_psycopg2() -> None:
    import importlib

    # If psycopg2 were imported at module scope, this would already have failed
    # at the top-of-file `from retail.validate import ...`. Re-import explicitly
    # to lock the contract.
    mod = importlib.import_module("retail.validate")
    assert hasattr(mod, "check_pk_uniqueness")


def test_cli_imports_without_psycopg2() -> None:
    import importlib

    cli = importlib.import_module("retail.cli")
    assert hasattr(cli, "main")
    # The validate subcommand must be registered without importing a DB driver.
    parser = cli._build_parser()
    # argparse exposes subparsers via choices on the subparsers action.
    sub_actions = [a for a in parser._actions if hasattr(a, "choices") and a.choices]
    commands = set()
    for a in sub_actions:
        commands.update(a.choices.keys())
    assert "validate" in commands
    assert "check" in commands


# ---------------------------------------------------------------------------
# run_live_checks: the pure aggregator that runs all four checks against a
# runner + a ValidationTargets bundle (driver-free; fake runner).
# ---------------------------------------------------------------------------


def _clean_targets():
    return (
        PkTarget(table="silver.t", pk_columns=("a", "b")),
        DateCoverageTarget(
            fact="gold.f",
            fact_date="date_sk",
            date_dim="gold.dim_date",
            dim_date="date_sk",
        ),
        OrphanTarget(
            fact="gold.f", fks=(("product_sk", "gold.dim_product", "product_sk"),)
        ),
        ReconcileTarget(silver="silver.t", gold="gold.f", measures=("amt",)),
    )


def test_run_live_checks_all_clean_returns_no_findings() -> None:
    from retail.validate import ValidationTargets, run_live_checks

    pk, dc, orph, rec = _clean_targets()
    targets = ValidationTargets(pk=pk, date_coverage=dc, orphans=orph, reconcile=rec)
    # FIFO: pk(count,distinct,null) -> coverage(missing) -> orphan(count) -> recon(s,g)
    runner = FakeRunner([[(10, 10, 0)], [(0,)], [(0,)], [("5.00", "5.00")]])
    findings = run_live_checks(runner, targets)
    assert findings == []


def test_run_live_checks_aggregates_findings_across_checks() -> None:
    from retail.validate import ValidationTargets, run_live_checks

    pk, dc, orph, rec = _clean_targets()
    targets = ValidationTargets(pk=pk, date_coverage=dc, orphans=orph, reconcile=rec)
    # a PK dup AND an orphan -> two ERROR findings from two different checks
    runner = FakeRunner([[(10, 9, 0)], [(0,)], [(3,)], [("5.00", "5.00")]])
    findings = run_live_checks(runner, targets)
    assert len(findings) == 2
    rule_ids = {f.rule_id for f in findings}
    assert rule_ids == {"V-RC2", "V-RC16"}
    assert all(f.severity == Severity.ERROR for f in findings)
