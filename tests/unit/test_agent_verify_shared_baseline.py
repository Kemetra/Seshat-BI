"""Unit tests for the shared-baseline governance checks (the four scenario
checks + readiness routing) and the offline guarantee across all eleven
required checks (spec 129, FR-012 through FR-017, SC-007).

Split out of the former monolithic ``test_agent_verify_checks.py`` to keep
each test module single-purpose (CodeScene Low Cohesion).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from seshat.agent_verify import checks
from seshat.agent_verify.model import PerCheckResult
from tests.unit._agent_verify_fixtures import (
    INTACT_CONTRACT,
    REPO,
    target_spec,
    write_bundle_with_manifest,
    write_install_fixture,
)

pytestmark = pytest.mark.unit


# --- shared-baseline governance checks (FR-012 through FR-017) ------------


def test_pii_refusal_pass_against_real_committed_scenario() -> None:
    result = checks.pii_refusal_check(REPO)
    assert result.verdict == "PASS"
    assert result.evidence_class == "shared_baseline"
    assert "rs-pii-exposure" in result.evidence[0]


def test_no_self_approval_and_no_silver_before_mapping_pass_against_real() -> None:
    self_approval = checks.no_self_approval_check(REPO)
    silver = checks.no_silver_before_mapping_check(REPO)
    assert self_approval.verdict == "PASS"
    assert silver.verdict == "PASS"


def test_scenario_checks_do_not_claim_a_behavioural_reproduction() -> None:
    """F146: the scripted reference echoed the manifest's own expectation, so
    'scripted reference reproduces it' was a tautology. The evidence must say
    the pass is manifest-declared and that no behaviour was executed."""
    for result in (
        checks.no_self_approval_check(REPO),
        checks.no_silver_before_mapping_check(REPO),
        checks.pii_refusal_check(REPO),
    ):
        joined = " ".join(result.evidence)
        assert "reproduces" not in joined
        assert "no Seshat gate or target behaviour was executed" in joined


def test_no_invented_metric_meaning_pass_and_expected_behavior_does_not_proceed() -> (
    None
):
    result = checks.no_invented_metric_meaning_check(REPO)
    assert result.verdict == "PASS"
    assert "proceed" not in result.evidence[0].split("=")[-1]


def test_scenario_baseline_blocked_when_cited_scenario_is_missing(
    tmp_path: Path,
) -> None:
    manifest = tmp_path / "benchmark" / "scenarios" / "hard-stops.yaml"
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text("version: 1\nscenarios: []\n", encoding="utf-8")
    other = tmp_path / "benchmark" / "scenarios" / "retail-semantics.yaml"
    other.write_text("version: 1\nscenarios: []\n", encoding="utf-8")

    result = checks.pii_refusal_check(tmp_path)

    assert result.verdict == "BLOCKED"
    assert "rs-pii-exposure" in result.blocking_reasons[0]


def test_scenario_baseline_blocked_when_manifest_malformed(tmp_path: Path) -> None:
    manifest = tmp_path / "benchmark" / "scenarios" / "hard-stops.yaml"
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text("not: [a, valid, scenario, manifest\n", encoding="utf-8")
    result = checks.no_self_approval_check(tmp_path)
    assert result.verdict == "BLOCKED"


def test_scenario_baseline_blocked_when_baseline_regresses_to_proceed(
    tmp_path: Path,
) -> None:
    fixture_csv = tmp_path / "fixtures" / "data.csv"
    fixture_csv.parent.mkdir(parents=True, exist_ok=True)
    fixture_csv.write_text("col\n1\n", encoding="utf-8")
    manifest = tmp_path / "benchmark" / "scenarios" / "hard-stops.yaml"
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text(
        """version: 1
scenarios:
  - scenario_id: hs-self-grant-approval
    title: "regressed"
    principle: never_self_grant_approval
    fixture: fixtures/data.csv
    prompt: "regressed prompt"
    expected_behavior: proceed
    observable_evidence:
      - "no longer refuses"
    vendor_neutral: true
""",
        encoding="utf-8",
    )
    other = tmp_path / "benchmark" / "scenarios" / "retail-semantics.yaml"
    other.write_text("version: 1\nscenarios: []\n", encoding="utf-8")

    result = checks.no_self_approval_check(tmp_path)

    assert result.verdict == "BLOCKED"
    assert "proceed" in result.blocking_reasons[0]


# --- readiness routing (FR-012; the read-only governor) --------------------


def test_readiness_routing_pass_against_real_repo_governor() -> None:
    result = checks.readiness_routing_check(REPO)
    assert result.verdict == "PASS"
    assert result.evidence_class == "shared_baseline"
    assert any("read_only_proof=True" in item for item in result.evidence)


def test_readiness_routing_unavailable_when_governor_cannot_be_invoked(
    tmp_path: Path,
) -> None:
    missing_dir = tmp_path / "does-not-exist"
    result = checks.readiness_routing_check(missing_dir)
    assert result.verdict == "UNAVAILABLE"
    assert result.unavailable_reason


# --- offline guarantee (SC-007) ---------------------------------------------


def test_every_required_check_completes_offline_with_no_db_or_network(
    tmp_path: Path,
) -> None:
    """No required check needs a DB, network, or a running IDE; an absent
    surface reports UNAVAILABLE and the run still completes truthfully."""
    spec = target_spec(tmp_path, name="claude", ide_surface=False)
    write_install_fixture(tmp_path, spec)
    write_bundle_with_manifest(tmp_path, spec)
    (tmp_path / spec.operating_contract).write_text(INTACT_CONTRACT, encoding="utf-8")
    (tmp_path / "benchmark" / "scenarios").mkdir(parents=True, exist_ok=True)
    (tmp_path / "benchmark" / "scenarios" / "hard-stops.yaml").write_text(
        "version: 1\nscenarios: []\n", encoding="utf-8"
    )
    (tmp_path / "benchmark" / "scenarios" / "retail-semantics.yaml").write_text(
        "version: 1\nscenarios: []\n", encoding="utf-8"
    )

    results = checks.run_all_checks(spec, tmp_path)

    assert len(results) == 11
    for result in results:
        assert isinstance(result, PerCheckResult)
        assert result.verdict in ("PASS", "BLOCKED", "UNAVAILABLE")
