from __future__ import annotations

import copy
import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from scripts.release_candidate_audit import audit_candidate
from seshat.release_evidence import (
    EvidenceValidationError,
    RollbackAuthorizationRequest,
    validate_rollback_authorization,
    validate_surface_availability,
)

pytestmark = pytest.mark.integration

ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "tests/fixtures/public_distribution"
SOURCE_REVISION = "0123456789abcdef0123456789abcdef01234567"
ARTIFACT_DIGESTS = {
    "seshat_bi-0.2.0-py3-none-any.whl": "a" * 64,
    "seshat_bi-0.2.0.tar.gz": "b" * 64,
}


def test_dry_run_evidence_pack_is_sanitized_and_non_authorizing() -> None:
    report = audit_candidate(ROOT, allow_untracked_inputs=True)
    manifest = report["evidence_manifest"]
    assert manifest["candidate_id"] == report["candidate_id"]
    assert manifest["publication_approval"] is None
    assert set(manifest["artifact_digests"]) == {
        "claude-bundle-manifest",
        "codex-bundle-manifest",
    }
    assert set(manifest["repository_check_statuses"].values()) == {"pass"}
    validate_surface_availability(manifest["surface_availability"])
    rendered = json.dumps(manifest)
    assert "approval-record.valid" not in rendered
    assert "score" not in rendered.casefold()
    assert "C:\\Users\\" not in rendered


def test_rollback_is_surface_scoped_and_replacement_is_not_authorized() -> None:
    rollback = json.loads(
        (FIXTURES / "rollback-record.valid.json").read_text(encoding="utf-8")
    )
    approval = json.loads(
        (FIXTURES / "approval-record.valid.json").read_text(encoding="utf-8")
    )
    approval.update(
        {
            "approval_id": rollback["approval_id"],
            "action": rollback["action"],
            "scope": "Yank only the affected candidate from PyPI.",
        }
    )
    validate_rollback_authorization(
        rollback,
        approval,
        RollbackAuthorizationRequest(
            version="0.2.0",
            source_revision=SOURCE_REVISION,
            artifact_digests=ARTIFACT_DIGESTS,
            at=datetime(2026, 7, 13, 12, tzinfo=timezone.utc),
        ),
    )

    reused = copy.deepcopy(approval)
    reused["action"] = "publish_pypi"
    with pytest.raises(EvidenceValidationError, match="does not match"):
        validate_rollback_authorization(
            rollback,
            reused,
            RollbackAuthorizationRequest(
                version="0.2.0",
                source_revision=SOURCE_REVISION,
                artifact_digests=ARTIFACT_DIGESTS,
                at=datetime(2026, 7, 13, 12, tzinfo=timezone.utc),
            ),
        )
