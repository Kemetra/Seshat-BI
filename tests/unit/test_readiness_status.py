from __future__ import annotations

from pathlib import Path

import pytest

from retail.core import RuleContext, Severity
from retail.rules.readiness_status import check_readiness_status_consistency

pytestmark = pytest.mark.unit

STATUS_PATH = "mappings/demo/readiness-status.yaml"


def _status_yaml(
    *,
    current_stage: str = "publish_ready",
    publish_status: str = "pass",
    publish_blockers: str = "[]",
    approvals: str | None = None,
    top_blockers: str = "[]",
) -> str:
    if approvals is None:
        approvals = (
            "  - {stage: mapping_ready, owner: data_owner, at: '2026-01-01'}\n"
            "  - {stage: semantic_model_ready, owner: data_owner, at: '2026-01-01'}\n"
            "  - {stage: dashboard_ready, owner: data_owner, at: '2026-01-01'}\n"
            "  - {stage: publish_ready, owner: data_owner, at: '2026-01-01'}\n"
        )
    return f"""table: "bronze.demo"
source_id: "demo"
source_family: "demo"
current_stage: "{current_stage}"
stages:
  source_ready:
    status: "pass"
    evidence: ["source-profile.md"]
    blocking_reasons: []
  mapping_ready:
    status: "pass"
    evidence: ["source-map.yaml"]
    blocking_reasons: []
  silver_ready:
    status: "pass"
    evidence: ["silver.sql"]
    blocking_reasons: []
  gold_ready:
    status: "pass"
    evidence: ["validate exit 0"]
    blocking_reasons: []
  semantic_model_ready:
    status: "pass"
    evidence: ["contracts approved"]
    blocking_reasons: []
  dashboard_ready:
    status: "pass"
    evidence: ["binding map approved"]
    blocking_reasons: []
  publish_ready:
    status: "{publish_status}"
    evidence: ["handoff pack"]
    blocking_reasons: {publish_blockers}
blocking_reasons: {top_blockers}
approvals:
{approvals}next_action: "done"
last_checked_at: "2026-01-01"
checked_by: "test"
"""


def _ctx(tmp_path: Path, text: str, rel: str = STATUS_PATH) -> RuleContext:
    path = tmp_path / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return RuleContext(repo_root=tmp_path, tracked_files=(rel,))


def _messages(ctx: RuleContext) -> list[str]:
    findings = list(check_readiness_status_consistency(ctx))
    assert all(f.rule_id == "RS1" for f in findings)
    assert all(f.severity is Severity.ERROR for f in findings)
    return [f.message for f in findings]


def test_valid_readiness_status_passes(tmp_path: Path) -> None:
    ctx = _ctx(tmp_path, _status_yaml())
    assert list(check_readiness_status_consistency(ctx)) == []


def test_pass_stage_without_evidence_fails(tmp_path: Path) -> None:
    text = _status_yaml().replace('evidence: ["source-profile.md"]', "evidence: []")
    messages = _messages(_ctx(tmp_path, text))
    assert any("source_ready" in m and "no evidence" in m for m in messages)


def test_blocked_stage_without_blockers_fails(tmp_path: Path) -> None:
    text = _status_yaml(
        current_stage="publish_ready",
        publish_status="blocked",
        publish_blockers="[]",
        top_blockers='["publish approval missing"]',
    )
    messages = _messages(_ctx(tmp_path, text))
    assert any(
        "publish_ready" in m and "blocked" in m and "no blocking" in m for m in messages
    )


def test_non_blocked_stage_with_blockers_fails(tmp_path: Path) -> None:
    text = _status_yaml(
        publish_status="warning",
        publish_blockers='["publish re-approval pending"]',
    )
    messages = _messages(_ctx(tmp_path, text))
    assert any("publish_ready" in m and "blocking_reasons" in m for m in messages)


def test_approval_required_stage_pass_without_approval_fails(tmp_path: Path) -> None:
    approvals = (
        "  - {stage: mapping_ready, owner: data_owner, at: '2026-01-01'}\n"
        "  - {stage: semantic_model_ready, owner: data_owner, at: '2026-01-01'}\n"
        "  - {stage: dashboard_ready, owner: data_owner, at: '2026-01-01'}\n"
    )
    messages = _messages(_ctx(tmp_path, _status_yaml(approvals=approvals)))
    assert any("publish_ready" in m and "approvals" in m for m in messages)


def test_current_stage_cannot_skip_earlier_blocked_stage(tmp_path: Path) -> None:
    old = (
        "  mapping_ready:\n"
        '    status: "pass"\n'
        '    evidence: ["source-map.yaml"]\n'
        "    blocking_reasons: []"
    )
    new = (
        "  mapping_ready:\n"
        '    status: "blocked"\n'
        '    evidence: ["source-map.yaml"]\n'
        '    blocking_reasons: ["grain not approved"]'
    )
    text = _status_yaml().replace(
        old,
        new,
    )
    messages = _messages(_ctx(tmp_path, text))
    assert any("skips past earlier blocked stage" in m for m in messages)


def test_blocked_current_stage_requires_top_level_blocker_mirror(
    tmp_path: Path,
) -> None:
    text = _status_yaml(
        current_stage="publish_ready",
        publish_status="blocked",
        publish_blockers='["publish approval missing"]',
        top_blockers="[]",
    )
    messages = _messages(_ctx(tmp_path, text))
    assert any("top-level blocking_reasons" in m for m in messages)


def test_no_status_files_is_silent_pass(tmp_path: Path) -> None:
    ctx = RuleContext(
        repo_root=tmp_path,
        tracked_files=("mappings/demo/source-map.yaml",),
    )
    assert list(check_readiness_status_consistency(ctx)) == []


# --- H3: file-source encoding-confirmation gate (adversarial review) ---------------


def _file_source_yaml(*, kind: str = "csv", with_source_approval: bool) -> str:
    """A readiness status whose source_ready block declares a file source_kind. The
    stage is pass at every stage; source_ready has an approval only when requested."""
    approvals = (
        "  - {stage: mapping_ready, owner: data_owner, at: '2026-01-01'}\n"
        "  - {stage: semantic_model_ready, owner: data_owner, at: '2026-01-01'}\n"
        "  - {stage: dashboard_ready, owner: data_owner, at: '2026-01-01'}\n"
        "  - {stage: publish_ready, owner: data_owner, at: '2026-01-01'}\n"
    )
    if with_source_approval:
        approvals = (
            "  - {stage: source_ready, owner: data_owner, at: '2026-01-01', "
            "note: 'encoding utf-8 confirmed'}\n"
        ) + approvals
    base = _status_yaml(approvals=approvals)
    # inject source_kind into the source_ready block
    return base.replace(
        '  source_ready:\n    status: "pass"\n    evidence: ["source-profile.md"]',
        f'  source_ready:\n    status: "pass"\n    source_kind: "{kind}"\n'
        f'    evidence: ["source-profile.md"]',
    )


def test_file_source_pass_without_encoding_approval_fails(tmp_path: Path) -> None:
    """A csv/excel source_ready cannot read pass without a source_ready approval
    confirming the [PROPOSED] encoding (adversarial review H3)."""
    messages = _messages(
        _ctx(tmp_path, _file_source_yaml(kind="csv", with_source_approval=False))
    )
    assert any(
        "source_ready" in m and "file source" in m and "encoding" in m for m in messages
    )


def test_file_source_pass_with_encoding_approval_is_clean(tmp_path: Path) -> None:
    """With a recorded source_ready approval, a file source passes cleanly."""
    ctx = _ctx(tmp_path, _file_source_yaml(kind="excel", with_source_approval=True))
    assert list(check_readiness_status_consistency(ctx)) == []


def test_db_source_pass_needs_no_source_approval(tmp_path: Path) -> None:
    """Regression guard: a DB source (no source_kind) still passes source_ready with
    NO source_ready approval -- the H3 gate must not touch existing table sources."""
    # the base fixture's source_ready has no source_kind and no source_ready approval
    ctx = _ctx(tmp_path, _status_yaml())
    messages = [m for m in _messages_or_empty(ctx) if "source_ready" in m]
    assert messages == []


def _messages_or_empty(ctx: RuleContext) -> list[str]:
    return [f.message for f in check_readiness_status_consistency(ctx)]


def test_file_source_kind_case_and_extension_variants_still_gated(
    tmp_path: Path,
) -> None:
    """Adversarial re-review H3 bypass: a natural label like 'CSV', 'Excel', 'xlsx', or
    a trailing space must NOT slip the gate. Each normalizes to a supported file kind
    and, with no source_ready approval, must still fail. (Legacy 'xls' is NOT a
    supported reader format -- it is covered by test_unknown_source_kind_fails_loud.)"""
    for variant in ("CSV", "Csv", "csv ", "Excel", "EXCEL", "xlsx", "xlsm", " TSV "):
        yaml_text = _file_source_yaml(kind=variant, with_source_approval=False)
        messages = _messages(_ctx(tmp_path, yaml_text))
        assert any("source_ready" in m and "file source" in m for m in messages), (
            f"variant {variant!r} bypassed the file-source gate"
        )


def test_unknown_source_kind_fails_loud(tmp_path: Path) -> None:
    """An unrecognized source_kind (typo / unknown / unsupported format) must fail loud,
    not silently fall through to the DB (unaffected) path and skip the encoding gate.
    Legacy 'xls' (BIFF -- openpyxl cannot read it) is unsupported and belongs here."""
    for bogus in ("cvs", "spreadsheet", "parquet", "xls"):
        messages = _messages(
            _ctx(tmp_path, _file_source_yaml(kind=bogus, with_source_approval=False))
        )
        assert any("unrecognized source_kind" in m for m in messages), (
            f"bogus source_kind {bogus!r} did not fail loud"
        )


def test_db_source_kind_explicit_needs_no_source_approval(tmp_path: Path) -> None:
    """An explicit DB source_kind ('db-table') is NOT a file source -> no source_ready
    approval required, and not flagged unrecognized."""
    ctx = _ctx(tmp_path, _file_source_yaml(kind="db-table", with_source_approval=False))
    messages = [m for m in _messages_or_empty(ctx) if "source_ready" in m]
    assert messages == []
