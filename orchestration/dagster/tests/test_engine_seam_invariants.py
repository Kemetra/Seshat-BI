"""SC-006 / FR-008 / plan-review R5: the engine seam changes NOTHING structural.

Three invariants, each sitting ON its risk (not adjacent to it):

1. Asset dependency TOPOLOGY is unchanged (FR-005): the silver/gold/live edges
   are asserted POSITIVELY from the built assets -- a body change to _build_layer
   cannot perturb them.
2. A real dbt-engine evidence record CONFORMS to the unchanged run-evidence
   schema (FR-008): only gate_command / measured contents differ; the record
   built through the PRODUCTION _measured_from_result validates against the
   committed schema mirror, and the committed schema file is byte-unchanged.
3. STATIC no-bypass oracle (R5): no module under tower_bi_orchestration imports a
   dagster_dbt execution API (DbtCliResource / @dbt_assets) or invokes dbt
   directly; the bridge reaches dbt ONLY through the governed seshat entry point.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from conftest import TABLE
from tower_bi_orchestration.assets import build_table_assets

from seshat.dagster_adapter import evidence as ev

_REPO_ROOT = Path(__file__).resolve().parents[3]
_ORCH_SRC = _REPO_ROOT / "orchestration" / "dagster" / "src" / "tower_bi_orchestration"


# --------------------------------------------------------------------------
# 1. Topology unchanged (FR-005) -- positive edge assertion.
# --------------------------------------------------------------------------


def _asset_by_name(assets: list, name: str):
    return next(a for a in assets if a.key.path[-1] == name)


def test_asset_dependency_topology_is_unchanged(tmp_path) -> None:
    assets = build_table_assets(TABLE, tmp_path)

    def upstream_leaves(name: str) -> set[str]:
        asset = _asset_by_name(assets, name)
        deps = {dep.path[-1] for keys in asset.asset_deps.values() for dep in keys}
        return deps

    # The exact medallion edges spec 134 shipped; the dbt engine seam is a BODY
    # branch only and must not move any edge.
    assert upstream_leaves("silver_tables") == {"source_map"}
    assert upstream_leaves("gold_tables") == {"silver_tables"}
    assert upstream_leaves("live_validate") == {"gold_tables"}
    assert upstream_leaves("source_map") == {"source_profile"}


# --------------------------------------------------------------------------
# 2. dbt-engine evidence conforms to the UNCHANGED schema (FR-008).
# --------------------------------------------------------------------------


def _dbt_measured() -> dict:
    """The production dbt-engine measured shape (built by the real bridge helper)."""
    from tower_bi_orchestration import dbt_build

    import seshat.cli.commands.dbt as dbt_cli

    result = dbt_cli.CommandResult(
        command="build",
        table_id="retail_store_sales",
        outcome="pass",  # seshat.dbt readiness word -> translated to an exec word
        exit_code=0,
        message="derived dbt evidence completed",
        evidence_path="mappings/retail_store_sales/dbt-evidence/inv.json",
    )
    measured = dbt_build._measured_from_result(result, "retail_store_sales")
    return {
        **measured,
        "engine": "dbt",
        "warehouse_updated": False,
        "self_accepted_by_recompute": True,
    }


def test_dbt_engine_record_conforms_to_the_unchanged_schema() -> None:
    measured = _dbt_measured()
    # never the readiness token, never a numeric score (hard rule #9)
    assert "pass" not in measured.values()
    assert not [k for k in measured if "score" in k.lower()]

    summary = {
        "run_id": "run-dbt-001",
        "commit_sha": "0000000",
        "started": "2026-07-17T00:00:00Z",
        "finished": "2026-07-17T00:01:00Z",
        "trigger": "manual-CI",
        "tables": ["retail_store_sales"],
        "run_status": "succeeded",
    }
    record = {
        "run_id": "run-dbt-001",
        "asset": "silver_tables",
        "table": "retail_store_sales",
        "gate_command": "-m seshat.cli check",
        "exit_code": 0,
        "measured": measured,
        "outcome": "materialized",  # execution word, never "pass"
        "blocking_reason": None,
        "owner": None,
        "ts": "2026-07-17T00:00:30Z",
    }
    # validate_records is the code mirror of the committed JSON schema.
    assert ev.validate_records(summary, [record]) == []


def test_run_evidence_schema_file_is_byte_unchanged() -> None:
    schema = "schemas/dagster-run-evidence.schema.json"
    result = subprocess.run(
        ["git", "-c", "core.fsmonitor=false", "diff", "--quiet", "HEAD", "--", schema],
        cwd=_REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, "the run-evidence schema MUST NOT change (FR-008)"


# --------------------------------------------------------------------------
# 3. STATIC no-bypass oracle (plan-review R5).
# --------------------------------------------------------------------------

# Real USAGE shapes (import / attribute / decorator), not prose: a module's
# docstring may legitimately say it imports NO dagster_dbt, so the oracle scans
# executable code (parsed AST), never comment/docstring text.
_FORBIDDEN_IMPORTS = frozenset({"dagster_dbt"})
_FORBIDDEN_NAMES = frozenset({"DbtCliResource", "dbt_assets", "DbtProject"})


def _orch_sources() -> list[Path]:
    return list(_ORCH_SRC.rglob("*.py"))


def _import_hits(node) -> list[str]:
    import ast

    if isinstance(node, ast.Import):
        return [
            a.name for a in node.names if a.name.split(".")[0] in _FORBIDDEN_IMPORTS
        ]
    if isinstance(node, ast.ImportFrom):
        root = (node.module or "").split(".")[0]
        from_module = [node.module or ""] if root in _FORBIDDEN_IMPORTS else []
        return from_module + [a.name for a in node.names if a.name in _FORBIDDEN_NAMES]
    return []


def _name_hits(node) -> list[str]:
    import ast

    if isinstance(node, ast.Name) and node.id in _FORBIDDEN_NAMES:
        return [node.id]
    if isinstance(node, ast.Attribute) and node.attr in _FORBIDDEN_NAMES:
        return [node.attr]
    return []


def _forbidden_uses(source: str) -> list[str]:
    import ast

    hits: list[str] = []
    for node in ast.walk(ast.parse(source)):
        hits += _import_hits(node) + _name_hits(node)
    return hits


def test_no_module_uses_a_dagster_dbt_execution_api() -> None:
    offenders: list[str] = []
    for path in _orch_sources():
        for hit in _forbidden_uses(path.read_text(encoding="utf-8")):
            offenders.append(f"{path.name}: {hit}")
    assert offenders == [], f"dagster-dbt execution API reachable: {offenders}"


def test_bridge_reaches_dbt_only_through_the_governed_seshat_entry() -> None:
    bridge = (_ORCH_SRC / "dbt_build.py").read_text(encoding="utf-8")
    # positively: the bridge delegates to the governed seshat build entry point
    assert "run_governed_build" in bridge
    assert "from seshat.cli.commands.dbt import" in bridge
    # negatively: it constructs no dbt argv / subprocess / raw selector itself
    # (the dbt-CLI selection form is `--select selector:<name>`; the bridge's
    # measured dict key `"selector"` is a report field, not an argv token).
    for forbidden in ("subprocess", "--select", "selector:seshat", "DbtCliResource"):
        assert forbidden not in bridge, f"bridge builds dbt directly: {forbidden}"
