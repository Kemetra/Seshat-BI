"""US3 (SC-004): the dbt engine degrades TRUTHFULLY -- never a fabricated pass.

* No live dbt profile (SESHAT_DBT_*) under `engine: dbt` -> the dbt deferred
  boundary is recorded and the asset blocks fail-closed (the dbt bridge never
  runs); the migrations DSN is NOT the dbt engine's credential contract.
* The dbt runtime absent (DbtUnavailable) -> the asset blocks with a concrete
  redacted reason + named owner, no traceback.
* A dbt error carrying a fake DSN/host is REDACTED before it reaches the dagster
  record OR the raised Failure (plan-review F4/R6; Principle IX).
* Lock contention (LockUnavailable) -> a concrete redacted blocking_reason, per
  seshat.dbt bounded-lock semantics -- never a traceback, never a silent hang.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from conftest import TABLE, mappings_digest
from dagster import Failure, build_asset_context
from tower_bi_orchestration import commands
from tower_bi_orchestration.assets import build_table_assets
from tower_bi_orchestration.evidence_writer import EvidenceWriter


def _dbt_engine(root: Path) -> None:
    (root / "mappings" / TABLE / "build-engine.yaml").write_text(
        "silver: dbt\ngold: dbt\n", encoding="utf-8"
    )


def _silver_asset(root: Path):
    for asset in build_table_assets(TABLE, root):
        if asset.key.path[-1] == "silver_tables":
            return asset
    raise AssertionError("silver_tables asset not found")


def _records(root: Path) -> dict:
    return {row["asset"]: row for row in EvidenceWriter(root, "testrun-001").records()}


def test_dbt_engine_no_profile_records_deferred_boundary_and_blocks(
    green_repo, monkeypatch
) -> None:
    _dbt_engine(green_repo)
    from tower_bi_orchestration.assets import gates

    # No live dbt profile, and a green gate so ONLY the dbt deferred boundary
    # can stop the asset (the migrations DSN is deliberately irrelevant here).
    monkeypatch.setattr(gates.dbt_build, "profile_present", lambda root: False)
    monkeypatch.setattr(commands, "run_gate_command", lambda argv, cwd: (0, "ok"))
    before = mappings_digest(green_repo)

    with pytest.raises(Failure):
        _silver_asset(green_repo)(build_asset_context())

    silver = _records(green_repo)["silver_tables"]
    assert silver["outcome"] == "blocked"
    assert gates.dbt_build.DBT_DEFERRED_BOUNDARY in silver["blocking_reason"]
    assert silver["owner"]  # named owner, fail-closed
    assert silver["ts"]  # timestamped record
    assert silver["measured"].get("engine") != "dbt"  # bridge never ran (no fabricate)
    assert mappings_digest(green_repo) == before  # no readiness pass written


def test_dbt_runtime_absent_blocks_with_concrete_reason_no_traceback(
    green_repo, monkeypatch
) -> None:
    _dbt_engine(green_repo)
    from tower_bi_orchestration.assets import gates

    monkeypatch.setattr(gates.dbt_build, "profile_present", lambda root: True)
    monkeypatch.setattr(commands, "run_gate_command", lambda argv, cwd: (0, "ok"))

    from tower_bi_orchestration.assets import gates

    def unavailable(context, table, layer, root):
        # what the bridge returns when the dbt runtime is not importable
        return (
            1,
            {
                "engine": "dbt",
                "outcome": "blocked",
                "blocking_reason": "dbt is unavailable; install 'seshat-bi[dbt]'",
                "owner": "the dbt runtime owner",
            },
            None,
        )

    monkeypatch.setattr(gates.dbt_build, "build_layer", unavailable)

    with pytest.raises(Failure) as err:
        _silver_asset(green_repo)(build_asset_context())

    assert "Traceback" not in str(err.value)
    silver = _records(green_repo)["silver_tables"]
    assert silver["outcome"] == "blocked"
    assert "unavailable" in silver["blocking_reason"]
    assert silver["owner"] == "the dbt runtime owner"


def test_dbt_error_with_a_fake_dsn_is_redacted_everywhere(
    green_repo, monkeypatch
) -> None:
    _dbt_engine(green_repo)
    from tower_bi_orchestration.assets import gates

    monkeypatch.setattr(gates.dbt_build, "profile_present", lambda root: True)
    monkeypatch.setattr(commands, "run_gate_command", lambda argv, cwd: (0, "ok"))

    # Assembled from parts via interpolation so this committed source never holds
    # the full scheme://userinfo@host literal shape the C2 secret scanner catches
    # (the {} interpolation is C2's documented source-code exemption); the RUNTIME
    # value is still a real DSN the shared redaction must scrub.
    scheme = "postgresql"
    userinfo = "user:secretpw"
    secret_dsn = f"{scheme}://{userinfo}@dbhost:5432/analytics"

    import seshat.cli.commands.dbt as dbt_cli

    def raise_with_dsn(root, table, runner):
        # a governed refusal whose text carries a live-looking DSN
        raise dbt_cli.GovernanceError("DBT_X", f"connection refused at {secret_dsn}")

    monkeypatch.setattr(dbt_cli, "create_plan", raise_with_dsn)

    with pytest.raises(Failure) as err:
        _silver_asset(green_repo)(build_asset_context())

    # absent from the raised Failure description
    assert secret_dsn not in str(err.value)
    assert "secretpw" not in str(err.value)
    # absent from the recorded evidence row
    silver = _records(green_repo)["silver_tables"]
    row_text = str(silver)
    assert secret_dsn not in row_text
    assert "secretpw" not in row_text
    assert silver["outcome"] == "blocked"


def test_lock_contention_surfaces_a_concrete_redacted_reason(
    green_repo, monkeypatch
) -> None:
    _dbt_engine(green_repo)
    from tower_bi_orchestration.assets import gates

    monkeypatch.setattr(gates.dbt_build, "profile_present", lambda root: True)
    monkeypatch.setattr(commands, "run_gate_command", lambda argv, cwd: (0, "ok"))

    import seshat.cli.commands.dbt as dbt_cli

    def held_lock(root, table, runner):
        raise dbt_cli.LockUnavailable(
            "dbt invocation already in progress for retail_store_sales/shadow"
        )

    monkeypatch.setattr(dbt_cli, "create_plan", held_lock)

    with pytest.raises(Failure) as err:
        _silver_asset(green_repo)(build_asset_context())

    assert "Traceback" not in str(err.value)
    silver = _records(green_repo)["silver_tables"]
    assert silver["outcome"] == "blocked"
    assert "already in progress" in silver["blocking_reason"]
    assert silver["owner"]  # named owner
