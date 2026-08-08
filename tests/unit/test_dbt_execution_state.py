"""Tests for the dbt execution-evidence consumer (spec 150, Phase 7).

The dbt adapter already parses dbt's own ``manifest.json``/``run_results.json``,
normalizes them into ``RunEvidence``, and commits a schema-validated record to
``mappings/<table>/dbt-evidence/``. Nothing read that record back.

These tests pin the reader's contract. The load-bearing ones are the negative
guarantees: execution evidence must never grant readiness (US2), and -- the
defect adversarial review round 2 caught -- must never SOFTEN an existing stop
(FR-019/FR-020).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from seshat.agent_next import build_agent_next_document
from seshat.dbt_execution_state import (
    STATE_ABSENT,
    STATE_BLOCKED,
    STATE_BUILT,
    STATE_FAILED,
    STATE_UNREADABLE,
    dbt_execution_state,
)

pytestmark = pytest.mark.unit


def _write_status(tmp_path: Path, table_dir: str, body: str) -> Path:
    path = tmp_path / "mappings" / table_dir / "readiness-status.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")
    return path


def _record(outcome: str, **overrides: object) -> dict:
    """A record carrying every envelope field the reader names."""
    record = {
        "schema_version": 1,
        "authority": "derived-evidence-only",
        "invocation_id": "20260808T141530Z-9f3a2b71",
        "table_id": "silver.orders",
        "command": "build",
        "outcome": outcome,
        "blocking_reasons": [],
        "readiness_effect": "none; named-human approval required",
    }
    record.update(overrides)
    return record


def _write_evidence(tmp_path: Path, table_dir: str, record: dict) -> Path:
    path = (
        tmp_path
        / "mappings"
        / table_dir
        / "dbt-evidence"
        / f"{record['invocation_id']}.json"
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(record), encoding="utf-8")
    return path


_BLOCKED_TABLE = """\
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
approvals: []
next_action: "resolve grain"
"""


# --------------------------------------------------------------------------
# T003 -- fail closed
# --------------------------------------------------------------------------


def test_absent_directory_is_absent_not_success(tmp_path: Path) -> None:
    _write_status(tmp_path, "orders", _BLOCKED_TABLE)
    assert dbt_execution_state(tmp_path, "orders") == STATE_ABSENT


def test_empty_evidence_directory_is_absent(tmp_path: Path) -> None:
    _write_status(tmp_path, "orders", _BLOCKED_TABLE)
    (tmp_path / "mappings" / "orders" / "dbt-evidence").mkdir(parents=True)
    assert dbt_execution_state(tmp_path, "orders") == STATE_ABSENT


def test_corrupt_json_is_unreadable_never_success(tmp_path: Path) -> None:
    _write_status(tmp_path, "orders", _BLOCKED_TABLE)
    path = (
        tmp_path
        / "mappings"
        / "orders"
        / "dbt-evidence"
        / "20260808T141530Z-9f3a2b71.json"
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("{not valid json", encoding="utf-8")

    state = dbt_execution_state(tmp_path, "orders")
    assert state == STATE_UNREADABLE
    assert state != STATE_BUILT


def test_missing_envelope_fields_is_unreadable(tmp_path: Path) -> None:
    _write_status(tmp_path, "orders", _BLOCKED_TABLE)
    _write_evidence(
        tmp_path,
        "orders",
        {"invocation_id": "20260808T141530Z-9f3a2b71", "schema_version": 1},
    )
    assert dbt_execution_state(tmp_path, "orders") == STATE_UNREADABLE


# --------------------------------------------------------------------------
# T004 -- outcome translation
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("outcome", "expected"),
    (
        ("pass", STATE_BUILT),
        ("failed", STATE_FAILED),
        ("blocked", STATE_BLOCKED),
        ("unavailable", STATE_BLOCKED),
        ("something-new-upstream", STATE_BLOCKED),
    ),
)
def test_outcome_translates_to_execution_state(
    tmp_path: Path, outcome: str, expected: str
) -> None:
    """Unknown upstream status fails closed to blocked, never to built."""
    _write_status(tmp_path, "orders", _BLOCKED_TABLE)
    _write_evidence(tmp_path, "orders", _record(outcome))
    assert dbt_execution_state(tmp_path, "orders") == expected


def test_state_is_never_a_readiness_token(tmp_path: Path) -> None:
    """FR-006: the classifier must not emit the readiness four-status vocabulary.

    ``blocked`` is shared between the two vocabularies by design; ``pass``,
    ``warning`` and ``not_started`` must never appear.
    """
    _write_status(tmp_path, "orders", _BLOCKED_TABLE)
    for outcome in ("pass", "failed", "blocked", "unavailable"):
        _write_evidence(tmp_path, "orders", _record(outcome))
        assert dbt_execution_state(tmp_path, "orders") not in {
            "pass",
            "warning",
            "not_started",
        }


# --------------------------------------------------------------------------
# T007/FR-009 -- deterministic selection
# --------------------------------------------------------------------------


def test_latest_record_wins_by_filename_sort(tmp_path: Path) -> None:
    _write_status(tmp_path, "orders", _BLOCKED_TABLE)
    _write_evidence(
        tmp_path, "orders", _record("pass", invocation_id="20260101T090000Z-aaaaaaaa")
    )
    _write_evidence(
        tmp_path, "orders", _record("failed", invocation_id="20260808T141530Z-bbbbbbbb")
    )
    assert dbt_execution_state(tmp_path, "orders") == STATE_FAILED


def test_corrupt_latest_does_not_fall_back_to_a_flattering_older_record(
    tmp_path: Path,
) -> None:
    """A corrupt newest record must not silently yield the older passing one."""
    _write_status(tmp_path, "orders", _BLOCKED_TABLE)
    _write_evidence(
        tmp_path, "orders", _record("pass", invocation_id="20260101T090000Z-aaaaaaaa")
    )
    corrupt = (
        tmp_path
        / "mappings"
        / "orders"
        / "dbt-evidence"
        / "20260808T141530Z-bbbbbbbb.json"
    )
    corrupt.write_text("{truncated", encoding="utf-8")

    assert dbt_execution_state(tmp_path, "orders") == STATE_UNREADABLE


# --------------------------------------------------------------------------
# T002 -- US2: execution success never becomes readiness
# --------------------------------------------------------------------------


def test_passing_dbt_record_leaves_blocked_stage_blocked(tmp_path: Path) -> None:
    _write_status(tmp_path, "orders", _BLOCKED_TABLE)
    _write_evidence(tmp_path, "orders", _record("pass"))

    document = build_agent_next_document(tmp_path)

    assert document["readiness_state"] == "blocked"
    assert document["blocking_reasons"] == ["grain not confirmed unique on data"]


def test_passing_dbt_record_changes_nothing_at_all(tmp_path: Path) -> None:
    """A clean build is evidence, not a governance event: no caveat, no change."""
    baseline_root = tmp_path / "baseline"
    with_record = tmp_path / "with_record"
    for root in (baseline_root, with_record):
        _write_status(root, "orders", _BLOCKED_TABLE)
    _write_evidence(with_record, "orders", _record("pass"))

    baseline = build_agent_next_document(baseline_root)
    actual = build_agent_next_document(with_record)

    assert actual == baseline


# --------------------------------------------------------------------------
# T005a -- FR-019/FR-020: the caveat must never SOFTEN an existing stop
# --------------------------------------------------------------------------

# Mapping Ready is recorded `pass` but carries no named approval, so the
# decision surface returns `approval_required` -- a DIFFERENT stop branch from
# `stop_blocked` (``_stop_point`` handles the two separately), and therefore not
# redundant coverage.
_AWAITING_APPROVAL_TABLE = """\
table: "silver.orders"
current_stage: "mapping_ready"
stages:
  source_ready: {status: "pass", evidence: ["profile"]}
  mapping_ready:
    status: "pass"
    evidence: ["mappings/orders/source-map.yaml"]
  silver_ready: {status: "not_started"}
  gold_ready: {status: "not_started"}
  semantic_model_ready: {status: "not_started"}
  dashboard_ready: {status: "not_started"}
  publish_ready: {status: "not_started"}
approvals: []
next_action: "approve the map"
"""


def test_passing_dbt_record_does_not_discharge_a_pending_approval(
    tmp_path: Path,
) -> None:
    """US2/FR-005: a green build is not a substitute for a named human."""
    baseline_root = tmp_path / "baseline"
    with_record = tmp_path / "with_record"
    for root in (baseline_root, with_record):
        _write_status(root, "orders", _AWAITING_APPROVAL_TABLE)
    _write_evidence(with_record, "orders", _record("pass"))

    baseline = build_agent_next_document(baseline_root)
    actual = build_agent_next_document(with_record)

    assert actual["outcome"] == "approval_required"
    assert actual["required_authority"] == baseline["required_authority"]
    assert actual == baseline


def test_failed_dbt_record_does_not_soften_a_pending_approval(tmp_path: Path) -> None:
    """The second stop branch: `approval_required`, not `stop_blocked`."""
    baseline_root = tmp_path / "baseline"
    with_record = tmp_path / "with_record"
    for root in (baseline_root, with_record):
        _write_status(root, "orders", _AWAITING_APPROVAL_TABLE)
    _write_evidence(with_record, "orders", _record("failed"))

    baseline = build_agent_next_document(baseline_root)
    actual = build_agent_next_document(with_record)

    assert actual["outcome"] == "approval_required"
    assert actual["next_allowed_action"] == baseline["next_allowed_action"]
    assert actual["stop_point"] == baseline["stop_point"]
    assert actual["required_authority"] == baseline["required_authority"]
    assert actual["forbidden_scope"] == baseline["forbidden_scope"]
    differing = {key for key in actual if actual[key] != baseline.get(key)}
    assert differing == {"caveats"}


def test_failed_dbt_record_does_not_soften_a_blocked_table(tmp_path: Path) -> None:
    """The round-2 defect, pinned.

    If the dbt signal joined the ``next_override`` chain, this blocked table's
    ``STOP`` sentence would be displaced by the dbt caveat and its
    blocked-specific ``stop_point`` would be skipped. The caveat is additive, so
    every other field must be byte-identical and the ONLY difference is the
    added caveat.
    """
    baseline_root = tmp_path / "baseline"
    with_record = tmp_path / "with_record"
    for root in (baseline_root, with_record):
        _write_status(root, "orders", _BLOCKED_TABLE)
    _write_evidence(with_record, "orders", _record("failed"))

    baseline = build_agent_next_document(baseline_root)
    actual = build_agent_next_document(with_record)

    # The stop survives, verbatim.
    assert actual["next_allowed_action"] == baseline["next_allowed_action"]
    assert actual["next_allowed_action"].startswith("STOP")
    assert actual["stop_point"] == baseline["stop_point"]
    assert "Stopped now" in actual["stop_point"]
    assert actual["outcome"] == baseline["outcome"]
    assert actual["forbidden_scope"] == baseline["forbidden_scope"]
    assert actual["readiness_state"] == baseline["readiness_state"]

    # The caveat is the ONLY difference in the whole document.
    assert actual["caveats"] != baseline["caveats"]
    differing = {key for key in actual if actual[key] != baseline.get(key)}
    assert differing == {"caveats"}


def _dbt_caveats(document: dict) -> list[dict]:
    return [c for c in document["caveats"] if c.get("kind") == "dbt_execution"]


def test_caveat_names_the_outcome_invocation_and_record_path(tmp_path: Path) -> None:
    _write_status(tmp_path, "orders", _BLOCKED_TABLE)
    _write_evidence(
        tmp_path,
        "orders",
        _record("failed", blocking_reasons=[{"reason": "relation does not exist"}]),
    )

    caveats = _dbt_caveats(build_agent_next_document(tmp_path))
    assert len(caveats) == 1
    detail = caveats[0]["detail"]

    assert "failed" in detail
    assert "20260808T141530Z-9f3a2b71" in detail
    assert "mappings/orders/dbt-evidence/20260808T141530Z-9f3a2b71.json" in detail
    assert "relation does not exist" in detail


def test_caveat_is_a_typed_dict_not_a_bare_string(tmp_path: Path) -> None:
    """``has_open_request`` calls ``.get('kind')`` on every caveat.

    A bare string would raise there, and a caveat reusing an approval-request
    kind would masquerade as an outstanding owner decision.
    """
    from seshat.approval_requests import OPEN_REQUEST_KIND, UNPARSED_REQUEST_KIND

    _write_status(tmp_path, "orders", _BLOCKED_TABLE)
    _write_evidence(tmp_path, "orders", _record("failed"))

    for caveat in build_agent_next_document(tmp_path)["caveats"]:
        assert isinstance(caveat, dict)
        assert caveat.get("kind") not in {OPEN_REQUEST_KIND, UNPARSED_REQUEST_KIND}


def test_unreadable_record_emits_a_caveat_naming_the_file(tmp_path: Path) -> None:
    _write_status(tmp_path, "orders", _BLOCKED_TABLE)
    path = (
        tmp_path
        / "mappings"
        / "orders"
        / "dbt-evidence"
        / "20260808T141530Z-9f3a2b71.json"
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("{truncated", encoding="utf-8")

    caveats = _dbt_caveats(build_agent_next_document(tmp_path))
    assert len(caveats) == 1
    assert "20260808T141530Z-9f3a2b71.json" in caveats[0]["detail"]


def test_absent_evidence_emits_no_caveat(tmp_path: Path) -> None:
    """Never having run dbt is not a defect and must not be reported as one."""
    _write_status(tmp_path, "orders", _BLOCKED_TABLE)
    assert build_agent_next_document(tmp_path)["caveats"] == []


# --------------------------------------------------------------------------
# T005 -- FR-017: the caveat must not present itself as a stop
# --------------------------------------------------------------------------


def test_caveat_does_not_claim_a_stop_it_cannot_impose(tmp_path: Path) -> None:
    """The caveat rides in ``caveats``; it is not an action and not a stop."""
    _write_status(tmp_path, "orders", _BLOCKED_TABLE)
    _write_evidence(tmp_path, "orders", _record("failed"))

    for caveat in _dbt_caveats(build_agent_next_document(tmp_path)):
        assert not caveat["detail"].startswith("STOP")
