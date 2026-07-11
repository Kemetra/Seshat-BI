from __future__ import annotations

from pathlib import Path

import pytest

from seshat.packs.validator import validate_pack

pytestmark = pytest.mark.unit

_MANIFEST = """\
schema_version: "1.0"
pack_id: acme.retail-kpis
version: "1.0.0"
category: kpi
owner: "Casey Analyst"
description: "Generic KPI starter content."
core_compatibility: "1.x"
provides: [net-sales-template]
requires: []
conflicts: []
artifacts:
  - path: artifacts/net-sales.yaml
    purpose: "KPI template"
human_decisions:
  - "A named owner approves each KPI definition."
fixtures: []
verification:
  - "retail pack validate --repo . --pack packs/local/acme/seshat-pack.yaml"
non_goals:
  - "Does not grant any approval."
"""


def _write_pack(root: Path, manifest: str = _MANIFEST) -> Path:
    pack_dir = root / "packs/local/acme"
    (pack_dir / "artifacts").mkdir(parents=True)
    (pack_dir / "artifacts/net-sales.yaml").write_text("kpi: x\n", encoding="utf-8")
    manifest_path = pack_dir / "seshat-pack.yaml"
    manifest_path.write_text(manifest, encoding="utf-8")
    return manifest_path


def _rules(findings: list[dict]) -> set[str]:
    return {finding["rule"] for finding in findings}


def test_valid_manifest_parses_into_model_with_no_findings(tmp_path: Path) -> None:
    manifest_path = _write_pack(tmp_path)
    manifest, findings = validate_pack(tmp_path, manifest_path)
    assert findings == []
    assert manifest is not None
    assert manifest.pack_id == "acme.retail-kpis"
    assert manifest.category == "kpi"
    assert manifest.qualified_provides() == ("acme.retail-kpis:net-sales-template",)


def test_schema_invalid_manifest_fails_closed(tmp_path: Path) -> None:
    manifest_path = _write_pack(
        tmp_path, _MANIFEST.replace("category: kpi", "category: everything")
    )
    manifest, findings = validate_pack(tmp_path, manifest_path)
    assert manifest is None
    assert _rules(findings) == {"pack_schema"}


def test_unreadable_manifest_fails_closed(tmp_path: Path) -> None:
    manifest, findings = validate_pack(tmp_path, "packs/absent/seshat-pack.yaml")
    assert manifest is None
    assert _rules(findings) == {"pack_unreadable"}


def test_bad_namespace_local_id_is_rejected(tmp_path: Path) -> None:
    manifest_path = _write_pack(
        tmp_path,
        _MANIFEST.replace("provides: [net-sales-template]", 'provides: ["Net Sales!"]'),
    )
    _, findings = validate_pack(tmp_path, manifest_path)
    assert "pack_namespace" in _rules(findings)


def test_executable_artifact_is_rejected(tmp_path: Path) -> None:
    manifest_path = _write_pack(
        tmp_path,
        _MANIFEST.replace("artifacts/net-sales.yaml", "artifacts/hook.py"),
    )
    (tmp_path / "packs/local/acme/artifacts/hook.py").write_text(
        "print('no')\n", encoding="utf-8"
    )
    _, findings = validate_pack(tmp_path, manifest_path)
    assert "pack_executable_content" in _rules(findings)


_ARTIFACT_LINES = '  - path: artifacts/net-sales.yaml\n    purpose: "KPI template"'

# Forbidden manifest content: (old text, replacement, expected finding rule).
_FORBIDDEN_CONTENT = {
    "hook_key": (
        _ARTIFACT_LINES,
        _ARTIFACT_LINES + "\n    on_load: run",
        "pack_executable_content",
    ),
    "secret_material": (
        'description: "Generic KPI starter content."',
        'description: "Connect via postgresql://user:pw@host/db"',
        "pack_secret",
    ),
    "stage_declaration": (
        _ARTIFACT_LINES,
        _ARTIFACT_LINES + "\n    stage_order: [gold_ready, source_ready]",
        "pack_stage_change",
    ),
    "authority_escalation": (
        '"A named owner approves each KPI definition."',
        '"This pack auto-approves mapping gates."',
        "pack_authority",
    ),
    "universal_schema_claim": (
        "Generic KPI starter content.",
        "A universal schema for every retailer.",
        "pack_universal_claim",
    ),
}


@pytest.mark.parametrize("case", sorted(_FORBIDDEN_CONTENT))
def test_forbidden_manifest_content_is_rejected(tmp_path: Path, case: str) -> None:
    old, new, expected_rule = _FORBIDDEN_CONTENT[case]
    manifest_path = _write_pack(tmp_path, _MANIFEST.replace(old, new))
    _, findings = validate_pack(tmp_path, manifest_path)
    assert expected_rule in _rules(findings)


def test_missing_declared_artifact_is_reported(tmp_path: Path) -> None:
    manifest_path = _write_pack(tmp_path)
    (tmp_path / "packs/local/acme/artifacts/net-sales.yaml").unlink()
    _, findings = validate_pack(tmp_path, manifest_path)
    assert "pack_artifact_missing" in _rules(findings)


def test_escaping_artifact_path_is_reported(tmp_path: Path) -> None:
    manifest_path = _write_pack(
        tmp_path,
        _MANIFEST.replace("artifacts/net-sales.yaml", "../../../../etc/passwd.yaml"),
    )
    _, findings = validate_pack(tmp_path, manifest_path)
    assert "pack_artifact_escape" in _rules(findings)
