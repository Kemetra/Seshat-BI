"""US5 (SC-007): migrations remain the untouched parity oracle and rollback.

Activating the dbt engine changes only what the asset EXECUTES. A dbt-engine run
must not modify, delete, or supersede any `warehouse/migrations/*.sql` file and
must not write migration-owned silver/gold (the governed dbt build targets
shadow schemas only, enforced inside seshat.dbt). Reverting a table to
`engine: migrations` reproduces the pre-feature migrations behavior exactly.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

from conftest import TABLE, stub_green_db
from dagster import materialize
from tower_bi_orchestration.assets import build_table_assets
from tower_bi_orchestration.evidence_writer import EvidenceWriter


def _migrations_digest(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted((root / "warehouse" / "migrations").rglob("*.sql")):
        digest.update(str(path.relative_to(root)).encode())
        digest.update(path.read_bytes())
    return digest.hexdigest()


def _set_engine(root: Path, silver: str, gold: str) -> None:
    (root / "mappings" / TABLE / "build-engine.yaml").write_text(
        f"silver: {silver}\ngold: {gold}\n", encoding="utf-8"
    )


def _through_silver(root: Path):
    return [
        a
        for a in build_table_assets(TABLE, root)
        if a.key.path[-1]
        in {
            "raw_source_file",
            "bronze_table",
            "source_profile",
            "source_map",
            "silver_tables",
        }
    ]


def _stub_dbt_bridge(monkeypatch) -> dict:
    from tower_bi_orchestration.assets import gates

    seen: dict = {"applied_sql": []}

    def fake_build_layer(context, table, layer, root):
        # The governed bridge targets shadow only; it applies no migration SQL.
        return (
            0,
            {"engine": "dbt", "selector": f"seshat_table_{table}", "target": "shadow"},
            f"mappings/{table}/dbt-evidence/inv-{layer}.json",
        )

    monkeypatch.setattr(gates.dbt_build, "build_layer", fake_build_layer)
    return seen


def test_dbt_engine_run_touches_no_migration_file(green_repo, monkeypatch) -> None:
    from tower_bi_orchestration.assets import gates as _gates

    monkeypatch.setattr(_gates.dbt_build, "profile_present", lambda root: True)
    stub_green_db(monkeypatch)
    _set_engine(green_repo, "dbt", "dbt")

    applied: list = []
    from tower_bi_orchestration import db

    # A dbt-engine build MUST NOT apply any migration SQL.
    monkeypatch.setattr(db, "apply_sql_file", lambda dsn, path: applied.append(path))
    _stub_dbt_bridge(monkeypatch)

    before = _migrations_digest(green_repo)
    result = materialize(_through_silver(green_repo))
    assert result.success is True

    assert applied == []  # the migrations loop never ran under the dbt engine
    assert _migrations_digest(green_repo) == before  # SQL files byte-unchanged

    silver = {
        r["asset"]: r for r in EvidenceWriter(green_repo, "testrun-001").records()
    }["silver_tables"]
    assert silver["measured"]["engine"] == "dbt"
    assert silver["measured"].get("target") == "shadow"  # shadow only


def test_revert_to_migrations_reproduces_the_prefeature_path(
    green_repo, monkeypatch
) -> None:
    stub_green_db(monkeypatch)
    _set_engine(green_repo, "migrations", "migrations")

    applied: list = []
    from tower_bi_orchestration import db

    monkeypatch.setattr(
        db, "apply_sql_file", lambda dsn, path: applied.append(Path(path).name)
    )
    # If the dbt bridge were reached, this would raise -- proving migrations only.
    from tower_bi_orchestration.assets import gates

    def forbidden_bridge(context, table, layer, root):
        raise AssertionError("dbt bridge must not run under engine: migrations")

    monkeypatch.setattr(gates.dbt_build, "build_layer", forbidden_bridge)

    result = materialize(_through_silver(green_repo))
    assert result.success is True

    silver = {
        r["asset"]: r for r in EvidenceWriter(green_repo, "testrun-001").records()
    }["silver_tables"]
    assert silver["measured"]["engine"] == "migrations"
    # the committed silver migration was applied (the pre-feature behavior)
    assert any("silver" in name for name in applied)
