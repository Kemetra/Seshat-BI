"""US1 (SC-001/SC-002) + US2 (SC-003): the dbt engine builds through the governed
seshat.dbt path with the SAME gate, and the engine is explicit + fail-closed.

Two layers of proof, no database and no secrets:

* Bridge governance (SC-001): the bridge runs the FULL governed build through
  seshat.dbt -- it computes a plan, recomputes/self-accepts the accept-plan
  digest, and never passes a raw dbt selector/argument. Proven with call-spies
  on the governed entry points (the seshat.dbt runner is never really invoked).
* Asset branch (SC-001/SC-002/SC-003): with the dbt bridge stubbed to a canned
  governed result, the silver/gold asset takes the dbt branch, runs the SAME
  `seshat check` gate, records the dbt engine + self-accepted-plan marker +
  warehouse_updated:false; a non-zero check fails the asset and skips every
  downstream asset -- identical to the migrations engine; and non-`dbt` engine
  values take the migrations branch.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from conftest import TABLE, mappings_digest, stub_green_db
from dagster import materialize
from tower_bi_orchestration import commands
from tower_bi_orchestration.assets import build_table_assets
from tower_bi_orchestration.evidence_writer import (
    EvidenceWriter,
    RunMeta,
    finalize_run,
)


def _set_engine(root: Path, silver: str, gold: str) -> None:
    (root / "mappings" / TABLE / "build-engine.yaml").write_text(
        f"silver: {silver}\ngold: {gold}\n", encoding="utf-8"
    )


# --------------------------------------------------------------------------
# Bridge governance (SC-001): no raw pass-through, digest recomputed.
# --------------------------------------------------------------------------


def test_bridge_runs_the_full_governed_plan_and_self_accepts_the_digest(
    monkeypatch,
) -> None:
    from tower_bi_orchestration import dbt_build

    import seshat.cli.commands.dbt as dbt_cli
    from seshat.dbt.contracts import Operation

    seen: dict[str, object] = {}

    class _FakePlan:
        table_id = "retail_store_sales"

    def fake_create_plan(root, table, runner):
        # The governed plan must be computed through seshat.dbt (not a raw
        # dagster-dbt selector); the runner passed must be the governed
        # invoke_dbt, never a caller-supplied selector/argument.
        seen["create_plan_table"] = table
        seen["runner_is_invoke_dbt"] = runner is dbt_cli.invoke_dbt
        return _FakePlan()

    def fake_plan_digest(plan) -> str:
        seen["digest_recomputed"] = True
        return "d" * 64

    def fake_execute(args, operation):
        # The wrapper must self-accept its OWN recomputed digest and target the
        # governed BUILD op -- never a raw selector/target/profile argument.
        seen["accept_plan"] = args.accept_plan
        seen["operation"] = operation
        seen["table"] = args.table
        return dbt_cli.CommandResult(
            command="build",
            table_id=args.table,
            outcome="pass",
            exit_code=0,
            message="derived dbt evidence completed",
            evidence_path="mappings/retail_store_sales/dbt-evidence/x.json",
        )

    monkeypatch.setattr(dbt_cli, "create_plan", fake_create_plan)
    monkeypatch.setattr(dbt_cli, "_plan_digest", fake_plan_digest)
    monkeypatch.setattr(dbt_cli, "_execute", fake_execute)

    exit_code, measured, evidence_path = dbt_build.build_layer(
        context=None, table="retail_store_sales", layer="silver", root=Path(".")
    )

    assert seen["create_plan_table"] == "retail_store_sales"
    assert seen["runner_is_invoke_dbt"] is True  # governed runner, no raw arg
    assert seen["digest_recomputed"] is True
    assert seen["accept_plan"] == "d" * 64  # self-accepted its own recompute
    assert seen["operation"] is Operation.BUILD
    assert exit_code == 0
    assert evidence_path == "mappings/retail_store_sales/dbt-evidence/x.json"
    assert measured["selector"] == "seshat_table_retail_store_sales"
    assert "pass" not in measured.values()  # never the readiness token


def test_bridge_maps_governed_refusals_to_blocked_without_traceback(
    monkeypatch,
) -> None:
    from tower_bi_orchestration import dbt_build

    import seshat.cli.commands.dbt as dbt_cli

    def raise_drift(root, table, runner):
        raise dbt_cli.PlanDrift("accepted plan has drifted")

    monkeypatch.setattr(dbt_cli, "create_plan", raise_drift)

    exit_code, measured, evidence_path = dbt_build.build_layer(
        context=None, table="retail_store_sales", layer="silver", root=Path(".")
    )
    assert exit_code != 0
    assert measured["outcome"] == "blocked"
    assert evidence_path is None
    assert measured["blocking_reason"]  # a concrete reason, not a traceback


def test_bridge_maps_a_completed_failed_run_to_failed_with_a_concrete_reason(
    monkeypatch,
) -> None:
    # A dbt run that COMPLETES with model/test failures: _execute RETURNS a
    # CommandResult(outcome="failed") rather than raising. The dagster record
    # must read `failed` (ran-and-failed), NOT the generic `blocked`
    # (precondition-refusal) -- the distinction matters on the live surface.
    from tower_bi_orchestration import dbt_build

    import seshat.cli.commands.dbt as dbt_cli

    def completed_failed(root, table, operation=dbt_cli.Operation.BUILD):
        return dbt_cli.CommandResult(
            command="build",
            table_id=table,
            outcome="failed",
            exit_code=1,
            message="derived dbt evidence completed; models/tests failed",
            evidence_path=f"mappings/{table}/dbt-evidence/inv.json",
            blocking_reasons=(
                {"code": "DBT_EXECUTION_FAILED", "message": "a governed test failed"},
            ),
        )

    monkeypatch.setattr(dbt_build, "run_governed_build", completed_failed)

    exit_code, measured, evidence_path = dbt_build.build_layer(
        context=None, table="retail_store_sales", layer="silver", root=Path(".")
    )
    assert exit_code == 1
    assert measured["outcome"] == "failed"  # NOT the generic "blocked"
    assert measured["blocking_reason"]  # a concrete reason
    assert measured["owner"]
    assert evidence_path == "mappings/retail_store_sales/dbt-evidence/inv.json"


# --------------------------------------------------------------------------
# Asset branch (SC-001): engine dbt -> dbt branch, gate unchanged, exit 0.
# --------------------------------------------------------------------------


def _stub_dbt_bridge(monkeypatch, *, exit_code: int) -> dict:
    """Stub the dbt bridge to a canned governed result (no seshat.dbt run)."""
    from tower_bi_orchestration.assets import gates

    calls: dict = {"count": 0}

    def fake_build_layer(context, table, layer, root):
        calls["count"] += 1
        calls["layer"] = layer
        measured = {
            "engine": "dbt",
            "selector": f"seshat_table_{table}",
            "outcome": "pass" if exit_code == 0 else "failed",
            "run_results": {"total": 8, "success": 8},
        }
        path = f"mappings/{table}/dbt-evidence/inv-{layer}.json"
        return exit_code, measured, path

    monkeypatch.setattr(gates.dbt_build, "build_layer", fake_build_layer)
    return calls


def test_engine_dbt_takes_the_governed_branch_and_gate_and_materializes(
    green_repo, monkeypatch
) -> None:
    from tower_bi_orchestration.assets import gates as _gates

    monkeypatch.setattr(_gates.dbt_build, "profile_present", lambda root: True)
    stub_green_db(monkeypatch)
    _set_engine(green_repo, "dbt", "migrations")
    calls = _stub_dbt_bridge(monkeypatch, exit_code=0)
    before = mappings_digest(green_repo)

    through_gold = [
        a
        for a in build_table_assets(TABLE, green_repo)
        if a.key.path[-1]
        in {
            "raw_source_file",
            "bronze_table",
            "source_profile",
            "source_map",
            "silver_tables",
        }
    ]
    result = materialize(through_gold)
    assert result.success is True

    records = {
        row["asset"]: row for row in EvidenceWriter(green_repo, "testrun-001").records()
    }
    silver = records["silver_tables"]
    assert silver["outcome"] == "materialized"
    assert silver["exit_code"] == 0
    assert silver["measured"]["engine"] == "dbt"
    assert silver["measured"]["warehouse_updated"] is False  # shadow rehearsal
    assert silver["measured"]["self_accepted_by_recompute"] is True
    # the dbt bridge was invoked exactly once for this layer
    assert calls["count"] == 1
    # the SAME static gate ran (engine-independent gate_command)
    assert "check" in silver["gate_command"]
    assert silver["outcome"] != "pass"  # execution word, never the readiness token
    assert mappings_digest(green_repo) == before  # no authored truth


def test_engine_dbt_nonzero_gate_fails_and_skips_downstream(
    green_repo, monkeypatch
) -> None:
    from tower_bi_orchestration.assets import gates as _gates

    monkeypatch.setattr(_gates.dbt_build, "profile_present", lambda root: True)
    stub_green_db(monkeypatch)
    _set_engine(green_repo, "dbt", "dbt")
    _stub_dbt_bridge(monkeypatch, exit_code=0)

    def failing_gate(argv, cwd):
        return 1, "3 rule violations"

    monkeypatch.setattr(commands, "run_gate_command", failing_gate)

    result = materialize(build_table_assets(TABLE, green_repo), raise_on_error=False)
    assert result.success is False

    finalize_run(
        green_repo, "testrun-001", [TABLE], RunMeta(started="2026-07-17T00:00:00Z")
    )
    records = {
        row["asset"]: row for row in EvidenceWriter(green_repo, "testrun-001").records()
    }
    silver = records["silver_tables"]
    assert silver["outcome"] == "failed"
    assert silver["exit_code"] == 1
    assert "exit 1" in silver["blocking_reason"]
    assert silver["measured"]["engine"] == "dbt"  # branch recorded even on failure
    for downstream in ("gold_tables", "live_validate", "metric_contracts"):
        assert records[downstream]["outcome"] == "skipped", downstream


# --------------------------------------------------------------------------
# US2 (SC-003): only exact `dbt` engages the bridge; everything else migrations.
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "engine_body",
    [None, "silver: migrations\ngold: migrations\n", "silver: sqlmesh\ngold: x\n"],
)
def test_nondbt_engine_takes_migrations_branch(
    green_repo, monkeypatch, engine_body
) -> None:
    stub_green_db(monkeypatch)
    if engine_body is not None:
        (green_repo / "mappings" / TABLE / "build-engine.yaml").write_text(
            engine_body, encoding="utf-8"
        )
    calls = _stub_dbt_bridge(monkeypatch, exit_code=0)

    through_silver = [
        a
        for a in build_table_assets(TABLE, green_repo)
        if a.key.path[-1]
        in {
            "raw_source_file",
            "bronze_table",
            "source_profile",
            "source_map",
            "silver_tables",
        }
    ]
    result = materialize(through_silver)
    assert result.success is True

    records = {
        row["asset"]: row for row in EvidenceWriter(green_repo, "testrun-001").records()
    }
    silver = records["silver_tables"]
    assert silver["outcome"] == "materialized"
    assert silver["measured"]["engine"] == "migrations"
    assert calls["count"] == 0  # the dbt bridge was NEVER invoked
