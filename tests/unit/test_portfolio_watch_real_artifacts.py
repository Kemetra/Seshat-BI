"""Portfolio Watch reads what the real producers emit, and never reads an
unproven artifact as current."""

from __future__ import annotations

from pathlib import Path

import pytest

from seshat import portfolio_watch as pw
from seshat.drift import (
    DriftSemantics,
    ReportContext,
    to_findings_dict,
    to_portfolio_artifact,
)
from tests.fixtures.portfolio_watch.builders import (
    drift_artifact,
    generic_artifact,
    init_git_repo,
    write_json_artifact,
    write_readiness_status,
    write_source_profile,
)
from tests.unit.test_drift import _col, _profile

pytestmark = pytest.mark.unit


def _real_pii_drift_doc() -> dict:
    """Output of the real producer: a dropped-PII column reappeared."""
    base = _profile([_col("amount")])
    observed = _profile([_col("amount"), _col("email")])
    return to_findings_dict(
        base,
        observed,
        ReportContext(baseline_ref="source-profile.md", evidence=["re-profile"]),
        DriftSemantics(dropped_pii_columns=frozenset({"email"})),
    )


def _source_drift(summary: dict) -> dict:
    scope = summary["scopes"][0]
    return next(d for d in scope["dimensions"] if d["dimension"] == "source_drift")


def test_real_drift_output_with_pii_surface_drift_raises_attention(
    tmp_path: Path,
) -> None:
    write_readiness_status(tmp_path, "sales", current_stage="source_ready")
    write_source_profile(tmp_path, "sales")
    write_json_artifact(tmp_path, "sales", "drift-findings.json", _real_pii_drift_doc())

    summary = pw.build_portfolio_watch_summary(tmp_path)

    dimension = _source_drift(summary)
    assert dimension["state"] != pw.STATE_UNREADABLE
    assert any(item["class"] == "pii_surface_drift" for item in dimension["items"])
    scope = summary["scopes"][0]
    assert scope["requires_human_attention"] is True
    assert scope["owner"] == "governance"


def test_stamped_real_drift_output_is_covered_at_head(tmp_path: Path) -> None:
    write_readiness_status(tmp_path, "sales", current_stage="source_ready")
    write_source_profile(tmp_path, "sales")
    head = init_git_repo(tmp_path)
    artifact = to_portfolio_artifact(_real_pii_drift_doc(), captured_at_revision=head)
    write_json_artifact(tmp_path, "sales", "drift-findings.json", artifact)

    dimension = _source_drift(pw.build_portfolio_watch_summary(tmp_path))

    assert dimension["state"] == pw.STATE_COVERED
    assert dimension["class"] == "blocked"


def test_artifact_without_captured_at_revision_is_stale(tmp_path: Path) -> None:
    write_readiness_status(tmp_path, "sales", current_stage="source_ready")
    write_source_profile(tmp_path, "sales")
    init_git_repo(tmp_path)
    write_json_artifact(
        tmp_path, "sales", "drift-findings.json", drift_artifact(class_="no_drift")
    )

    dimension = _source_drift(pw.build_portfolio_watch_summary(tmp_path))

    assert dimension["state"] == pw.STATE_STALE
    assert "captured_at_revision" in dimension["measured"]


def test_artifact_without_a_provable_head_is_stale(tmp_path: Path) -> None:
    write_readiness_status(tmp_path, "sales", current_stage="source_ready")
    write_source_profile(tmp_path, "sales")
    write_json_artifact(
        tmp_path,
        "sales",
        "drift-findings.json",
        drift_artifact(class_="no_drift", captured_at_revision="abc123"),
    )
    if pw._source_revision(tmp_path) is not None:
        pytest.skip("the temp directory sits inside a git repository")

    dimension = _source_drift(pw.build_portfolio_watch_summary(tmp_path))

    assert dimension["state"] == pw.STATE_STALE


def test_summary_builds_the_readiness_projection_once(
    tmp_path: Path, monkeypatch
) -> None:
    calls: list[Path] = []
    real = pw.build_readiness_projection

    def counting(root):
        calls.append(root)
        return real(root)

    monkeypatch.setattr(pw, "build_readiness_projection", counting)
    write_readiness_status(tmp_path, "sales", current_stage="source_ready")

    pw.build_portfolio_watch_summary(tmp_path)

    assert len(calls) == 1


def test_explorer_footer_does_not_claim_committed_only_evidence() -> None:
    from seshat.explorer import build

    source = Path(build.__file__).read_text(encoding="utf-8")
    assert "Generated from committed evidence only" not in source


def test_malformed_item_degrades_to_unreadable(tmp_path: Path) -> None:
    """A corrupted item must not vanish and later read as 'resolved'."""
    write_readiness_status(tmp_path, "sales", current_stage="source_ready")
    head = init_git_repo(tmp_path)
    write_json_artifact(
        tmp_path,
        "sales",
        "metric-drift-findings.json",
        generic_artifact(
            class_="drift",
            captured_at_revision=head,
            items=[{"class": 7, "subject_locator": "NetSales"}],
        ),
    )

    scope = pw.build_portfolio_watch_summary(tmp_path)["scopes"][0]
    dimension = next(
        d for d in scope["dimensions"] if d["dimension"] == "contract_metric_drift"
    )

    assert dimension["state"] == pw.STATE_UNREADABLE
    assert "1 malformed item" in dimension["measured"]
