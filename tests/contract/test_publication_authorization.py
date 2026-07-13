from __future__ import annotations

import copy
import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from seshat.release_evidence import (
    ApprovalScope,
    AuthorizationRequest,
    EvidenceValidationError,
    RollbackAuthorizationRequest,
    validate_action_authorization,
    validate_rollback_authorization,
    validate_surface_availability,
)

pytestmark = pytest.mark.unit

ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "tests/fixtures/public_distribution"
AT = datetime(2026, 7, 13, 12, tzinfo=timezone.utc)
SOURCE_REVISION = "0123456789abcdef0123456789abcdef01234567"
ARTIFACT_DIGESTS = {
    "seshat_bi-0.2.0-py3-none-any.whl": "a" * 64,
    "seshat_bi-0.2.0.tar.gz": "b" * 64,
}


def _approval() -> dict[str, object]:
    return json.loads(
        (FIXTURES / "approval-record.valid.json").read_text(encoding="utf-8")
    )


def _availability() -> dict[str, object]:
    return {
        "schema_version": "1.0",
        "surfaces": {
            "python_pypi": {"status": "available", "reason": ""},
            "claude_repository": {
                "status": "unverified",
                "reason": "external acceptance is missing",
            },
            "codex_repository": {
                "status": "unavailable",
                "reason": "repository plugin is not public",
            },
            "claude_public_catalog": {
                "status": "unavailable",
                "reason": "not submitted",
            },
            "openai_public_plugin": {
                "status": "unavailable",
                "reason": "not submitted",
            },
        },
        "coordinated_release_status": "unverified",
        "summary": "Python is available; agent surfaces remain unverified.",
    }


def _request(
    *,
    at: datetime = AT,
    used: set[str] | frozenset[str] = frozenset(),
    **scope: object,
) -> AuthorizationRequest:
    return AuthorizationRequest(
        ApprovalScope(**scope),  # type: ignore[arg-type]
        used_approval_ids=used,
        at=at,
    )


def _rollback_request(*, at: datetime = AT) -> RollbackAuthorizationRequest:
    return RollbackAuthorizationRequest(
        version="0.2.0",
        source_revision=SOURCE_REVISION,
        artifact_digests=ARTIFACT_DIGESTS,
        at=at,
    )


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("candidate_id", "candidate-other"),
        ("version", "9.9.9"),
        ("action", "publish_github_release"),
    ],
)
def test_approval_must_match_exact_candidate_version_and_action(
    field: str, value: str
) -> None:
    expected = {
        "candidate_id": "candidate-0.2.0-0123456789ab",
        "version": "0.2.0",
        "source_revision": SOURCE_REVISION,
        "artifact_digests": ARTIFACT_DIGESTS,
        "action": "publish_pypi",
    }
    expected[field] = value
    with pytest.raises(EvidenceValidationError, match="does not match"):
        validate_action_authorization(_approval(), _request(**expected))


def test_consumed_or_expired_approval_cannot_be_reused() -> None:
    approval = _approval()
    with pytest.raises(EvidenceValidationError, match="already consumed"):
        validate_action_authorization(
            approval,
            _request(
                candidate_id=str(approval["candidate_id"]),
                version=str(approval["version"]),
                source_revision=SOURCE_REVISION,
                artifact_digests=ARTIFACT_DIGESTS,
                action=str(approval["action"]),
                used={str(approval["approval_id"])},
            ),
        )
    with pytest.raises(EvidenceValidationError, match="expired"):
        validate_action_authorization(
            approval,
            _request(
                candidate_id=str(approval["candidate_id"]),
                version=str(approval["version"]),
                source_revision=SOURCE_REVISION,
                artifact_digests=ARTIFACT_DIGESTS,
                action=str(approval["action"]),
                at=datetime(2026, 7, 15, tzinfo=timezone.utc),
            ),
        )


def test_action_authorization_rejects_an_unbound_scope() -> None:
    with pytest.raises(EvidenceValidationError, match="exact action scope"):
        validate_action_authorization(
            _approval(),
            AuthorizationRequest(ApprovalScope(), at=AT),
        )


def test_partial_availability_cannot_claim_a_full_launch() -> None:
    record = _availability()
    validate_surface_availability(record)
    false_claim = copy.deepcopy(record)
    false_claim["coordinated_release_status"] = "available"
    false_claim["summary"] = "The full launch is available."
    with pytest.raises(EvidenceValidationError, match="coordinated release"):
        validate_surface_availability(false_claim)


def test_rollback_requires_its_own_matching_approval() -> None:
    rollback = json.loads(
        (FIXTURES / "rollback-record.valid.json").read_text(encoding="utf-8")
    )
    approval = _approval()
    approval.update(
        {
            "approval_id": rollback["approval_id"],
            "action": "rollback_pypi",
            "scope": "Yank only the affected candidate from PyPI.",
        }
    )
    validate_rollback_authorization(
        rollback,
        approval,
        _rollback_request(),
    )
    approval["action"] = "publish_pypi"
    with pytest.raises(EvidenceValidationError, match="does not match"):
        validate_rollback_authorization(
            rollback,
            approval,
            _rollback_request(),
        )


def test_rollback_action_must_match_its_public_surface() -> None:
    rollback = json.loads(
        (FIXTURES / "rollback-record.valid.json").read_text(encoding="utf-8")
    )
    rollback["surface"] = "codex_repository"
    with pytest.raises(EvidenceValidationError, match="affected public surface"):
        validate_rollback_authorization(
            rollback,
            _approval(),
            _rollback_request(),
        )


def test_approval_rejects_changed_source_or_artifact_digests() -> None:
    approval = _approval()
    common = {
        "candidate_id": str(approval["candidate_id"]),
        "version": str(approval["version"]),
        "artifact_digests": ARTIFACT_DIGESTS,
        "action": str(approval["action"]),
    }
    with pytest.raises(EvidenceValidationError, match="source_revision"):
        validate_action_authorization(
            approval,
            _request(source_revision="f" * 40, **common),
        )
    with pytest.raises(EvidenceValidationError, match="artifact_digests"):
        validate_action_authorization(
            approval,
            _request(
                source_revision=SOURCE_REVISION,
                **{**common, "artifact_digests": {"changed.whl": "c" * 64}},
            ),
        )
