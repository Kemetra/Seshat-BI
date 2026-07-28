"""Provider contracts remain immutable, minimal, and authority-bound."""

from __future__ import annotations

import ast
from dataclasses import FrozenInstanceError
from pathlib import Path, PurePosixPath
from types import MappingProxyType

import pytest

from seshat.statistical.contracts import (
    AnalysisSpec,
    ColumnBinding,
    MethodSpec,
)
from seshat.statistical.policy import PolicyContext
from seshat.statistical.providers.base import (
    DataRequest,
    ProviderUnavailable,
    ResourceLimits,
    build_data_request,
)

pytestmark = pytest.mark.unit


def _spec(column: str = "metric_value") -> AnalysisSpec:
    return AnalysisSpec(
        schema_version="1.0",
        analysis_id="weekly_signal",
        revision=1,
        subject="sample",
        question="Is the metric changing?",
        cadence="weekly",
        owner="Example Analyst",
        readiness_status=PurePosixPath("mappings/sample/readiness-status.yaml"),
        metric_contracts=(
            PurePosixPath("mappings/sample/metrics/ApprovedMetric.yaml"),
        ),
        provider=MappingProxyType({"kind": "local_csv", "dataset_id": "weekly_metric"}),
        population=MappingProxyType(
            {
                "grain": "one row per completed week",
                "inclusion": (),
                "exclusion": (),
            }
        ),
        roles=MappingProxyType(
            {"response": ColumnBinding(column=column, logical_type="number")}
        ),
        method=MethodSpec("describe", "1.0", MappingProxyType({})),
        missing_policy="complete_case",
        minimum_data=MappingProxyType(
            {"observations": 4, "groups": 1, "seasonal_cycles": 0}
        ),
        random_seed=1729,
        pii=MappingProxyType(
            {
                "classification": "none",
                "approval_evidence": (),
                "minimum_group_count": 7,
            }
        ),
        outputs=MappingProxyType({}),
    )


def _context() -> PolicyContext:
    return PolicyContext(
        subject="sample",
        readiness_path=Path("mappings/sample/readiness-status.yaml"),
        readiness_revision="7",
        contracts=(),
        approved_tables=frozenset({"gold.sample"}),
        approved_columns=MappingProxyType({"gold.sample": frozenset({"metric_value"})}),
    )


def test_build_data_request_projects_only_policy_approved_roles() -> None:
    request = build_data_request(_spec(), _context())

    assert request.table == "gold.sample"
    assert request.columns == ("metric_value",)
    assert request.logical_types == ("number",)
    assert request.roles == {"response": "metric_value"}
    assert request.privacy_floor == 7
    assert request.filters == ()
    assert request.aggregates == ()
    assert request.joins == ()


def test_build_data_request_refuses_role_outside_policy_context() -> None:
    with pytest.raises(
        ProviderUnavailable, match="not approved for statistical use"
    ) as exc_info:
        build_data_request(_spec("private_value"), _context())

    assert exc_info.value.blocker.code == "STAT_PROVIDER_REQUEST_REFUSED"


def test_provider_contracts_are_frozen_and_limits_are_positive() -> None:
    limits = ResourceLimits(max_rows=10, max_bytes=1024)
    with pytest.raises(FrozenInstanceError):
        limits.max_rows = 11
    with pytest.raises(ValueError, match="positive"):
        ResourceLimits(max_rows=0)
    with pytest.raises(ValueError, match="same length"):
        DataRequest(columns=("value",), logical_types=())


def test_provider_modules_have_no_heavy_or_database_imports() -> None:
    root = Path(__file__).parents[3] / "src/seshat/statistical/providers"
    forbidden = {
        "numpy",
        "scipy",
        "statsmodels",
        "ruptures",
        "pandas",
        "psycopg",
        "psycopg2",
        "sqlalchemy",
    }
    imported: set[str] = set()
    for path in root.glob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name.split(".", 1)[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module.split(".", 1)[0])
    assert imported.isdisjoint(forbidden)
