"""Tests for the read-only blocker explainer surface."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from seshat.blocker_explainer import build_blocker_explanations
from seshat.cli import main

pytestmark = pytest.mark.unit


def _write_status(tmp_path: Path, table_dir: str, body: str) -> None:
    path = tmp_path / "mappings" / table_dir / "readiness-status.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")


def test_classifier_extraction_is_behavior_preserving() -> None:
    """Regression lock (spec 115 T004/V9): the classifier moved to
    readiness_classify.py must map each canonical reason to the SAME
    (category, explanation, next_surface) the blocker explainer relied on. If a
    future edit to the shared classifier drifts, this fails BEFORE it can silently
    change blocker_explainer's shipped output."""
    from seshat.readiness_classify import CATEGORY_RANK, classify

    # the five categories, in the fixed rank order, each via a marker word
    assert classify("missing named approval")[0] == "approval"
    assert classify("PK not unique on the data")[0] == "grain"
    assert classify("live validation deferred, no dsn")[0] == "live_validation"
    assert classify("a required artifact is missing")[0] == "artifact"
    assert classify("some other readiness note")[0] == "readiness"
    # 'missing' matches the 'artifact' rule before the default -- order preserved
    assert CATEGORY_RANK == (
        "approval",
        "grain",
        "live_validation",
        "artifact",
        "readiness",
    )
    # blocker_explainer imports THIS classify (not a private copy)
    from seshat import blocker_explainer

    assert blocker_explainer._classify is classify


def test_empty_repo_has_no_blockers(tmp_path: Path) -> None:
    assert build_blocker_explanations(tmp_path) == {
        "items": [],
        "read_only_proof": True,
    }


def test_stage_blocker_is_categorized_and_explained(tmp_path: Path) -> None:
    _write_status(
        tmp_path,
        "orders",
        """\
table: "silver.orders"
current_stage: "mapping_ready"
stages:
  source_ready: {status: "pass", evidence: ["profile"]}
  mapping_ready:
    status: "blocked"
    blocking_reasons: ["grain not confirmed unique on data"]
  silver_ready: {status: "not_started"}
  gold_ready: {status: "not_started"}
  semantic_model_ready: {status: "not_started"}
  dashboard_ready: {status: "not_started"}
  publish_ready: {status: "not_started"}
blocking_reasons: ["grain not confirmed unique on data"]
approvals: []
""",
    )

    result = build_blocker_explanations(tmp_path)

    assert result["items"] == [
        {
            "table": "silver.orders",
            "source_path": "mappings/orders/readiness-status.yaml",
            "stage": "mapping_ready",
            "category": "grain",
            "reason": "grain not confirmed unique on data",
            "explanation": (
                "The mapping gate is blocked on grain or key certainty; resolve "
                "the named grain/PK question before silver work."
            ),
            "next_surface": "approval request or source-mapping review",
            # Remediation metadata (B1'): grain certainty is a Principle-V
            # judgment call, so it can only be cleared by a named human.
            "remediation": "human_only",
            "doc": "docs/readiness/mapping-ready.md",
            "stop_condition": (
                "stop at the grain/PK question; propose options with evidence "
                "and let the owner rule"
            ),
        }
    ]


def test_validation_blocker_routes_to_live_validation(tmp_path: Path) -> None:
    _write_status(
        tmp_path,
        "orders",
        """\
table: "silver.orders"
stages:
  source_ready: {status: "pass", evidence: ["profile"]}
  mapping_ready: {status: "pass", evidence: ["map"]}
  silver_ready: {status: "pass", evidence: ["silver"]}
  gold_ready:
    status: "blocked"
    blocking_reasons: ["Deferred boundary: no DSN configured"]
approvals:
  - {stage: mapping_ready, owner: "Ada Lovelace (analyst)", at: "2026-07-01"}
""",
    )

    item = build_blocker_explanations(tmp_path)["items"][0]
    assert item["category"] == "live_validation"
    assert item["next_surface"] == "retail validate setup"


def test_invalid_pass_approval_is_explained_as_approval_blocker(tmp_path: Path) -> None:
    _write_status(
        tmp_path,
        "orders",
        """\
table: "silver.orders"
stages:
  source_ready: {status: "pass", evidence: ["profile"]}
  mapping_ready: {status: "pass", evidence: ["map"]}
  silver_ready: {status: "not_started"}
approvals:
  - {stage: mapping_ready, owner: "analyst", at: "2026-07-01"}
""",
    )

    item = build_blocker_explanations(tmp_path)["items"][0]
    assert item["stage"] == "mapping_ready"
    assert item["category"] == "approval"
    assert item["reason"] == "invalid or missing approval for pass stage"


def test_file_source_source_ready_missing_approval_is_explained(
    tmp_path: Path,
) -> None:
    _write_status(
        tmp_path,
        "orders_file",
        """\
table: "bronze.orders_file"
stages:
  source_ready:
    status: "pass"
    source_kind: "csv"
    evidence: ["profile"]
  mapping_ready: {status: "not_started"}
approvals: []
""",
    )

    item = build_blocker_explanations(tmp_path)["items"][0]
    assert item["stage"] == "source_ready"
    assert item["category"] == "approval"
    assert item["reason"] == "invalid or missing approval for pass stage"


def test_cli_blockers_json_is_read_only_and_score_free(tmp_path: Path, capsys) -> None:
    _write_status(
        tmp_path,
        "orders",
        """\
table: "silver.orders"
stages:
  source_ready: {status: "pass", evidence: ["profile"]}
  mapping_ready:
    status: "blocked"
    blocking_reasons: ["Map is filled but not yet reviewed/APPROVED"]
approvals: []
""",
    )
    before = sorted(p.relative_to(tmp_path) for p in tmp_path.rglob("*") if p.is_file())

    exit_code = main(["blockers", "--repo", str(tmp_path), "--format", "json"])

    assert exit_code == 0
    parsed = json.loads(capsys.readouterr().out)
    assert parsed["items"][0]["category"] == "approval"
    dumped = json.dumps(parsed).lower()
    for banned in ("score", "confidence", "health", "maturity"):
        assert banned not in dumped
    after = sorted(p.relative_to(tmp_path) for p in tmp_path.rglob("*") if p.is_file())
    assert before == after


# ---------------------------------------------------------------------------
# Remediation metadata on each blocker item (B1'). `blockers` already said WHAT
# is blocked and WHICH surface is next; these pin the answer to "is this mine to
# fix, or does it need a named human?" -- sourced from the committed allowlist in
# readiness_classify, never generated per blocker.
# ---------------------------------------------------------------------------


def test_blocker_item_carries_remediation_metadata(tmp_path: Path) -> None:
    """Each blocker names its remediation class, a doc route, and a stop condition."""
    _write_status(
        tmp_path,
        "orders",
        """\
table: "bronze.orders"
current_stage: "mapping_ready"
stages:
  mapping_ready:
    status: "blocked"
    blocking_reasons: ["named-human approval missing for mapping_ready"]
""",
    )

    doc = build_blocker_explanations(tmp_path)
    item = doc["items"][0]

    assert item["category"] == "approval"
    assert item["remediation"] == "human_only"
    assert item["doc"] == "docs/readiness/readiness-model.md"
    assert item["stop_condition"]


def test_blocker_item_keeps_its_pre_existing_keys(tmp_path: Path) -> None:
    """Backward compatibility: the additive change keeps the original keys."""
    _write_status(
        tmp_path,
        "orders",
        """\
table: "bronze.orders"
current_stage: "source_ready"
stages:
  source_ready:
    status: "blocked"
    blocking_reasons: ["mappings/orders/source-profile.md does not exist"]
""",
    )

    item = build_blocker_explanations(tmp_path)["items"][0]

    for key in (
        "table",
        "source_path",
        "stage",
        "category",
        "reason",
        "explanation",
        "next_surface",
    ):
        assert key in item, key


def test_mechanical_and_human_only_are_distinguished(tmp_path: Path) -> None:
    """An artifact gap is mechanical; a missing approval is not -- same report."""
    _write_status(
        tmp_path,
        "orders",
        """\
table: "bronze.orders"
current_stage: "source_ready"
stages:
  source_ready:
    status: "blocked"
    blocking_reasons: ["mappings/orders/source-profile.md does not exist"]
  mapping_ready:
    status: "blocked"
    blocking_reasons: ["named-human approval missing for mapping_ready"]
""",
    )

    by_category = {
        item["category"]: item["remediation"]
        for item in build_blocker_explanations(tmp_path)["items"]
    }

    assert by_category["artifact"] == "mechanical"
    assert by_category["approval"] == "human_only"


def test_text_render_names_who_acts(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The human-facing render must show the remediation class, not only JSON.

    A reader scanning `seshat blockers` needs to see at a glance which blockers
    are theirs to rule on; metadata visible only in --format json would not
    reach them.
    """
    _write_status(
        tmp_path,
        "orders",
        """\
table: "bronze.orders"
current_stage: "mapping_ready"
stages:
  mapping_ready:
    status: "blocked"
    blocking_reasons: ["named-human approval missing for mapping_ready"]
""",
    )

    rc = main(["blockers", "--repo", str(tmp_path)])

    out = capsys.readouterr().out
    assert rc == 0
    assert "human_only" in out
    assert "docs/readiness/readiness-model.md" in out
    assert "stop" in out.lower()
