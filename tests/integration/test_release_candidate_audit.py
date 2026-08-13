from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from scripts.release_candidate_audit import audit_candidate, audit_registry

pytestmark = pytest.mark.integration

ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "tests" / "fixtures" / "public_distribution" / "release_audit"


def test_product_candidate_audit_distinguishes_repo_pass_from_release_blocker() -> None:
    # The release blocker is injected rather than read from ambient Git tag state.
    # Asserting on "existing immutable tag vX" coupled this test to whether the
    # checkout happened to carry tags: CI's default shallow, tag-less checkout
    # emitted no such blocker, and the assertion would flip again on every
    # version bump. Injection keeps the repo-pass/release-blocked distinction
    # under test at any checkout depth.
    baseline = audit_candidate(ROOT, allow_untracked_inputs=True)
    candidate_version = baseline["candidate_version"]
    report = audit_candidate(
        ROOT,
        allow_untracked_inputs=True,
        known_immutable_package_versions={candidate_version},
    )

    assert report["repository_status"] == "pass"
    assert report["repository_checks"]["registry"]["kpi_mc_15_count"] == 1
    assert report["status"] == "blocked"
    assert any(
        f"immutable package version {candidate_version}" in item
        for item in report["blocking_reasons"]
    )
    assert "score" not in json.dumps(report).casefold()
    assert report["approval"] is None


@pytest.mark.parametrize(
    ("name", "message"),
    [
        ("duplicate-kpi.yaml", "duplicate KPI registry IDs"),
        ("missing-contract.yaml", "contract does not resolve"),
    ],
)
def test_registry_release_blocker_fixtures(name: str, message: str) -> None:
    document = yaml.safe_load((FIXTURES / name).read_text(encoding="utf-8"))
    report = audit_registry(ROOT, document)
    assert report["status"] == "fail"
    assert any(message in item for item in report["blocking_reasons"])


def test_known_immutable_package_version_blocks_reuse() -> None:
    candidate = audit_candidate(ROOT, allow_untracked_inputs=True)
    candidate_version = candidate["candidate_version"]
    report = audit_candidate(
        ROOT,
        allow_untracked_inputs=True,
        known_immutable_package_versions={candidate_version},
    )
    assert any(
        f"immutable package version {candidate_version}" in item
        for item in report["blocking_reasons"]
    )
