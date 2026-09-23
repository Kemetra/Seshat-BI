"""Decision gate: per-category and per-scope coverage (audit F002/F011/F013).

A stage used to pass as soon as ANY in-scope category held one approved
decision, and the verdict aggregated the whole store regardless of which
table/report asked. String-typed approval evidence also skipped the staleness
check in both the gate and DS2.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from seshat.core import RuleContext
from seshat.decision_gate import evidence_stale, verdict_for
from seshat.rules.decision_store import check_ds2

pytestmark = pytest.mark.unit

_REPO_ROOT = Path(__file__).resolve().parents[2]
_FLOW_REL = "contracts/knowledge/database-to-pbip-flow.yaml"
_AUTHORITY_REL = "contracts/knowledge/approval-authority.yaml"
_STORE = ".seshat/kpi-contracts.yaml"


def _repo(tmp_path: Path, store: str) -> tuple[Path, tuple[str, ...]]:
    files = {
        _STORE: store,
        _FLOW_REL: (_REPO_ROOT / _FLOW_REL).read_text(encoding="utf-8"),
        _AUTHORITY_REL: (_REPO_ROOT / _AUTHORITY_REL).read_text(encoding="utf-8"),
    }
    for rel, body in files.items():
        path = tmp_path / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(body, encoding="utf-8")
    return tmp_path, tuple(files)


def _approved(
    root: Path, dtype: str, did: str, owner: str, scope: str, evidence: str = ""
) -> str:
    ev = root / "ev.md"
    ev.write_text("evidence\n", encoding="utf-8")
    sha = hashlib.sha256(ev.read_bytes()).hexdigest()
    evidence = (
        evidence
        or f"      evidence: [ev.md]\n      evidence_identity: {{ev.md: {sha}}}\n"
    )
    return (
        f"  - id: {did}\n"
        f"    decision_type: {dtype}\n"
        "    statement: s\n"
        f"    scope: {scope}\n"
        "    status: approved\n"
        "    evidence: [ev.md]\n"
        "    proposed_by: agent\n"
        '    proposed_at: "2026-01-01"\n'
        "    approval:\n"
        f'      approved_by: "{owner}"\n'
        '      approved_at: "2026-01-02"\n'
        "      source: interview\n"
        f"{evidence}"
        f"      reviewed_scope: {scope}\n"
    )


def _kpi_only(tmp_path: Path) -> tuple[Path, tuple[str, ...]]:
    body = _approved(
        tmp_path,
        "kpi_definition",
        "kpi_definition.net_sales",
        "A. Owner (metric_owner)",
        "{kpis: [net_sales]}",
    )
    return _repo(tmp_path, "decisions:\n" + body)


@pytest.mark.parametrize(
    "stage", ["report_intent", "dashboard_blueprint", "pbip_prototype_readiness"]
)
def test_kpi_definition_alone_does_not_pass_dashboard_stages(
    tmp_path: Path, stage: str
) -> None:
    root, tracked = _kpi_only(tmp_path)
    verdict = verdict_for(root, tracked, stage)
    assert verdict.verdict == "blocked", verdict
    assert any("no approved" in b.reason for b in verdict.blocking)


def test_kpi_definition_alone_still_passes_kpi_contracts(tmp_path: Path) -> None:
    root, tracked = _kpi_only(tmp_path)
    assert verdict_for(root, tracked, "kpi_contracts").verdict == "pass"


def test_pii_alone_does_not_pass_silver_gold(tmp_path: Path) -> None:
    body = _approved(
        tmp_path,
        "pii_handling",
        "pii_handling.email",
        "A. Owner (data_owner)",
        "{tables: [a]}",
    )
    root, tracked = _repo(tmp_path, "decisions:\n" + body)
    verdict = verdict_for(root, tracked, "silver_gold_model_planning")
    assert verdict.verdict == "blocked"
    assert any("table_grain" in b.reason for b in verdict.blocking)


def _report_intent(tmp_path: Path, artifact: str) -> tuple[Path, tuple[str, ...]]:
    body = _approved(
        tmp_path,
        "report_intent_approval",
        f"report_intent_approval.{artifact}",
        "R. Owner (report_owner)",
        f"{{artifacts: [{artifact}]}}",
    )
    return _repo(tmp_path, "decisions:\n" + body)


def test_scoped_approval_passes_its_own_scope(tmp_path: Path) -> None:
    root, tracked = _report_intent(tmp_path, "report_a")
    verdict = verdict_for(root, tracked, "report_intent", scope=("artifacts:report_a",))
    assert verdict.verdict == "pass", verdict


def test_scoped_approval_does_not_pass_another_scope(tmp_path: Path) -> None:
    root, tracked = _report_intent(tmp_path, "report_a")
    verdict = verdict_for(root, tracked, "report_intent", scope=("artifacts:report_b",))
    assert verdict.verdict == "blocked"


def test_empty_scope_request_matches_nothing(tmp_path: Path) -> None:
    root, tracked = _report_intent(tmp_path, "report_a")
    assert verdict_for(root, tracked, "report_intent", scope=()).verdict == "blocked"


def test_string_evidence_is_stale() -> None:
    approval = {"evidence": "does/not/exist.md", "evidence_identity": "whatever"}
    assert evidence_stale(".", approval)
    approval = {"evidence": ["x.md"], "evidence_identity": "whatever"}
    assert evidence_stale(".", approval) == ["x.md"]


def test_string_evidence_blocks_a_critical_decision(tmp_path: Path) -> None:
    string_ev = "      evidence: does/not/exist.md\n      evidence_identity: whatever\n"
    body = _approved(
        tmp_path,
        "table_grain",
        "table_grain.b",
        "A. Owner (data_owner)",
        "{tables: [b]}",
        evidence=string_ev,
    )
    root, tracked = _repo(tmp_path, "decisions:\n" + body)
    verdict = verdict_for(root, tracked, "silver_gold_model_planning")
    assert verdict.verdict == "blocked"
    assert any("stale" in b.reason for b in verdict.blocking)
    findings = check_ds2(RuleContext(repo_root=root, tracked_files=tracked))
    assert any(
        f.rule_id == "DS2" and f.severity.value == "error" and "evidence" in f.message
        for f in findings
    ), findings
