"""DS1-DS5 rule behavior tests (spec 121, T010).

Uses the inline-YAML + tmp_path idiom (RS1's convention). A `.seshat` store is
planted at a non-test path so the rules pick it up; fixtures are self-contained.
Approval-authority eligibility (DS2) is exercised against the real committed
contract via the repo root.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from seshat.core import RuleContext, Severity
from seshat.rules.decision_store import (
    check_ds1,
    check_ds2,
    check_ds3,
    check_ds4,
    check_ds5,
)

pytestmark = pytest.mark.unit

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SEMANTIC = ".seshat/semantic-decisions.yaml"
_KPI = ".seshat/kpi-contracts.yaml"


def _ctx(tmp_path: Path, files: dict[str, str]) -> RuleContext:
    for rel, body in files.items():
        p = tmp_path / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(body, encoding="utf-8")
    return RuleContext(repo_root=tmp_path, tracked_files=tuple(files.keys()))


def _repo_ctx(tmp_path: Path, files: dict[str, str]) -> RuleContext:
    """Context rooted at tmp_path but ALSO exposing the real approval-authority
    contract by copying it in, so DS2 eligibility resolves."""
    contract_rel = "contracts/knowledge/approval-authority.yaml"
    src = (_REPO_ROOT / contract_rel).read_text(encoding="utf-8")
    all_files = dict(files)
    all_files[contract_rel] = src
    return _ctx(tmp_path, all_files)


def _ids(findings, rule_id: str) -> list:
    fs = [f for f in findings if f.rule_id == rule_id]
    return fs


# ---- DS1: layout / vocabulary / id / scope --------------------------------


def test_ds1_clean_store_no_findings(tmp_path: Path) -> None:
    body = (
        "decisions:\n"
        "  - id: table_grain.fct_sales\n"
        "    decision_type: table_grain\n"
        '    statement: "one sale line"\n'
        "    scope: {tables: [fct_sales]}\n"
        "    status: proposed\n"
        "    confidence: high\n"
        "    evidence: [x.md]\n"
        "    proposed_by: agent\n"
        '    proposed_at: "2026-01-01"\n'
    )
    assert list(check_ds1(_ctx(tmp_path, {_SEMANTIC: body}))) == []


def test_ds1_absent_store_passes(tmp_path: Path) -> None:
    # Only a blank template present -> selector never matches -> no findings.
    ctx = _ctx(tmp_path, {"templates/semantic-decisions.yaml": "decisions: []\n"})
    assert list(check_ds1(ctx)) == []


def test_ds1_invalid_status_errors(tmp_path: Path) -> None:
    body = (
        "decisions:\n"
        "  - id: table_grain.x\n"
        "    decision_type: table_grain\n"
        "    statement: s\n"
        "    scope: {tables: [x]}\n"
        "    status: totally_made_up\n"
        "    evidence: [x.md]\n"
        "    proposed_by: agent\n"
        '    proposed_at: "2026-01-01"\n'
    )
    fs = _ids(check_ds1(_ctx(tmp_path, {_SEMANTIC: body})), "DS1")
    assert any("invalid status" in f.message for f in fs)
    assert all(f.severity is Severity.ERROR for f in fs)


def test_ds1_malformed_id_errors(tmp_path: Path) -> None:
    body = (
        "decisions:\n"
        "  - id: Not A Slug!\n"
        "    decision_type: table_grain\n"
        "    statement: s\n"
        "    scope: {tables: [x]}\n"
        "    status: pending\n"
        "    evidence: [x.md]\n"
        "    proposed_by: agent\n"
        '    proposed_at: "2026-01-01"\n'
    )
    assert any(
        "malformed" in f.message
        for f in _ids(check_ds1(_ctx(tmp_path, {_SEMANTIC: body})), "DS1")
    )


def test_ds1_empty_scope_errors(tmp_path: Path) -> None:
    body = (
        "decisions:\n"
        "  - id: table_grain.x\n"
        "    decision_type: table_grain\n"
        "    statement: s\n"
        "    scope: {}\n"
        "    status: pending\n"
        "    evidence: [x.md]\n"
        "    proposed_by: agent\n"
        '    proposed_at: "2026-01-01"\n'
    )
    assert any(
        "scope must name" in f.message
        for f in _ids(check_ds1(_ctx(tmp_path, {_SEMANTIC: body})), "DS1")
    )


def test_ds1_duplicate_id_errors(tmp_path: Path) -> None:
    one = (
        "  - id: table_grain.x\n"
        "    decision_type: table_grain\n"
        "    statement: s\n"
        "    scope: {tables: [x]}\n"
        "    status: pending\n"
        "    evidence: [x.md]\n"
        "    proposed_by: agent\n"
        '    proposed_at: "2026-01-01"\n'
    )
    body = "decisions:\n" + one + one
    assert any(
        "appears 2 times" in f.message
        for f in _ids(check_ds1(_ctx(tmp_path, {_SEMANTIC: body})), "DS1")
    )


def test_ds1_pii_shape_is_warning(tmp_path: Path) -> None:
    body = (
        "decisions:\n"
        "  - id: pii_handling.email\n"
        "    decision_type: pii_handling\n"
        '    statement: "sample value is jane.doe@example.com"\n'
        "    scope: {columns: [c.email]}\n"
        "    status: pending\n"
        "    evidence: [x.md]\n"
        "    proposed_by: agent\n"
        '    proposed_at: "2026-01-01"\n'
    )
    fs = _ids(check_ds1(_ctx(tmp_path, {_SEMANTIC: body})), "DS1")
    pii = [f for f in fs if "raw suspected-PII" in f.message]
    assert pii and all(f.severity is Severity.WARNING for f in pii)


def test_ds1_pii_in_identity_field_is_error(tmp_path: Path) -> None:
    # An email in approved_by (an identity field, not free text) is ERROR, not just
    # WARNING -- it would otherwise render verbatim into the review artifact.
    ev = "x.md"
    body = (
        "decisions:\n"
        "  - id: kpi_definition.net\n"
        "    decision_type: kpi_definition\n"
        "    statement: s\n"
        "    scope: {kpis: [k]}\n"
        "    status: approved\n"
        f"    evidence: [{ev}]\n"
        "    proposed_by: agent\n"
        '    proposed_at: "2026-01-01"\n'
        "    approval:\n"
        '      approved_by: "jane.doe@example.com (metric_owner)"\n'
        '      approved_at: "2026-01-02"\n'
        "      source: interview\n"
        f"      evidence: [{ev}]\n"
        f"      evidence_identity: {{{ev}: abc}}\n"
        "      reviewed_scope: {kpis: [k]}\n"
    )
    fs = _ids(check_ds1(_ctx(tmp_path, {_SEMANTIC: body})), "DS1")
    hits = [f for f in fs if "approved_by" in f.message and "PII" in f.message]
    assert hits and all(f.severity is Severity.ERROR for f in hits)


def test_ds1_secret_in_field_is_error(tmp_path: Path) -> None:
    body = (
        "decisions:\n"
        "  - id: table_grain.x\n"
        "    decision_type: table_grain\n"
        '    statement: "connect with password=Sup3rSecret per owner"\n'
        "    scope: {tables: [x]}\n"
        "    status: pending\n"
        "    evidence: [x.md]\n"
        "    proposed_by: agent\n"
        '    proposed_at: "2026-01-01"\n'
    )
    fs = _ids(check_ds1(_ctx(tmp_path, {_SEMANTIC: body})), "DS1")
    hits = [f for f in fs if "secret/credential" in f.message]
    assert hits and all(f.severity is Severity.ERROR for f in hits)


def test_ds1_malformed_yaml_fails_closed(tmp_path: Path) -> None:
    fs = _ids(
        check_ds1(_ctx(tmp_path, {_SEMANTIC: "decisions: [\n unterminated"})), "DS1"
    )
    assert any("not valid YAML" in f.message for f in fs)


# ---- DS2: approval metadata + eligibility ---------------------------------


def _approved(dtype: str, did: str, approver: str, *, drop: str = "") -> str:
    lines = [
        "decisions:",
        f"  - id: {did}",
        f"    decision_type: {dtype}",
        "    statement: s",
        "    scope: {kpis: [k]}",
        "    status: approved",
        "    confidence: high",
        "    evidence: [x.md]",
        "    proposed_by: agent",
        '    proposed_at: "2026-01-01"',
        "    approval:",
        f'      approved_by: "{approver}"',
        '      approved_at: "2026-01-02"',
        "      source: interview",
        "      evidence: [x.md]",
        '      evidence_identity: {x.md: "abc123"}',
        "      reviewed_scope: {kpis: [k]}",
    ]
    return "\n".join(ln for ln in lines if not (drop and drop in ln)) + "\n"


def test_ds2_valid_eligible_approval_passes(tmp_path: Path) -> None:
    body = _approved("kpi_definition", "kpi_definition.net", "A. Owner (metric_owner)")
    ctx = _repo_ctx(tmp_path, {_KPI: body})
    assert _ids(check_ds2(ctx), "DS2") == []


def test_ds2_ineligible_authority_class_errors(tmp_path: Path) -> None:
    # report_owner is not eligible to approve a kpi_definition (metric_owner is).
    body = _approved("kpi_definition", "kpi_definition.net", "A. Person (report_owner)")
    fs = _ids(check_ds2(_repo_ctx(tmp_path, {_KPI: body})), "DS2")
    assert any("ineligible" in f.message for f in fs)


def test_ds2_bare_role_owner_errors(tmp_path: Path) -> None:
    body = _approved("kpi_definition", "kpi_definition.net", "metric_owner")
    fs = _ids(check_ds2(_repo_ctx(tmp_path, {_KPI: body})), "DS2")
    assert any("invalid approved_by" in f.message for f in fs)


def test_ds2_missing_evidence_identity_errors(tmp_path: Path) -> None:
    body = _approved(
        "kpi_definition",
        "kpi_definition.net",
        "A. Owner (metric_owner)",
        drop="evidence_identity",
    )
    fs = _ids(check_ds2(_repo_ctx(tmp_path, {_KPI: body})), "DS2")
    assert any("evidence_identity" in f.message for f in fs)


def test_ds2_approved_without_approval_block_errors(tmp_path: Path) -> None:
    body = (
        "decisions:\n"
        "  - id: kpi_definition.net\n"
        "    decision_type: kpi_definition\n"
        "    statement: s\n"
        "    scope: {kpis: [k]}\n"
        "    status: approved\n"
        "    evidence: [x.md]\n"
        "    proposed_by: agent\n"
        '    proposed_at: "2026-01-01"\n'
    )
    fs = _ids(check_ds2(_repo_ctx(tmp_path, {_KPI: body})), "DS2")
    assert any("no approval block" in f.message for f in fs)


# ---- DS3: batch integrity -------------------------------------------------


def test_ds3_critical_type_in_batch_errors(tmp_path: Path) -> None:
    body = (
        "decisions:\n"
        "  - id: pii_handling.x\n"
        "    decision_type: pii_handling\n"
        "    statement: s\n"
        "    scope: {columns: [c]}\n"
        "    status: approved\n"
        "    confidence: high\n"
        "    evidence: [x.md]\n"
        "    proposed_by: agent\n"
        '    proposed_at: "2026-01-01"\n'
        "    batch_id: batch.lowrisk\n"
        "batches:\n"
        "  - batch_id: batch.lowrisk\n"
        '    presented_at: "2026-01-01"\n'
        "    members: [pii_handling.x]\n"
        '    confirmed_by: "A. Owner (data_owner)"\n'
        '    confirmed_at: "2026-01-01"\n'
        "    evidence: [x.md]\n"
    )
    fs = _ids(check_ds3(_ctx(tmp_path, {_SEMANTIC: body})), "DS3")
    assert any("critical decision" in f.message for f in fs)


def test_ds3_invalid_confirmed_by_errors(tmp_path: Path) -> None:
    body = (
        "decisions:\n"
        "  - id: naming.x\n"
        "    decision_type: naming\n"
        "    statement: s\n"
        "    scope: {columns: [c]}\n"
        "    status: approved\n"
        "    confidence: high\n"
        "    evidence: [x.md]\n"
        "    proposed_by: agent\n"
        '    proposed_at: "2026-01-01"\n'
        "batches:\n"
        "  - batch_id: batch.a\n"
        '    presented_at: "2026-01-01"\n'
        "    members: [naming.x]\n"
        "    confirmed_by: owner\n"
        '    confirmed_at: "2026-01-01"\n'
        "    evidence: [x.md]\n"
    )
    fs = _ids(check_ds3(_ctx(tmp_path, {_SEMANTIC: body})), "DS3")
    assert any("invalid confirmed_by" in f.message for f in fs)


# ---- DS4: supersession + conflicts ----------------------------------------


def test_ds4_unresolved_supersede_ref_errors(tmp_path: Path) -> None:
    body = (
        "decisions:\n"
        "  - id: table_grain.x.2\n"
        "    decision_type: table_grain\n"
        "    statement: s\n"
        "    scope: {tables: [x]}\n"
        "    status: proposed\n"
        "    confidence: high\n"
        "    evidence: [x.md]\n"
        "    proposed_by: agent\n"
        '    proposed_at: "2026-01-01"\n'
        "    supersedes: table_grain.x.does_not_exist\n"
    )
    fs = _ids(check_ds4(_ctx(tmp_path, {_SEMANTIC: body})), "DS4")
    assert any("does not resolve" in f.message for f in fs)


def test_ds4_conflicting_active_records_errors(tmp_path: Path) -> None:
    rec = (
        "  - id: {did}\n"
        "    decision_type: table_grain\n"
        "    statement: s\n"
        "    scope: {{tables: [fct_sales]}}\n"
        "    status: proposed\n"
        "    confidence: high\n"
        "    evidence: [x.md]\n"
        "    proposed_by: agent\n"
        '    proposed_at: "2026-01-01"\n'
    )
    body = (
        "decisions:\n"
        + rec.format(did="table_grain.a")
        + rec.format(did="table_grain.b")
    )
    fs = _ids(check_ds4(_ctx(tmp_path, {_SEMANTIC: body})), "DS4")
    assert any("conflicting active" in f.message for f in fs)


def test_ds4_superseded_without_ref_errors(tmp_path: Path) -> None:
    body = (
        "decisions:\n"
        "  - id: table_grain.x\n"
        "    decision_type: table_grain\n"
        "    statement: s\n"
        "    scope: {tables: [x]}\n"
        "    status: superseded\n"
        "    evidence: [x.md]\n"
        "    proposed_by: agent\n"
        '    proposed_at: "2026-01-01"\n'
    )
    fs = _ids(check_ds4(_ctx(tmp_path, {_SEMANTIC: body})), "DS4")
    assert any("no superseded_by" in f.message for f in fs)


# ---- DS5: verdict-consistency store invariant -----------------------------


def test_ds5_approved_without_evidence_errors(tmp_path: Path) -> None:
    body = (
        "decisions:\n"
        "  - id: kpi_definition.net\n"
        "    decision_type: kpi_definition\n"
        "    statement: s\n"
        "    scope: {kpis: [k]}\n"
        "    status: approved\n"
        "    evidence: []\n"
        "    proposed_by: agent\n"
        '    proposed_at: "2026-01-01"\n'
        "    approval:\n"
        '      approved_by: "A. Owner (metric_owner)"\n'
        '      approved_at: "2026-01-02"\n'
        "      source: interview\n"
        "      evidence: []\n"
        "      evidence_identity: {}\n"
        "      reviewed_scope: {kpis: [k]}\n"
    )
    fs = _ids(check_ds5(_ctx(tmp_path, {_KPI: body})), "DS5")
    assert any("no evidence" in f.message for f in fs)


# ---- adversarial-review coverage gaps -------------------------------------


@pytest.mark.parametrize(
    "key",
    [
        "approved_by",
        "approved_at",
        "source",
        "evidence",
        "evidence_identity",
        "reviewed_scope",
    ],
)
def test_ds2_each_missing_required_key_errors(tmp_path: Path, key: str) -> None:
    # SC-002: every seeded incomplete approval is detected. Drop one required key
    # at a time and assert DS2 flags it.
    body = _approved(
        "kpi_definition", "kpi_definition.net", "A. Owner (metric_owner)", drop=key
    )
    fs = _ids(check_ds2(_repo_ctx(tmp_path, {_KPI: body})), "DS2")
    assert any(key in f.message for f in fs), key


def test_ds4_dangling_superseded_by_errors(tmp_path: Path) -> None:
    body = (
        "decisions:\n"
        "  - id: table_grain.x\n"
        "    decision_type: table_grain\n"
        "    statement: s\n"
        "    scope: {tables: [x]}\n"
        "    status: proposed\n"
        "    confidence: high\n"
        "    evidence: [x.md]\n"
        "    proposed_by: agent\n"
        '    proposed_at: "2026-01-01"\n'
        "    superseded_by: table_grain.nope\n"
    )
    fs = _ids(check_ds4(_ctx(tmp_path, {_SEMANTIC: body})), "DS4")
    assert any("does not resolve" in f.message for f in fs)


def test_ds1_missing_decision_type_errors(tmp_path: Path) -> None:
    body = (
        "decisions:\n"
        "  - id: table_grain.x\n"
        "    statement: s\n"
        "    scope: {tables: [x]}\n"
        "    status: pending\n"
        "    evidence: [x.md]\n"
        "    proposed_by: agent\n"
        '    proposed_at: "2026-01-01"\n'
    )
    fs = _ids(check_ds1(_ctx(tmp_path, {_SEMANTIC: body})), "DS1")
    assert any("no decision_type" in f.message for f in fs)


def test_ds1_proposed_without_confidence_errors(tmp_path: Path) -> None:
    body = (
        "decisions:\n"
        "  - id: table_grain.x\n"
        "    decision_type: table_grain\n"
        "    statement: s\n"
        "    scope: {tables: [x]}\n"
        "    status: proposed\n"
        "    evidence: [x.md]\n"
        "    proposed_by: agent\n"
        '    proposed_at: "2026-01-01"\n'
    )
    fs = _ids(check_ds1(_ctx(tmp_path, {_SEMANTIC: body})), "DS1")
    assert any("needs confidence" in f.message for f in fs)


def test_ds1_invalid_confidence_on_nonproposed_errors(tmp_path: Path) -> None:
    body = (
        "decisions:\n"
        "  - id: table_grain.x\n"
        "    decision_type: table_grain\n"
        "    statement: s\n"
        "    scope: {tables: [x]}\n"
        "    status: pending\n"
        "    confidence: sky_high\n"
        "    evidence: [x.md]\n"
        "    proposed_by: agent\n"
        '    proposed_at: "2026-01-01"\n'
    )
    fs = _ids(check_ds1(_ctx(tmp_path, {_SEMANTIC: body})), "DS1")
    assert any("invalid confidence" in f.message for f in fs)


def test_ds3_unhashable_member_does_not_crash(tmp_path: Path) -> None:
    body = (
        "decisions: []\n"
        "batches:\n"
        "  - batch_id: batch.a\n"
        '    presented_at: "2026-01-01"\n'
        "    members: [[nested, list]]\n"
        '    confirmed_by: "A. Owner (data_owner)"\n'
        '    confirmed_at: "2026-01-01"\n'
        "    evidence: [x.md]\n"
    )
    # Must not raise -- a non-string member is flagged, not crashed on.
    fs = _ids(check_ds3(_ctx(tmp_path, {_SEMANTIC: body})), "DS3")
    assert any("not a string id" in f.message for f in fs)


def test_ds4_unhashable_supersedes_does_not_crash(tmp_path: Path) -> None:
    body = (
        "decisions:\n"
        "  - id: table_grain.x\n"
        "    decision_type: table_grain\n"
        "    statement: s\n"
        "    scope: {tables: [x]}\n"
        "    status: proposed\n"
        "    confidence: high\n"
        "    evidence: [x.md]\n"
        "    proposed_by: agent\n"
        '    proposed_at: "2026-01-01"\n'
        "    supersedes: [a, b]\n"
    )
    fs = _ids(check_ds4(_ctx(tmp_path, {_SEMANTIC: body})), "DS4")
    assert any("must be a string id" in f.message for f in fs)


def test_ds3_batch_missing_evidence_errors(tmp_path: Path) -> None:
    body = (
        "decisions:\n"
        "  - id: naming.x\n"
        "    decision_type: naming\n"
        "    statement: s\n"
        "    scope: {columns: [c]}\n"
        "    status: approved\n"
        "    confidence: high\n"
        "    evidence: [x.md]\n"
        "    proposed_by: agent\n"
        '    proposed_at: "2026-01-01"\n'
        "batches:\n"
        "  - batch_id: batch.a\n"
        '    presented_at: "2026-01-01"\n'
        "    members: [naming.x]\n"
        '    confirmed_by: "A. Owner (data_owner)"\n'
        '    confirmed_at: "2026-01-01"\n'
    )
    fs = _ids(check_ds3(_ctx(tmp_path, {_SEMANTIC: body})), "DS3")
    assert any("records no presented evidence" in f.message for f in fs)
