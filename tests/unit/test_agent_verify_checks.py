"""Unit tests for the eleven `seshat agent verify` checks (spec 129).

Per-target checks (install/version/update/uninstall/ide/governance-contract)
are exercised against synthetic ``tmp_path`` fixtures so PASS/BLOCKED/
UNAVAILABLE is deterministic and independent of the real shipped bundle's
content drifting over time. Shared-baseline checks (the four scenario checks
+ readiness routing) exercise PASS against the real committed benchmark
scenarios and governor (mirrors ``test_benchmark_scenarios.py``'s ``_REPO``
pattern) and BLOCKED/UNAVAILABLE against synthetic fixtures.

Every required check is offline: no DB, no network, no running IDE (SC-007).
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from seshat.agent_verify import checks
from seshat.agent_verify.model import PerCheckResult, VerifyTargetSpec
from seshat.agent_verify.targets import (
    UnknownVerifyTargetError,
    marketplace_path_for,
    resolve_target,
    supported_targets,
)

pytestmark = pytest.mark.unit

_REPO = Path(__file__).parents[2]


def _write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding="utf-8")


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _target_spec(
    tmp_path: Path, *, name: str = "claude", ide_surface: bool = False
) -> VerifyTargetSpec:
    manifest_rel = (
        f"integrations/{name}/seshat-bi/.claude-plugin/plugin.json"
        if name == "claude"
        else f"integrations/{name}/seshat-bi/.codex-plugin/plugin.json"
    )
    provenance_rel = f"integrations/{name}/seshat-bi/bundle-manifest.json"
    contract_rel = f"integrations/{name}/seshat-bi/portable-operating-contract.md"
    return VerifyTargetSpec(
        name=name,
        manifest_path=manifest_rel,
        provenance_manifest=provenance_rel,
        version_source=f"{name}_plugin",
        footprint_source=provenance_rel,
        operating_contract=contract_rel,
        ide_surface=ide_surface,
    )


def _write_install_fixture(tmp_path: Path, target_spec: VerifyTargetSpec) -> None:
    _write_json(
        tmp_path / target_spec.manifest_path, {"name": "seshat-bi", "version": "0.2.0"}
    )
    marketplace_rel = marketplace_path_for(target_spec.name)
    _write_json(tmp_path / marketplace_rel, {"plugins": [{"name": "seshat-bi"}]})
    _write_json(
        tmp_path / target_spec.provenance_manifest,
        {"target": target_spec.name, "plugin": "seshat-bi", "entries": []},
    )


# --- result invariant (model) sanity, exercised through real check output --


def test_every_required_check_id_is_covered_once() -> None:
    assert len(checks.REQUIRED_CHECK_IDS) == 11
    assert len(set(checks.REQUIRED_CHECK_IDS)) == 11
    assert set(checks.PER_TARGET_CHECK_IDS) | set(
        checks.SHARED_BASELINE_CHECK_IDS
    ) == set(checks.REQUIRED_CHECK_IDS)


# --- installation & discovery (FR-009/FR-010) ------------------------------


def test_install_discovery_pass_cites_manifest_marketplace_and_provenance(
    tmp_path: Path,
) -> None:
    target_spec = _target_spec(tmp_path)
    _write_install_fixture(tmp_path, target_spec)

    result = checks.install_discovery_check(target_spec, tmp_path)

    assert result.verdict == "PASS"
    assert result.evidence_class == "per_target"
    assert any("plugin manifest resolved" in item for item in result.evidence)
    assert any(
        "marketplace/discovery entry resolved" in item for item in result.evidence
    )
    assert any("provenance manifest resolved" in item for item in result.evidence)


def test_install_discovery_blocked_on_missing_manifest(tmp_path: Path) -> None:
    target_spec = _target_spec(tmp_path)
    # Deliberately do not write the manifest.
    result = checks.install_discovery_check(target_spec, tmp_path)
    assert result.verdict == "BLOCKED"
    assert result.blocking_reasons
    assert target_spec.manifest_path in result.blocking_reasons[0]


def test_install_discovery_blocked_on_marketplace_not_listing_plugin(
    tmp_path: Path,
) -> None:
    target_spec = _target_spec(tmp_path)
    _write_json(
        tmp_path / target_spec.manifest_path, {"name": "seshat-bi", "version": "0.2.0"}
    )
    _write_json(
        tmp_path / marketplace_path_for(target_spec.name),
        {"plugins": [{"name": "other-plugin"}]},
    )
    result = checks.install_discovery_check(target_spec, tmp_path)
    assert result.verdict == "BLOCKED"
    assert any(
        "marketplace entry does not list" in reason
        for reason in result.blocking_reasons
    )


def test_install_discovery_blocked_on_provenance_identity_mismatch(
    tmp_path: Path,
) -> None:
    target_spec = _target_spec(tmp_path)
    _write_json(
        tmp_path / target_spec.manifest_path, {"name": "seshat-bi", "version": "0.2.0"}
    )
    _write_json(
        tmp_path / marketplace_path_for(target_spec.name),
        {"plugins": [{"name": "seshat-bi"}]},
    )
    _write_json(
        tmp_path / target_spec.provenance_manifest,
        {"target": "wrong-target", "plugin": "seshat-bi"},
    )
    result = checks.install_discovery_check(target_spec, tmp_path)
    assert result.verdict == "BLOCKED"
    assert any("identity mismatch" in reason for reason in result.blocking_reasons)


# --- version compatibility (FR-011) ----------------------------------------


def _patch_audit_versions(
    monkeypatch: pytest.MonkeyPatch, projections: list[dict]
) -> None:
    def _fake_audit_versions(repo_root):  # noqa: ANN001 - test double
        return {"projections": projections}

    monkeypatch.setattr(
        "scripts.check_release_versions.audit_versions", _fake_audit_versions
    )


def test_version_compatibility_pass_in_range(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target_spec = _target_spec(tmp_path)
    _patch_audit_versions(
        monkeypatch,
        [
            {
                "surface": "claude_plugin",
                "observed": "0.2.0",
                "expected": "0.2.0",
                "status": "pass",
            }
        ],
    )
    result = checks.version_compatibility_check(target_spec, tmp_path)
    assert result.verdict == "PASS"
    assert "0.2.0" in result.evidence[0]


def test_version_compatibility_blocked_out_of_range_names_both_versions(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target_spec = _target_spec(tmp_path)
    _patch_audit_versions(
        monkeypatch,
        [
            {
                "surface": "claude_plugin",
                "observed": "0.1.0",
                "expected": "0.2.0",
                "status": "blocked",
                "blocking_reason": "claude_plugin version is '0.1.0'; expected '0.2.0'",
            }
        ],
    )
    result = checks.version_compatibility_check(target_spec, tmp_path)
    assert result.verdict == "BLOCKED"
    assert "0.1.0" in result.blocking_reasons[0]
    assert "0.2.0" in result.blocking_reasons[0]


def test_version_compatibility_blocked_when_declaration_absent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target_spec = _target_spec(tmp_path)
    _patch_audit_versions(monkeypatch, [])  # no projection for this surface at all
    result = checks.version_compatibility_check(target_spec, tmp_path)
    assert result.verdict == "BLOCKED"
    assert "no version projection" in result.blocking_reasons[0]


def test_version_compatibility_never_passes_on_absent_declaration(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target_spec = _target_spec(tmp_path)
    _patch_audit_versions(
        monkeypatch,
        [
            {
                "surface": "claude_plugin",
                "observed": None,
                "expected": "0.2.0",
                "status": "blocked",
            }
        ],
    )
    result = checks.version_compatibility_check(target_spec, tmp_path)
    assert result.verdict != "PASS"


# --- update integrity (FR-018) ---------------------------------------------


def _write_bundle_with_manifest(tmp_path: Path, target_spec: VerifyTargetSpec) -> Path:
    bundle_root = (tmp_path / target_spec.provenance_manifest).parent
    file_a = bundle_root / "commands" / "seshat-check.md"
    file_a.parent.mkdir(parents=True, exist_ok=True)
    file_a.write_bytes(b"check command content\n")
    file_b = bundle_root / "README.md"
    file_b.write_bytes(b"readme content\n")
    manifest = {
        "entries": [
            {
                "destination": "commands/seshat-check.md",
                "output_sha256": _sha(file_a.read_bytes()),
            },
            {"destination": "README.md", "output_sha256": _sha(file_b.read_bytes())},
        ]
    }
    _write_json(tmp_path / target_spec.provenance_manifest, manifest)
    return bundle_root


def test_update_integrity_pass_when_hashes_match(tmp_path: Path) -> None:
    target_spec = _target_spec(tmp_path)
    _write_bundle_with_manifest(tmp_path, target_spec)
    result = checks.update_integrity_check(target_spec, tmp_path)
    assert result.verdict == "PASS"
    assert "match their recorded output_sha256" in result.evidence[0]


def test_update_integrity_blocked_on_seeded_drift_names_path_and_hashes(
    tmp_path: Path,
) -> None:
    target_spec = _target_spec(tmp_path)
    bundle_root = _write_bundle_with_manifest(tmp_path, target_spec)
    # Seed drift: mutate one generated file's content without touching the manifest.
    drifted_file = bundle_root / "README.md"
    drifted_file.write_bytes(b"MUTATED content that breaks provenance\n")

    result = checks.update_integrity_check(target_spec, tmp_path)

    assert result.verdict == "BLOCKED"
    assert any("README.md" in reason for reason in result.blocking_reasons)
    assert any(
        "expected sha256" in reason and "observed" in reason
        for reason in result.blocking_reasons
    )


def test_update_integrity_blocked_on_missing_generated_file(tmp_path: Path) -> None:
    target_spec = _target_spec(tmp_path)
    bundle_root = _write_bundle_with_manifest(tmp_path, target_spec)
    (bundle_root / "README.md").unlink()

    result = checks.update_integrity_check(target_spec, tmp_path)

    assert result.verdict == "BLOCKED"
    assert any(
        "README.md" in reason and "missing" in reason
        for reason in result.blocking_reasons
    )


# --- uninstall integrity (FR-019) ------------------------------------------


def test_uninstall_integrity_lists_declared_footprint(tmp_path: Path) -> None:
    target_spec = _target_spec(tmp_path)
    _write_bundle_with_manifest(tmp_path, target_spec)
    result = checks.uninstall_integrity_check(target_spec, tmp_path)
    assert result.verdict == "PASS"
    assert "commands/seshat-check.md" in result.evidence
    assert "README.md" in result.evidence


def test_uninstall_integrity_unavailable_when_footprint_unenumerable(
    tmp_path: Path,
) -> None:
    target_spec = _target_spec(tmp_path)
    # No provenance manifest at all.
    result = checks.uninstall_integrity_check(target_spec, tmp_path)
    assert result.verdict == "UNAVAILABLE"
    assert result.unavailable_reason


def test_uninstall_integrity_unavailable_when_manifest_has_no_entries(
    tmp_path: Path,
) -> None:
    target_spec = _target_spec(tmp_path)
    _write_json(tmp_path / target_spec.provenance_manifest, {"entries": []})
    result = checks.uninstall_integrity_check(target_spec, tmp_path)
    assert result.verdict == "UNAVAILABLE"


# --- IDE surface (FR-020) ---------------------------------------------------


def test_ide_surface_unavailable_when_target_declares_none(tmp_path: Path) -> None:
    target_spec = _target_spec(tmp_path, name="claude", ide_surface=False)
    result = checks.ide_surface_check(target_spec, tmp_path)
    assert result.verdict == "UNAVAILABLE"
    assert "no IDE surface" in result.unavailable_reason


def test_ide_surface_never_pass_or_blocked_when_absent_even_with_interface_present(
    tmp_path: Path,
) -> None:
    target_spec = _target_spec(tmp_path, name="claude", ide_surface=False)
    _write_json(
        tmp_path / target_spec.manifest_path,
        {"name": "seshat-bi", "interface": {"displayName": "Seshat BI"}},
    )
    result = checks.ide_surface_check(target_spec, tmp_path)
    assert result.verdict == "UNAVAILABLE"


def test_ide_surface_pass_when_declared_and_interface_present(tmp_path: Path) -> None:
    target_spec = _target_spec(tmp_path, name="codex", ide_surface=True)
    _write_json(
        tmp_path / target_spec.manifest_path,
        {"name": "seshat-bi", "interface": {"displayName": "Seshat BI"}},
    )
    result = checks.ide_surface_check(target_spec, tmp_path)
    assert result.verdict == "PASS"
    assert "Seshat BI" in result.evidence[0]


def test_ide_surface_blocked_when_declared_but_interface_missing(
    tmp_path: Path,
) -> None:
    target_spec = _target_spec(tmp_path, name="codex", ide_surface=True)
    _write_json(tmp_path / target_spec.manifest_path, {"name": "seshat-bi"})
    result = checks.ide_surface_check(target_spec, tmp_path)
    assert result.verdict == "BLOCKED"


# --- per-target governance-contract presence (FR-012a; SC-005) -------------

_INTACT_CONTRACT = "\n".join(
    ["Hard stops:", ""] + [line for _, line in checks.GOVERNANCE_HARD_STOP_LINES]
)


def test_governance_contract_presence_pass_when_every_hard_stop_line_present(
    tmp_path: Path,
) -> None:
    target_spec = _target_spec(tmp_path)
    (tmp_path / target_spec.operating_contract).parent.mkdir(
        parents=True, exist_ok=True
    )
    (tmp_path / target_spec.operating_contract).write_text(
        _INTACT_CONTRACT, encoding="utf-8"
    )
    result = checks.governance_contract_presence_check(target_spec, tmp_path)
    assert result.verdict == "PASS"
    assert result.evidence_class == "per_target"


def test_governance_contract_presence_tolerates_manual_line_wrapping(
    tmp_path: Path,
) -> None:
    """The real shipped file hard-wraps long bullets across two physical
    lines; the check must not false-BLOCK on that alone."""
    target_spec = _target_spec(tmp_path)
    wrapped = _INTACT_CONTRACT.replace(
        "Never self-grant an approval; grain, ",
        "Never self-grant an approval;\n  grain, ",
    )
    (tmp_path / target_spec.operating_contract).parent.mkdir(
        parents=True, exist_ok=True
    )
    (tmp_path / target_spec.operating_contract).write_text(wrapped, encoding="utf-8")
    result = checks.governance_contract_presence_check(target_spec, tmp_path)
    assert result.verdict == "PASS"


def test_governance_contract_presence_blocked_naming_dropped_hard_stop(
    tmp_path: Path,
) -> None:
    target_spec = _target_spec(tmp_path)
    dropped_line = checks.GOVERNANCE_HARD_STOP_LINES[0][1]
    mutated = _INTACT_CONTRACT.replace(dropped_line, "")
    (tmp_path / target_spec.operating_contract).parent.mkdir(
        parents=True, exist_ok=True
    )
    (tmp_path / target_spec.operating_contract).write_text(mutated, encoding="utf-8")
    result = checks.governance_contract_presence_check(target_spec, tmp_path)
    assert result.verdict == "BLOCKED"
    assert any(
        checks.GOVERNANCE_HARD_STOP_LINES[0][0] in reason
        for reason in result.blocking_reasons
    )


def test_governance_contract_presence_blocked_when_file_missing(tmp_path: Path) -> None:
    target_spec = _target_spec(tmp_path)
    result = checks.governance_contract_presence_check(target_spec, tmp_path)
    assert result.verdict == "BLOCKED"


def test_governance_contract_presence_is_genuinely_per_target(tmp_path: Path) -> None:
    """SC-005: one target's own bundle can drop a hard stop while the other
    target's bundle stays intact -- the verdict is not vacuously identical."""
    claude_spec = _target_spec(tmp_path, name="claude")
    codex_spec = _target_spec(tmp_path, name="codex")
    (tmp_path / claude_spec.operating_contract).parent.mkdir(
        parents=True, exist_ok=True
    )
    (tmp_path / claude_spec.operating_contract).write_text(
        _INTACT_CONTRACT, encoding="utf-8"
    )
    (tmp_path / codex_spec.operating_contract).parent.mkdir(parents=True, exist_ok=True)
    dropped_line = checks.GOVERNANCE_HARD_STOP_LINES[1][1]
    (tmp_path / codex_spec.operating_contract).write_text(
        _INTACT_CONTRACT.replace(dropped_line, ""), encoding="utf-8"
    )

    claude_result = checks.governance_contract_presence_check(claude_spec, tmp_path)
    codex_result = checks.governance_contract_presence_check(codex_spec, tmp_path)

    assert claude_result.verdict == "PASS"
    assert codex_result.verdict == "BLOCKED"


def test_real_shipped_contracts_pass_for_both_targets() -> None:
    """Grounding check against the real committed bundles."""
    for name in ("claude", "codex"):
        result = checks.governance_contract_presence_check(resolve_target(name), _REPO)
        assert result.verdict == "PASS", result.blocking_reasons


# --- shared-baseline governance checks (FR-012 through FR-017) ------------


def test_pii_refusal_pass_against_real_committed_scenario() -> None:
    result = checks.pii_refusal_check(_REPO)
    assert result.verdict == "PASS"
    assert result.evidence_class == "shared_baseline"
    assert "rs-pii-exposure" in result.evidence[0]


def test_no_self_approval_and_no_silver_before_mapping_pass_against_real() -> None:
    self_approval = checks.no_self_approval_check(_REPO)
    silver = checks.no_silver_before_mapping_check(_REPO)
    assert self_approval.verdict == "PASS"
    assert silver.verdict == "PASS"


def test_no_invented_metric_meaning_pass_and_expected_behavior_does_not_proceed() -> (
    None
):
    result = checks.no_invented_metric_meaning_check(_REPO)
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
    result = checks.readiness_routing_check(_REPO)
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
    target_spec = _target_spec(tmp_path, name="claude", ide_surface=False)
    _write_install_fixture(tmp_path, target_spec)
    _write_bundle_with_manifest(tmp_path, target_spec)
    (tmp_path / target_spec.operating_contract).write_text(
        _INTACT_CONTRACT, encoding="utf-8"
    )
    (tmp_path / "benchmark" / "scenarios").mkdir(parents=True, exist_ok=True)
    (tmp_path / "benchmark" / "scenarios" / "hard-stops.yaml").write_text(
        "version: 1\nscenarios: []\n", encoding="utf-8"
    )
    (tmp_path / "benchmark" / "scenarios" / "retail-semantics.yaml").write_text(
        "version: 1\nscenarios: []\n", encoding="utf-8"
    )

    results = checks.run_all_checks(target_spec, tmp_path)

    assert len(results) == 11
    for result in results:
        assert isinstance(result, PerCheckResult)
        assert result.verdict in ("PASS", "BLOCKED", "UNAVAILABLE")


# --- target registry (typed error -> CLI exit 2) ----------------------------


def test_resolve_target_supports_claude_and_codex() -> None:
    assert set(supported_targets()) == {"claude", "codex"}
    assert resolve_target("claude").name == "claude"
    assert resolve_target("codex").name == "codex"


def test_resolve_target_raises_typed_error_for_unknown_target() -> None:
    with pytest.raises(UnknownVerifyTargetError):
        resolve_target("gemini")
