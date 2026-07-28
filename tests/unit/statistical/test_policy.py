"""Authority-gate tests for governed statistical analysis."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest
import yaml

from seshat.statistical.policy import evaluate_policy
from seshat.statistical.schema import load_analysis_spec

pytestmark = pytest.mark.unit

_FIXTURE = Path(__file__).parents[2] / "fixtures" / "statistical" / "policy_repo"


def _repo(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    shutil.copytree(_FIXTURE, root)
    schema_dir = root / "schemas"
    schema_dir.mkdir()
    shutil.copy2(
        Path(__file__).parents[3] / "schemas" / "statistical-analysis-spec.schema.json",
        schema_dir,
    )
    return root


def _load(root: Path):
    path = root / "mappings/sample/analyses/weekly_metric_signal.yaml"
    return load_analysis_spec(path, root)


def _edit(path: Path, mutate) -> None:
    document = yaml.safe_load(path.read_text(encoding="utf-8"))
    mutate(document)
    path.write_text(yaml.safe_dump(document, sort_keys=False), encoding="utf-8")


def test_valid_policy_resolves_immutable_authority_context(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    decision = evaluate_policy(root, _load(root))

    assert decision.allowed is True
    assert decision.blockers == ()
    assert decision.context is not None
    assert decision.context.subject == "sample"
    assert decision.context.readiness_revision == "7"
    assert decision.context.approved_tables == frozenset({"gold.sample"})
    assert decision.context.approved_columns == {
        "gold.sample": frozenset({"metric_value"})
    }
    assert tuple(contract.name for contract in decision.context.contracts) == (
        "ApprovedMetric",
    )


@pytest.mark.parametrize(
    ("mutation", "expected"),
    [
        (
            lambda root: _edit(
                root / "mappings/sample/readiness-status.yaml",
                lambda doc: doc["stages"]["gold_ready"].update(status="blocked"),
            ),
            "STAT_GOLD_NOT_READY",
        ),
        (
            lambda root: _edit(
                root / "mappings/sample/readiness-status.yaml",
                lambda doc: doc["stages"]["gold_ready"].update(
                    evidence=["warehouse migration"]
                ),
            ),
            "STAT_LIVE_VALIDATION_MISSING",
        ),
        (
            # Negative evidence must never read as a successful live run.
            lambda root: _edit(
                root / "mappings/sample/readiness-status.yaml",
                lambda doc: doc["stages"]["gold_ready"].update(
                    evidence=["retail validate did not pass"]
                ),
            ),
            "STAT_LIVE_VALIDATION_MISSING",
        ),
        (
            # A bare verdict word is not proof; the exit status is.
            lambda root: _edit(
                root / "mappings/sample/readiness-status.yaml",
                lambda doc: doc["stages"]["gold_ready"].update(
                    evidence=["retail validate: PASS"]
                ),
            ),
            "STAT_LIVE_VALIDATION_MISSING",
        ),
        (
            lambda root: _edit(
                root / "mappings/sample/readiness-status.yaml",
                lambda doc: doc["stages"]["semantic_model_ready"].update(
                    status="blocked"
                ),
            ),
            "STAT_SEMANTIC_NOT_READY",
        ),
        (
            lambda root: _edit(
                root / "mappings/sample/metrics/ApprovedMetric.yaml",
                lambda doc: doc["readiness"].update(status="blocked"),
            ),
            "STAT_CONTRACT_NOT_APPROVED",
        ),
        (
            lambda root: _edit(
                root / "mappings/sample/metrics/ApprovedMetric.yaml",
                lambda doc: doc["binds_to"].update(gold_table="silver.sample"),
            ),
            "STAT_NON_GOLD_BINDING",
        ),
        (
            lambda root: _edit(
                root / "mappings/sample/metrics/ApprovedMetric.yaml",
                lambda doc: doc["binds_to"].update(pii_sensitive=True),
            ),
            "STAT_PII_APPROVAL_MISSING",
        ),
        (
            lambda root: _edit(
                root / "mappings/sample/metrics/ApprovedMetric.yaml",
                lambda doc: doc.update(grain="one row per transaction"),
            ),
            "STAT_GRAIN_CONFLICT",
        ),
    ],
)
def test_policy_refuses_each_governance_failure(
    tmp_path: Path, mutation, expected: str
) -> None:
    root = _repo(tmp_path)
    mutation(root)
    readiness = root / "mappings/sample/readiness-status.yaml"
    before = readiness.read_bytes()

    decision = evaluate_policy(root, _load(root))

    assert decision.allowed is False
    assert expected in {blocker.code for blocker in decision.blockers}
    assert decision.context is None
    assert readiness.read_bytes() == before


def test_policy_reports_all_blockers_in_stable_code_order(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    readiness = root / "mappings/sample/readiness-status.yaml"
    contract = root / "mappings/sample/metrics/ApprovedMetric.yaml"
    _edit(
        readiness,
        lambda doc: (
            doc["stages"]["gold_ready"].update(
                status="blocked", evidence=["warehouse migration"]
            ),
            doc["stages"]["semantic_model_ready"].update(status="blocked"),
        ),
    )
    _edit(
        contract,
        lambda doc: (
            doc["binds_to"].update(gold_table="silver.sample", pii_sensitive=True),
            doc.update(grain="one row per transaction"),
        ),
    )

    decision = evaluate_policy(root, _load(root))

    assert [blocker.code for blocker in decision.blockers] == [
        "STAT_GOLD_NOT_READY",
        "STAT_LIVE_VALIDATION_MISSING",
        "STAT_SEMANTIC_NOT_READY",
        "STAT_NON_GOLD_BINDING",
        "STAT_PII_APPROVAL_MISSING",
        "STAT_GRAIN_CONFLICT",
    ]


def test_policy_refuses_role_outside_approved_contract_columns(
    tmp_path: Path,
) -> None:
    root = _repo(tmp_path)
    spec_path = root / "mappings/sample/analyses/weekly_metric_signal.yaml"
    _edit(
        spec_path,
        lambda doc: doc["roles"]["response"].update(column="unapproved_value"),
    )

    decision = evaluate_policy(root, _load(root))

    assert [blocker.code for blocker in decision.blockers] == [
        "STAT_CONTRACT_NOT_APPROVED"
    ]
