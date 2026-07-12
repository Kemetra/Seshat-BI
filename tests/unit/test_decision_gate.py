"""Decision gate verdict tests (spec 121, T022).

Covers the SC-003 seeded scenarios (pending grain/PII/KPI-meaning/policy,
unapproved blueprint, missing evidence, conflicting/malformed store) and the
clarify-Q1 staleness split (critical => blocked, non-critical => warn). Uses the
real flow contract via the repo root and real on-disk evidence so
artifact_identity computes true sha256s.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from seshat.decision_gate import verdict_for

pytestmark = pytest.mark.unit

_REPO_ROOT = Path(__file__).resolve().parents[2]
_FLOW_REL = "contracts/knowledge/database-to-pbip-flow.yaml"
_AUTHORITY_REL = "contracts/knowledge/approval-authority.yaml"
_SEMANTIC = ".seshat/semantic-decisions.yaml"
_KPI = ".seshat/kpi-contracts.yaml"


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _repo(tmp_path: Path, files: dict[str, str]) -> tuple[Path, tuple[str, ...]]:
    """Materialize a workspace carrying the real flow + authority contracts."""
    all_files = dict(files)
    all_files[_FLOW_REL] = (_REPO_ROOT / _FLOW_REL).read_text(encoding="utf-8")
    all_files[_AUTHORITY_REL] = (_REPO_ROOT / _AUTHORITY_REL).read_text(
        encoding="utf-8"
    )
    tracked = []
    for rel, body in all_files.items():
        p = tmp_path / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(body, encoding="utf-8")
        tracked.append(rel)
    return tmp_path, tuple(tracked)


def _grain(status: str, did: str = "table_grain.fct_sales") -> str:
    return (
        "decisions:\n"
        f"  - id: {did}\n"
        "    decision_type: table_grain\n"
        "    statement: s\n"
        "    scope: {tables: [fct_sales]}\n"
        f"    status: {status}\n"
        + ("    confidence: high\n" if status == "proposed" else "")
        + "    evidence: [ev.md]\n"
        "    proposed_by: agent\n"
        '    proposed_at: "2026-01-01"\n'
    )


# ---- blocked scenarios (SC-003) -------------------------------------------


def test_pending_grain_blocks_silver_gold_modeling(tmp_path: Path) -> None:
    root, tracked = _repo(tmp_path, {_SEMANTIC: _grain("pending")})
    v = verdict_for(root, tracked, "silver_gold_model_planning")
    assert v.verdict == "blocked"
    assert any("table_grain.fct_sales" in b.decision_id for b in v.blocking)


def test_pending_pii_blocks_interview_downstream(tmp_path: Path) -> None:
    body = (
        "decisions:\n"
        "  - id: pii_handling.cust_email\n"
        "    decision_type: pii_handling\n"
        "    statement: s\n"
        "    scope: {columns: [dim_customer.email]}\n"
        "    status: needs_user_input\n"
        "    evidence: [ev.md]\n"
        "    proposed_by: agent\n"
        '    proposed_at: "2026-01-01"\n'
    )
    root, tracked = _repo(tmp_path, {_SEMANTIC: body})
    # FR-032/AC-006: pending pii_handling blocks cleaning (silver_gold), report
    # exposure (report_intent, dashboard_blueprint), AND pbip readiness.
    for stage in (
        "silver_gold_model_planning",
        "report_intent",
        "dashboard_blueprint",
        "pbip_prototype_readiness",
    ):
        v = verdict_for(root, tracked, stage)
        assert v.verdict == "blocked", stage
        assert any("pii_handling" in b.decision_id for b in v.blocking), stage


def test_pending_kpi_meaning_blocks_kpi_contracts(tmp_path: Path) -> None:
    body = (
        "decisions:\n"
        "  - id: kpi_definition.net_sales\n"
        "    decision_type: kpi_definition\n"
        "    statement: s\n"
        "    scope: {kpis: [net_sales]}\n"
        "    status: proposed\n"
        "    confidence: high\n"
        "    evidence: [ev.md]\n"
        "    proposed_by: agent\n"
        '    proposed_at: "2026-01-01"\n'
    )
    root, tracked = _repo(tmp_path, {_KPI: body})
    for stage in ("kpi_contracts", "semantic_model_dax", "pbip_prototype_readiness"):
        v = verdict_for(root, tracked, stage)
        assert v.verdict == "blocked", stage


def test_unapproved_blueprint_blocks_pbip(tmp_path: Path) -> None:
    body = (
        "decisions:\n"
        "  - id: dashboard_blueprint_approval.main\n"
        "    decision_type: dashboard_blueprint_approval\n"
        "    statement: s\n"
        "    scope: {artifacts: [dashboard.main]}\n"
        "    status: pending\n"
        "    evidence: [ev.md]\n"
        "    proposed_by: agent\n"
        '    proposed_at: "2026-01-01"\n'
    )
    root, tracked = _repo(tmp_path, {_SEMANTIC: body})
    v = verdict_for(root, tracked, "pbip_prototype_readiness")
    assert v.verdict == "blocked"


def test_malformed_store_fails_closed(tmp_path: Path) -> None:
    root, tracked = _repo(tmp_path, {_SEMANTIC: "decisions: [\n unterminated"})
    v = verdict_for(root, tracked, "silver_gold_model_planning")
    assert v.verdict == "blocked"
    assert v.blocking


def test_unknown_stage_fails_closed(tmp_path: Path) -> None:
    root, tracked = _repo(tmp_path, {_SEMANTIC: _grain("approved")})
    v = verdict_for(root, tracked, "no_such_stage")
    assert v.verdict == "blocked"


# ---- pass scenario --------------------------------------------------------


def _approved_grain_with_evidence(tmp_path: Path) -> tuple[Path, tuple[str, ...]]:
    ev = tmp_path / "ev.md"
    ev.parent.mkdir(parents=True, exist_ok=True)
    ev.write_text("profile evidence\n", encoding="utf-8")
    sha = _sha(ev)
    body = (
        "decisions:\n"
        "  - id: table_grain.fct_sales\n"
        "    decision_type: table_grain\n"
        "    statement: s\n"
        "    scope: {tables: [fct_sales]}\n"
        "    status: approved\n"
        "    evidence: [ev.md]\n"
        "    proposed_by: agent\n"
        '    proposed_at: "2026-01-01"\n'
        "    approval:\n"
        '      approved_by: "A. Owner (data_owner)"\n'
        '      approved_at: "2026-01-02"\n'
        "      source: interview\n"
        "      evidence: [ev.md]\n"
        f"      evidence_identity: {{ev.md: {sha}}}\n"
        "      reviewed_scope: {tables: [fct_sales]}\n"
    )
    return _repo(tmp_path, {_SEMANTIC: body})


def test_approved_fresh_grain_passes(tmp_path: Path) -> None:
    root, tracked = _approved_grain_with_evidence(tmp_path)
    v = verdict_for(root, tracked, "silver_gold_model_planning")
    assert v.verdict == "pass", v
    assert "ev.md" in v.evidence


def test_pass_requires_evidence(tmp_path: Path) -> None:
    # approved but evidence list empty -> blocked, never pass (DS5 store guard +
    # gate guard).
    body = (
        "decisions:\n"
        "  - id: table_grain.fct_sales\n"
        "    decision_type: table_grain\n"
        "    statement: s\n"
        "    scope: {tables: [fct_sales]}\n"
        "    status: approved\n"
        "    evidence: [ev.md]\n"
        "    proposed_by: agent\n"
        '    proposed_at: "2026-01-01"\n'
        "    approval:\n"
        '      approved_by: "A. Owner (data_owner)"\n'
        '      approved_at: "2026-01-02"\n'
        "      source: interview\n"
        "      evidence: []\n"
        "      evidence_identity: {}\n"
        "      reviewed_scope: {tables: [fct_sales]}\n"
    )
    root, tracked = _repo(tmp_path, {_SEMANTIC: body})
    v = verdict_for(root, tracked, "silver_gold_model_planning")
    assert v.verdict == "blocked"


# ---- staleness split (clarify Q1) -----------------------------------------


def test_stale_evidence_on_critical_blocks(tmp_path: Path) -> None:
    root, tracked = _approved_grain_with_evidence(tmp_path)
    # Mutate the evidence file so its sha no longer matches the recorded identity.
    (tmp_path / "ev.md").write_text("CHANGED after approval\n", encoding="utf-8")
    v = verdict_for(root, tracked, "silver_gold_model_planning")
    assert v.verdict == "blocked"
    assert any("stale" in b.reason for b in v.blocking)


def test_stale_evidence_on_noncritical_warns(tmp_path: Path) -> None:
    ev = tmp_path / "ev.md"
    ev.parent.mkdir(parents=True, exist_ok=True)
    ev.write_text("v1\n", encoding="utf-8")
    sha = _sha(ev)
    # 'naming' is a non-critical type; put it in a stage whose blocking set we
    # widen by using a non-critical decision that still lands in-scope: use the
    # gate directly against a synthetic category set via a real stage that lists
    # a non-critical -- since no flow stage blocks on 'naming', assert via the
    # classifier path: a non-critical approved+stale decision must WARN, not block.
    body = (
        "decisions:\n"
        "  - id: missing_value_rule.amt\n"  # critical, to prove the split explicitly
        "    decision_type: missing_value_rule\n"
        "    statement: s\n"
        "    scope: {columns: [fct.amt]}\n"
        "    status: approved\n"
        "    evidence: [ev.md]\n"
        "    proposed_by: agent\n"
        '    proposed_at: "2026-01-01"\n'
        "    approval:\n"
        '      approved_by: "A. Owner (metric_owner)"\n'
        '      approved_at: "2026-01-02"\n'
        "      source: interview\n"
        "      evidence: [ev.md]\n"
        f"      evidence_identity: {{ev.md: {sha}}}\n"
        "      reviewed_scope: {columns: [fct.amt]}\n"
    )
    root, tracked = _repo(tmp_path, {_KPI: body})
    ev.write_text("v2 CHANGED\n", encoding="utf-8")
    # missing_value_rule IS critical -> stale blocks (this asserts the critical arm).
    v = verdict_for(root, tracked, "kpi_contracts")
    assert v.verdict == "blocked"


def test_classifier_noncritical_stale_warns_directly(tmp_path: Path) -> None:
    # Direct classifier check of the non-critical stale arm: a fully-valid approval
    # on a NON-critical type whose evidence changed after approval must WARN, not
    # block (clarify Q1). authority=None is fine because a non-critical type skips
    # the eligibility check inside approval_is_valid.
    from seshat.decision_gate import _classify_decision

    ev = tmp_path / "ev.md"
    ev.write_text("v1\n", encoding="utf-8")
    sha = hashlib.sha256((tmp_path / "ev.md").read_bytes()).hexdigest()
    decision = {
        "id": "naming.col",
        "decision_type": "naming",  # non-critical
        "status": "approved",
        "approval": {
            "approved_by": "A. Owner (analyst)",
            "approved_at": "2026-01-02",
            "source": "interview",
            "evidence": ["ev.md"],
            "evidence_identity": {"ev.md": sha},
            "reviewed_scope": {"columns": ["c"]},
        },
    }
    (tmp_path / "ev.md").write_text("v2\n", encoding="utf-8")
    state, note = _classify_decision(tmp_path, decision, None)
    assert state == "warn"
    assert "stale" in note


# ---- absent store ---------------------------------------------------------


def test_absent_store_passes_when_stage_has_no_blockers(tmp_path: Path) -> None:
    # discovery has no blocking categories; an absent store means nothing blocks.
    root, tracked = _repo(tmp_path, {})
    v = verdict_for(root, tracked, "discovery")
    assert v.verdict == "pass"


# ---- adversarial-review regressions: fail-closed on absence/emptiness --------


def test_absent_store_blocks_a_gated_stage(tmp_path: Path) -> None:
    # No .seshat store at a stage WITH blocking categories must be blocked, never
    # a false pass from absence (critical review finding).
    root, tracked = _repo(tmp_path, {})
    for stage in (
        "silver_gold_model_planning",
        "kpi_contracts",
        "pbip_prototype_readiness",
    ):
        v = verdict_for(root, tracked, stage)
        assert v.verdict == "blocked", stage
        assert v.blocking


def test_empty_store_blocks_a_gated_stage(tmp_path: Path) -> None:
    root, tracked = _repo(tmp_path, {_SEMANTIC: "decisions: []\n"})
    v = verdict_for(root, tracked, "pbip_prototype_readiness")
    assert v.verdict == "blocked"


def test_all_superseded_does_not_falsely_pass(tmp_path: Path) -> None:
    # A single superseded record with no live replacement must not vacuously pass a
    # gated stage (empty-evidence pass finding).
    body = _grain("superseded") + "    superseded_by: table_grain.fct_sales.2\n"
    body += (
        "  - id: table_grain.fct_sales.2\n"
        "    decision_type: table_grain\n"
        "    statement: s\n"
        "    scope: {tables: [fct_sales]}\n"
        "    status: pending\n"
        "    evidence: [ev.md]\n"
        "    proposed_by: agent\n"
        '    proposed_at: "2026-01-01"\n'
    )
    root, tracked = _repo(tmp_path, {_SEMANTIC: body})
    v = verdict_for(root, tracked, "silver_gold_model_planning")
    assert v.verdict == "blocked"


def test_ineligible_approval_blocks_at_gate(tmp_path: Path) -> None:
    # An approved kpi_definition by report_owner (ineligible) must block the gate,
    # not just the DS2 lint (gate-vs-DS divergence finding).
    ev = tmp_path / "ev.md"
    ev.parent.mkdir(parents=True, exist_ok=True)
    ev.write_text("e\n", encoding="utf-8")
    sha = _sha(ev)
    body = (
        "decisions:\n"
        "  - id: kpi_definition.net\n"
        "    decision_type: kpi_definition\n"
        "    statement: s\n"
        "    scope: {kpis: [net]}\n"
        "    status: approved\n"
        "    evidence: [ev.md]\n"
        "    proposed_by: agent\n"
        '    proposed_at: "2026-01-01"\n'
        "    approval:\n"
        '      approved_by: "R. Report (report_owner)"\n'
        '      approved_at: "2026-01-02"\n'
        "      source: interview\n"
        "      evidence: [ev.md]\n"
        f"      evidence_identity: {{ev.md: {sha}}}\n"
        "      reviewed_scope: {kpis: [net]}\n"
    )
    root, tracked = _repo(tmp_path, {_KPI: body})
    v = verdict_for(root, tracked, "kpi_contracts")
    assert v.verdict == "blocked"
    assert any("ineligible" in b.reason for b in v.blocking)


def test_conflicting_active_decisions_block_at_gate(tmp_path: Path) -> None:
    rec = (
        "  - id: {did}\n"
        "    decision_type: table_grain\n"
        "    statement: s\n"
        "    scope: {{tables: [fct_sales]}}\n"
        "    status: pending\n"
        "    evidence: [ev.md]\n"
        "    proposed_by: agent\n"
        '    proposed_at: "2026-01-01"\n'
    )
    body = (
        "decisions:\n"
        + rec.format(did="table_grain.a")
        + rec.format(did="table_grain.b")
    )
    root, tracked = _repo(tmp_path, {_SEMANTIC: body})
    v = verdict_for(root, tracked, "silver_gold_model_planning")
    assert v.verdict == "blocked"
    assert any("conflicting" in b.reason for b in v.blocking)


def test_unknown_status_fails_closed_at_gate(tmp_path: Path) -> None:
    root, tracked = _repo(tmp_path, {_SEMANTIC: _grain("aproved")})  # typo
    v = verdict_for(root, tracked, "silver_gold_model_planning")
    assert v.verdict == "blocked"
    assert any("unrecognized status" in b.reason for b in v.blocking)


def test_unhashable_decision_type_does_not_crash(tmp_path: Path) -> None:
    body = (
        "decisions:\n"
        "  - id: table_grain.x\n"
        "    decision_type: [table_grain]\n"  # list, unhashable
        "    statement: s\n"
        "    scope: {tables: [x]}\n"
        "    status: pending\n"
        "    evidence: [ev.md]\n"
        "    proposed_by: agent\n"
        '    proposed_at: "2026-01-01"\n'
    )
    root, tracked = _repo(tmp_path, {_SEMANTIC: body})
    # Must not raise; the malformed record simply does not match any category.
    v = verdict_for(root, tracked, "silver_gold_model_planning")
    assert v.verdict == "blocked"  # blocked via evidence-presence (no valid decision)


# ---- spine projection (R-6) -----------------------------------------------


def test_spine_projection_maps_status_and_stage(tmp_path: Path) -> None:
    from seshat.decision_gate import project_to_spine

    root, tracked = _repo(tmp_path, {_SEMANTIC: _grain("pending")})
    v = verdict_for(root, tracked, "silver_gold_model_planning")
    proj = project_to_spine(v)
    assert proj["spine_stage"] == "silver_ready"
    assert proj["status"] == "blocked"  # warn->warning, blocked->blocked, pass->pass
    assert proj["blocking_reasons"]


def test_spine_projection_warn_maps_to_warning(tmp_path: Path) -> None:
    from seshat.decision_gate import Verdict, project_to_spine

    v = Verdict(stage="dashboard_blueprint", verdict="warn", warnings=("x",))
    proj = project_to_spine(v)
    assert proj["spine_stage"] == "dashboard_ready"
    assert proj["status"] == "warning"
