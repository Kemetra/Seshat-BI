"""Integration test: Report Intent metric-name resolution (spec 123, US1,
FR-003/FR-004).

Independent Test (spec.md US1): "every metric referenced anywhere in intent...
resolves to an approved metric contract; any missing definition is surfaced as
a gap, not invented" (SC-002). This test sits ON that real danger: it proves
that an intent naming a metric with NO approved contract is reported as a GAP
with `readiness: blocked` and that the resolver NEVER invents a metric contract
file to make the reference resolve -- the oracle here is a real filesystem
check (does the contract file exist / what does it actually say), not a
property read back from the code under test.

Uses the REAL retail_store_sales worked instance
(mappings/retail_store_sales/design/report-intent.yaml, spec 123 T015) and its
REAL approved (pass) metric contracts for the "resolves clean" half, and a
synthetic tmp_path fixture (mirroring gap_detector's tests) for the "records a
gap, never invents" half.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from seshat.report_intent import resolve_metric_references

pytestmark = pytest.mark.unit

_REPO_ROOT = Path(__file__).resolve().parents[2]


def _load(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8-sig"))


# --- User Story 1: the real retail_store_sales worked instance resolves clean


def test_real_worked_instance_all_metrics_resolve() -> None:
    intent_path = (
        _REPO_ROOT / "mappings" / "retail_store_sales" / "design" / "report-intent.yaml"
    )
    intent = _load(intent_path)

    result = resolve_metric_references(intent, _REPO_ROOT)

    assert result.gaps == ()
    assert set(result.resolved) == {
        "TotalSales",
        "TransactionCount",
        "AvgTransactionValue",
        "TotalQuantity",
        "DiscountedTransactionRate",
    }


# --- User Story 2: an unapproved / missing metric is a gap, never invented ---


def _metric_yaml(name: str, status: str) -> str:
    return (
        f'name: "{name}"\n'
        "owner: metric_owner\n"
        "binds_to:\n"
        '  gold_table: "gold.fct_x"\n'
        "  columns:\n"
        '    - "amount"\n'
        "definition: {kind: base, aggregation: sum, filter: []}\n"
        "readiness:\n"
        f'  status: "{status}"\n'
        '  evidence: ["approved by the named metric owner"]\n'
        "  blocking_reasons: []\n"
    )


def _approve(root: Path, scope: str, *names: str) -> None:
    status = root / "mappings" / scope / "readiness-status.yaml"
    status.parent.mkdir(parents=True, exist_ok=True)
    status.write_text(
        "approvals:\n"
        "  - stage: semantic_model_ready\n"
        '    owner: "Ada Lovelace (metric_owner)"\n'
        '    at: "2026-07-22"\n'
        f"    contracts: [{', '.join(names)}]\n",
        encoding="utf-8",
    )


def test_unapproved_metric_is_a_gap_never_invented(tmp_path: Path) -> None:
    metrics_dir = tmp_path / "mappings" / "demo_table" / "metrics"
    metrics_dir.mkdir(parents=True)
    (metrics_dir / "DraftMetric.yaml").write_text(
        _metric_yaml("DraftMetric", "not_started"), encoding="utf-8"
    )

    intent = {
        "outcome_metrics": [
            {
                "name": "DraftMetric",
                "store_ref": "mappings/demo_table/metrics/DraftMetric.yaml",
                "status_required": "pass",
            }
        ],
        "driver_metrics": [],
        "guardrail_metrics": [],
    }

    result = resolve_metric_references(intent, tmp_path)

    assert result.resolved == ()
    assert len(result.gaps) == 1
    gap = result.gaps[0]
    assert gap.name == "DraftMetric"
    assert "not owner-approved" in gap.reason

    # Never invented: the gap's store_ref file is untouched -- still the
    # not_started content the test wrote, never silently promoted to pass.
    on_disk = _load(metrics_dir / "DraftMetric.yaml")
    assert on_disk["readiness"]["status"] == "not_started"


def test_missing_contract_file_is_a_gap_never_invented(tmp_path: Path) -> None:
    intent = {
        "outcome_metrics": [
            {
                "name": "GhostMetric",
                "store_ref": "mappings/demo_table/metrics/GhostMetric.yaml",
                "status_required": "pass",
            }
        ],
        "driver_metrics": [],
        "guardrail_metrics": [],
    }

    result = resolve_metric_references(intent, tmp_path)

    assert result.resolved == ()
    assert len(result.gaps) == 1
    gap = result.gaps[0]
    assert gap.name == "GhostMetric"
    assert "no approved metric contract found" in gap.reason

    # Never invented: no file was created at the referenced store_ref.
    assert not (
        tmp_path / "mappings" / "demo_table" / "metrics" / "GhostMetric.yaml"
    ).exists()


def test_mixed_resolved_and_gap(tmp_path: Path) -> None:
    metrics_dir = tmp_path / "mappings" / "demo_table" / "metrics"
    metrics_dir.mkdir(parents=True)
    (metrics_dir / "GoodMetric.yaml").write_text(
        _metric_yaml("GoodMetric", "pass"), encoding="utf-8"
    )
    _approve(tmp_path, "demo_table", "GoodMetric")

    intent = {
        "outcome_metrics": [
            {
                "name": "GoodMetric",
                "store_ref": "mappings/demo_table/metrics/GoodMetric.yaml",
                "status_required": "pass",
            }
        ],
        "driver_metrics": [
            {
                "name": "MissingMetric",
                "store_ref": "mappings/demo_table/metrics/MissingMetric.yaml",
                "status_required": "pass",
            }
        ],
        "guardrail_metrics": [],
    }

    result = resolve_metric_references(intent, tmp_path)

    assert result.resolved == ("GoodMetric",)
    assert len(result.gaps) == 1
    assert result.gaps[0].name == "MissingMetric"


def test_self_asserted_pass_is_not_an_approved_contract(tmp_path: Path) -> None:
    """Audit F040: `readiness.status: pass` alone is not approval -- the shared
    inventory also needs a named metric_owner approval naming the contract."""
    metrics_dir = tmp_path / "mappings" / "demo_table" / "metrics"
    metrics_dir.mkdir(parents=True)
    (metrics_dir / "NetSales.yaml").write_text(
        'name: "NetSales"\nreadiness: {status: pass}\n', encoding="utf-8"
    )
    ref = {"name": "NetSales", "store_ref": "mappings/demo_table/metrics/NetSales.yaml"}
    result = resolve_metric_references({"outcome_metrics": [ref]}, tmp_path)
    assert result.resolved == ()


def test_store_ref_for_another_contract_is_a_gap(tmp_path: Path) -> None:
    """Audit F145: a Gross Margin reference pointing at net_sales is a gap."""
    metrics_dir = tmp_path / "mappings" / "t" / "metrics"
    metrics_dir.mkdir(parents=True)
    (metrics_dir / "NetSales.yaml").write_text(
        _metric_yaml("NetSales", "pass"), encoding="utf-8"
    )
    _approve(tmp_path, "t", "NetSales")
    intent = {
        "outcome_metrics": [
            {"name": "Gross Margin", "store_ref": "mappings/t/metrics/NetSales.yaml"}
        ]
    }
    result = resolve_metric_references(intent, tmp_path)
    assert result.resolved == ()
    assert "names contract 'NetSales'" in result.gaps[0].reason


@pytest.mark.parametrize(
    "store_ref", ["../outside/x.yaml", "/etc/x.yaml", "mappings/../x/metrics/y.yaml"]
)
def test_uncontained_store_ref_is_a_gap(tmp_path: Path, store_ref: str) -> None:
    intent = {"guardrail_metrics": [{"name": "x", "store_ref": store_ref}]}
    result = resolve_metric_references(intent, tmp_path)
    assert result.resolved == ()
    assert "not a contained" in result.gaps[0].reason
