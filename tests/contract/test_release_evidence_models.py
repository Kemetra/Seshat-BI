from __future__ import annotations

import json
from pathlib import Path

import pytest

from seshat.release_evidence import (
    ApprovalScope,
    EvidenceValidationError,
    validate_external_acceptance,
    validate_publication_approval,
    validate_release_candidate,
    validate_rollback_record,
)

pytestmark = pytest.mark.unit

ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "tests" / "fixtures" / "public_distribution"


def _fixture(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def test_valid_release_candidate_and_no_score_rule() -> None:
    record = _fixture("release-candidate.valid.json")
    assert validate_release_candidate(record) is record
    with pytest.raises(EvidenceValidationError, match="prohibited"):
        validate_release_candidate({**record, "readiness_score": 100})


def test_blocked_candidate_requires_concrete_blocker() -> None:
    record = _fixture("release-candidate.valid.json")
    with pytest.raises(EvidenceValidationError, match="requires concrete blockers"):
        validate_release_candidate({**record, "status": "blocked", "blockers": []})


def test_acceptance_requires_external_fresh_workspace_and_truthful_result() -> None:
    record = _fixture("acceptance-run.valid.json")
    assert validate_external_acceptance(record) is record
    with pytest.raises(EvidenceValidationError, match="hide the development"):
        validate_external_acceptance({**record, "development_repo_available": True})
    with pytest.raises(EvidenceValidationError, match="fabricated"):
        validate_external_acceptance({**record, "fabricated_score": True})


def test_approval_is_named_and_exactly_action_scoped() -> None:
    record = _fixture("approval-record.valid.json")
    assert (
        validate_publication_approval(
            record,
            ApprovalScope(
                candidate_id="candidate-0.2.0-0123456789ab",
                version="0.2.0",
                source_revision="0123456789abcdef0123456789abcdef01234567",
                artifact_digests={
                    "seshat_bi-0.2.0-py3-none-any.whl": "a" * 64,
                    "seshat_bi-0.2.0.tar.gz": "b" * 64,
                },
                action="publish_pypi",
            ),
        )
        is record
    )
    with pytest.raises(EvidenceValidationError, match="action scope"):
        validate_publication_approval(
            record, ApprovalScope(action="publish_github_release")
        )
    with pytest.raises(EvidenceValidationError, match="approver"):
        validate_publication_approval({**record, "approver": ""})


def test_rollback_requires_named_actor_and_separate_approval_reference() -> None:
    record = {
        "schema_version": "1.0",
        "rollback_id": "rollback-pypi-001",
        "candidate_id": "candidate-0.2.0-0123456789ab",
        "surface": "python_pypi",
        "trigger": "artifact integrity mismatch",
        "actor": "Named Release Owner",
        "action": "rollback_pypi",
        "status": "completed",
        "blockers": [],
        "recorded_at": "2026-07-13T01:00:00Z",
        "approval_id": "approval-rollback-pypi-001",
    }
    assert validate_rollback_record(record) is record
    with pytest.raises(EvidenceValidationError, match="approval_id"):
        validate_rollback_record({**record, "approval_id": ""})
