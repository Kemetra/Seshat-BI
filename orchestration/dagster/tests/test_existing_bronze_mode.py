"""#404/#405: non-destructive existing-Bronze source mode (in-process).

The load-bearing proof: with SESHAT_DAGSTER_SOURCE_MODE=existing-bronze the
ingest head verifies a pre-loaded ``bronze.<table>`` READ-ONLY. It issues ZERO
Bronze DDL/DML (``load_csv`` never runs), ``raw_source_file`` records
``deferred`` (not a STOP edge), the gated tail proceeds, and a mismatched /
absent / empty relation fails closed with a named blocker.

Mirrors ``test_migrations_unchanged.py``: destructive ``db`` helpers are
monkeypatched to append to a list; the test asserts that list stays ``[]``.
"""

from __future__ import annotations

import pytest
from conftest import TABLE, make_fixture_repo
from dagster import materialize
from tower_bi_orchestration import commands, db
from tower_bi_orchestration.assets import build_table_assets
from tower_bi_orchestration.evidence_writer import (
    EvidenceWriter,
    RunMeta,
    finalize_run,
)
from tower_bi_orchestration.jobs import THROUGH_GOLD_ASSETS

RUN_ID = "testrun-001"


@pytest.fixture
def db_first_repo(tmp_path, monkeypatch):
    """A green fixture repo scoped to existing-bronze mode."""
    root = make_fixture_repo(tmp_path)
    monkeypatch.setenv("SESHAT_REPO_ROOT", str(root))
    monkeypatch.setenv("SESHAT_DAGSTER_RUN_ID", RUN_ID)
    monkeypatch.setenv("SESHAT_DAGSTER_SOURCE_MODE", "existing-bronze")
    monkeypatch.delenv("SESHAT_DAGSTER_TABLES", raising=False)
    monkeypatch.delenv("SESHAT_RAW_LANDING_DIR", raising=False)
    return root


def _forbid_bronze_writes(monkeypatch) -> list:
    """Record any call to the ONE Bronze-writing helper, ``load_csv``.

    #405's guarantee is "zero BRONZE DDL/DML": ``load_csv`` is the only helper
    that drops/creates/reloads ``bronze.<table>``. A read-only existing-Bronze
    run must never call it -- the returned list must stay ``[]``.

    (``apply_sql_file`` is the SILVER/GOLD migration builder -- a separate,
    legitimate medallion layer the issue does not forbid; it targets
    ``silver``/``gold``, never ``bronze``. It is asserted read-only against
    Bronze by the fact that ``load_csv`` and the drop-and-reload never run.)
    """
    bronze_writes: list = []
    monkeypatch.setattr(
        db,
        "load_csv",
        lambda dsn, table, path: bronze_writes.append(("load_csv", table)),
    )
    return bronze_writes


def _stub_existing_bronze(monkeypatch, *, rows: int, columns: tuple[str, ...]) -> None:
    monkeypatch.setattr(db, "resolve_dsn", lambda: "postgresql://stub")
    monkeypatch.setattr(
        db,
        "inspect_bronze",
        lambda dsn, table: db.BronzeRelation(exists=True, columns=columns, rows=rows),
    )
    # The silver/gold migration builder is a no-op here (its Bronze-independence
    # is what `_forbid_bronze_writes` proves): stub it so the through-gold tail
    # completes without a real DB connection, exactly as `stub_green_db` does.
    monkeypatch.setattr(db, "apply_sql_file", lambda dsn, path: None)
    # Green static + live gates so the run reaches gold (the DB-first tail is
    # identical to CSV mode -- the mapping gate is NOT bypassed).
    monkeypatch.setattr(
        commands, "run_gate_command", lambda argv, cwd: (0, "0 violations")
    )


# The fixture's source-map.yaml has no `columns:` list, so referenced columns
# is empty -> the superset check requires nothing. Any healthy relation passes.
_HEALTHY_COLUMNS = ("id", "amount")


def _through_gold(root):
    return [
        a
        for a in build_table_assets(TABLE, root)
        if a.key.path[-1] in THROUGH_GOLD_ASSETS
    ]


def test_existing_bronze_run_issues_zero_bronze_writes(
    db_first_repo, monkeypatch
) -> None:
    writes = _forbid_bronze_writes(monkeypatch)
    _stub_existing_bronze(monkeypatch, rows=249106, columns=_HEALTHY_COLUMNS)

    result = materialize(_through_gold(db_first_repo))
    assert result.success is True

    # THE non-destruction guarantee: the Bronze drop-and-reload never ran.
    assert writes == []

    records = {r["asset"]: r for r in EvidenceWriter(db_first_repo, RUN_ID).records()}
    # raw_source_file is deferred (no landing file by design) -- NOT a STOP edge.
    assert records["raw_source_file"]["outcome"] == "deferred"
    assert records["raw_source_file"]["owner"]
    # bronze_table verified the existing relation read-only.
    bronze = records["bronze_table"]
    assert bronze["outcome"] == "materialized"
    assert bronze["measured"]["source_mode"] == "existing-bronze"
    assert bronze["measured"]["rows_present"] == 249106
    assert bronze["measured"]["bronze_mutated"] is False
    assert "rows_loaded" not in bronze["measured"]  # nothing was loaded
    # The gated tail proceeded through gold (gate NOT bypassed).
    assert records["source_map"]["outcome"] == "materialized"
    assert records["gold_tables"]["outcome"] == "materialized"

    summary = finalize_run(
        db_first_repo, RUN_ID, [TABLE], RunMeta(started="2026-07-21T00:00:00Z")
    )
    assert summary["run_status"] == "succeeded"


def test_absent_existing_bronze_fails_closed_with_named_blocker(
    db_first_repo, monkeypatch
) -> None:
    writes = _forbid_bronze_writes(monkeypatch)
    monkeypatch.setattr(db, "resolve_dsn", lambda: "postgresql://stub")
    monkeypatch.setattr(
        db, "inspect_bronze", lambda dsn, table: db.BronzeRelation(exists=False)
    )

    result = materialize(_through_gold(db_first_repo), raise_on_error=False)
    assert result.success is False  # fail closed
    assert writes == []  # still zero writes -- never tried to create it

    records = {r["asset"]: r for r in EvidenceWriter(db_first_repo, RUN_ID).records()}
    bronze = records["bronze_table"]
    assert bronze["outcome"] == "failed"
    assert "not found" in bronze["blocking_reason"]
    assert bronze["owner"]  # named


def test_empty_existing_bronze_fails_closed(db_first_repo, monkeypatch) -> None:
    _forbid_bronze_writes(monkeypatch)
    _stub_existing_bronze(monkeypatch, rows=0, columns=_HEALTHY_COLUMNS)

    result = materialize(_through_gold(db_first_repo), raise_on_error=False)
    assert result.success is False
    bronze = {r["asset"]: r for r in EvidenceWriter(db_first_repo, RUN_ID).records()}[
        "bronze_table"
    ]
    assert bronze["outcome"] == "failed"
    assert "EMPTY" in bronze["blocking_reason"]


def test_mismatched_columns_fail_closed(db_first_repo, monkeypatch) -> None:
    # A source-map that references a column the live relation lacks -> mismatch.
    (db_first_repo / "mappings" / TABLE / "source-map.yaml").write_text(
        "table: demo_table\n"
        "columns:\n"
        "  - source_name: id\n"
        "  - source_name: amount\n"
        "  - source_name: currency\n",  # not present in _HEALTHY_COLUMNS
        encoding="utf-8",
    )
    _forbid_bronze_writes(monkeypatch)
    _stub_existing_bronze(monkeypatch, rows=10, columns=_HEALTHY_COLUMNS)

    result = materialize(_through_gold(db_first_repo), raise_on_error=False)
    assert result.success is False
    bronze = {r["asset"]: r for r in EvidenceWriter(db_first_repo, RUN_ID).records()}[
        "bronze_table"
    ]
    assert bronze["outcome"] == "failed"
    assert "currency" in bronze["blocking_reason"]
    assert "source-map" in bronze["blocking_reason"]


def test_bronze_unchanged_after_a_downstream_gate_failure(
    db_first_repo, monkeypatch
) -> None:
    """#405 acceptance #3 (second half): Bronze stays untouched after a
    DOWNSTREAM failure too.

    bronze_table verifies the existing relation read-only (materialized), then
    a downstream gate fails. The Bronze drop-and-reload still never runs and the
    run fails closed -- the read-only verification never mutated the relation
    on the way in, and the failure never triggers a reload on the way out.
    """
    writes = _forbid_bronze_writes(monkeypatch)
    monkeypatch.setattr(db, "resolve_dsn", lambda: "postgresql://stub")
    monkeypatch.setattr(
        db,
        "inspect_bronze",
        lambda dsn, table: db.BronzeRelation(
            exists=True, columns=_HEALTHY_COLUMNS, rows=249106
        ),
    )
    monkeypatch.setattr(db, "apply_sql_file", lambda dsn, path: None)
    # The static governance gate fails at silver_tables (a downstream STOP).
    monkeypatch.setattr(
        commands, "run_gate_command", lambda argv, cwd: (1, "3 violations")
    )

    result = materialize(_through_gold(db_first_repo), raise_on_error=False)
    assert result.success is False  # fail closed on the downstream gate

    records = {r["asset"]: r for r in EvidenceWriter(db_first_repo, RUN_ID).records()}
    # Bronze was verified read-only and materialized BEFORE the failure...
    assert records["bronze_table"]["outcome"] == "materialized"
    assert records["bronze_table"]["measured"]["bronze_mutated"] is False
    # ...the downstream gate failed...
    assert records["silver_tables"]["outcome"] == "failed"
    # ...and the Bronze drop-and-reload NEVER ran, before or after the failure.
    assert writes == []


def test_silver_migration_writing_bronze_fails_closed_before_applying(
    db_first_repo, monkeypatch
) -> None:
    """#417 defense-in-depth: in existing-bronze mode a silver migration that
    WRITES to Bronze (a layering violation) fails closed BEFORE it is applied --
    extending the adapter's read-only guarantee to whole-run Bronze immutability.

    ``apply_sql_file`` is a raise-on-call spy here (NOT a no-op), so "the offending
    migration was never executed" is provable: if the guard let it through, the
    spy would raise and the test would fail for the wrong reason.
    """
    writes = _forbid_bronze_writes(monkeypatch)
    monkeypatch.setattr(db, "resolve_dsn", lambda: "postgresql://stub")
    monkeypatch.setattr(
        db,
        "inspect_bronze",
        lambda dsn, table: db.BronzeRelation(
            exists=True, columns=_HEALTHY_COLUMNS, rows=249106
        ),
    )
    monkeypatch.setattr(
        commands, "run_gate_command", lambda argv, cwd: (0, "0 violations")
    )

    def must_not_apply(dsn, path):
        raise AssertionError(f"guard must fail closed before applying {path.name}")

    monkeypatch.setattr(db, "apply_sql_file", must_not_apply)

    # Overwrite the fixture's benign silver migration with one that WRITES Bronze.
    offending = (
        db_first_repo / "warehouse" / "migrations" / f"0001_create_silver_{TABLE}.sql"
    )
    offending.write_text(
        f"INSERT INTO bronze.{TABLE} (id) SELECT 1;\n", encoding="utf-8"
    )

    result = materialize(_through_gold(db_first_repo), raise_on_error=False)
    assert result.success is False  # fail closed
    assert writes == []  # the read-only adapter never wrote either

    records = {r["asset"]: r for r in EvidenceWriter(db_first_repo, RUN_ID).records()}
    silver = records["silver_tables"]
    assert silver["outcome"] == "failed"
    assert "bronze" in silver["blocking_reason"].lower()
    assert silver["measured"]["offending_migration"] == offending.name
    assert silver["owner"] == "warehouse owner"


def test_silver_migration_reading_bronze_is_allowed(db_first_repo, monkeypatch) -> None:
    """The normal medallion flow is untouched: a silver migration that only READS
    Bronze (``FROM bronze.<t>``) is applied and the run proceeds through gold --
    the guard fires on WRITES, never on the legitimate read (#417)."""
    _forbid_bronze_writes(monkeypatch)
    _stub_existing_bronze(monkeypatch, rows=249106, columns=_HEALTHY_COLUMNS)

    # A legitimate silver migration: builds silver BY READING bronze.
    silver_mig = (
        db_first_repo / "warehouse" / "migrations" / f"0001_create_silver_{TABLE}.sql"
    )
    silver_mig.write_text(
        f"CREATE TABLE silver.{TABLE} AS SELECT * FROM bronze.{TABLE};\n",
        encoding="utf-8",
    )

    result = materialize(_through_gold(db_first_repo))
    assert result.success is True  # the read-from-bronze migration is allowed

    records = {r["asset"]: r for r in EvidenceWriter(db_first_repo, RUN_ID).records()}
    assert records["silver_tables"]["outcome"] == "materialized"
    assert records["gold_tables"]["outcome"] == "materialized"


def test_existing_bronze_without_dsn_blocks_on_deferred_boundary(
    db_first_repo, monkeypatch
) -> None:
    writes = _forbid_bronze_writes(monkeypatch)
    monkeypatch.setattr(db, "resolve_dsn", lambda: None)

    def must_not_inspect(dsn, table):
        raise AssertionError("must not inspect without a DSN")

    monkeypatch.setattr(db, "inspect_bronze", must_not_inspect)

    result = materialize(_through_gold(db_first_repo), raise_on_error=False)
    assert result.success is False
    assert writes == []
    bronze = {r["asset"]: r for r in EvidenceWriter(db_first_repo, RUN_ID).records()}[
        "bronze_table"
    ]
    assert bronze["outcome"] == "blocked"
    assert bronze["blocking_reason"] == db.DEFERRED_BOUNDARY
