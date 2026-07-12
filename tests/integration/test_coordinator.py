"""Integration test: the US2 dashboard coordinator fail-closed matrix (spec 123,
FR-033/FR-034/FR-010, SC-005).

The coordinator (`src/seshat/dashboard_coordinator.py`) is a pure state-inspection
helper: given committed paths it returns exactly ONE next allowed action, or a
`blocked` result that names what is missing/invalid, the evidence checked, the
responsible owner, and the action that would unblock progress (FR-034).

The oracle here sits ON the risk (memory: verifier must sit on the risk): every
test drives the REAL helper against a REAL committed-state fixture tree on disk --
never a mock that could pass without exercising the stop. Each fail-closed case
starts from the hand-authored approved-intent fixture (T017) and mutates exactly
one committed input to trip one precondition, proving the coordinator fails closed
on that trigger AND never self-grants `dashboard_ready: pass` (FR-010).
"""

from __future__ import annotations

import hashlib
import shutil
from pathlib import Path

import pytest

from seshat import dashboard_coordinator as dc

pytestmark = pytest.mark.unit

_REPO_ROOT = Path(__file__).resolve().parents[2]
_FIXTURE = _REPO_ROOT / "tests" / "fixtures" / "report_intent" / "approved_happy"
_SUBJECT = "mappings/demo_report_area"
_INTENT_REL = "mappings/demo_report_area/design/report-intent.yaml"
_STORE_REL = ".seshat/kpi-contracts.yaml"
_FLOW_REL = "contracts/knowledge/database-to-pbip-flow.yaml"
_AUTHORITY_REL = "contracts/knowledge/approval-authority.yaml"
_READINESS_REL = "mappings/demo_report_area/readiness-status.yaml"
_BINDING_REL = "mappings/demo_report_area/design/visual-contract-binding-map.md"


def _materialize(tmp_path: Path) -> tuple[Path, tuple[str, ...]]:
    """Copy the approved-intent fixture into a fresh workspace, add the real shipped
    flow + authority contracts, and inject the live sha256 of the committed intent
    into the report_intent_approval evidence_identity so the shipped decision gate
    accepts the approval as fresh (not stale). Returns (repo_root, tracked_files)."""
    root = tmp_path / "ws"
    shutil.copytree(_FIXTURE, root)

    # Bring in the real shipped contracts the gate machinery reads.
    for rel in (_FLOW_REL, _AUTHORITY_REL):
        dest = root / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(
            (_REPO_ROOT / rel).read_text(encoding="utf-8"), encoding="utf-8"
        )

    # Freshness: the gate compares recorded evidence_identity sha vs current file
    # bytes. Inject the digest of the copied intent file (raw bytes, as sha256_file
    # reads it) so a valid, non-stale approval is what we actually test against.
    intent_sha = hashlib.sha256((root / _INTENT_REL).read_bytes()).hexdigest()
    store = root / _STORE_REL
    store.write_text(
        store.read_text(encoding="utf-8").replace("__EVIDENCE_SHA__", intent_sha),
        encoding="utf-8",
    )

    tracked = _tracked(root)
    return root, tracked


def _tracked(root: Path) -> tuple[str, ...]:
    """Every file under the workspace, as posix repo-relative paths."""
    return tuple(
        p.relative_to(root).as_posix() for p in sorted(root.rglob("*")) if p.is_file()
    )


# --------------------------------------------------------------------------- #
# baseline: the unmutated approved fixture must NOT block (so a mutation-induced
# block is attributable to the mutation, not a broken fixture).
# --------------------------------------------------------------------------- #
def test_baseline_fixture_is_not_blocked(tmp_path: Path) -> None:
    root, tracked = _materialize(tmp_path)
    result = dc.next_action(root, _SUBJECT, tracked)
    assert result.outcome == "next_action", result
    assert result.blocked is None


# --------------------------------------------------------------------------- #
# FR-033 fail-closed matrix -- each trigger yields a conforming blocked result.
# --------------------------------------------------------------------------- #
def _assert_blocked_shape(result: dc.CoordinatorResult) -> dc.Blocked:
    """A conforming blocked result names what/evidence/owner/unblock (FR-034) and
    never self-grants dashboard_ready: pass (FR-010)."""
    assert result.outcome == "blocked", result
    assert result.action is None
    b = result.blocked
    assert b is not None
    assert b.what.strip(), "blocked.what must name what is missing/invalid"
    assert b.evidence.strip(), "blocked.evidence must name the evidence checked"
    assert b.owner.strip(), "blocked.owner must name the responsible owner"
    assert b.unblock.strip(), "blocked.unblock must name the unblocking action"
    # No self-grant (FR-010): a blocked coordinator never emits a dashboard-ready pass.
    assert result.stage != "dashboard_ready:pass"
    assert "dashboard_ready: pass" not in b.what
    return b


def test_semantic_model_not_pass_blocks(tmp_path: Path) -> None:
    root, tracked = _materialize(tmp_path)
    readiness = root / _READINESS_REL
    readiness.write_text(
        readiness.read_text(encoding="utf-8").replace(
            '  semantic_model_ready:\n    status: "pass"',
            '  semantic_model_ready:\n    status: "warning"',
        ),
        encoding="utf-8",
    )
    result = dc.next_action(root, _SUBJECT, tracked)
    b = _assert_blocked_shape(result)
    assert "semantic_model_ready" in b.what


def test_missing_contract_blocks_and_routes_upstream(tmp_path: Path) -> None:
    root, tracked = _materialize(tmp_path)
    # Remove one approved contract the intent references -> resolution gap (FR-004).
    (root / "mappings/demo_report_area/metrics/DemoCount.yaml").unlink()
    tracked = _tracked(root)
    result = dc.next_action(root, _SUBJECT, tracked)
    b = _assert_blocked_shape(result)
    assert "DemoCount" in b.what
    # Routes upstream to metric-contract definition (FR-004).
    assert "metric contract" in b.unblock.lower()


def test_unapproved_contract_blocks(tmp_path: Path) -> None:
    root, tracked = _materialize(tmp_path)
    # A present-but-not-approved contract is NOT a valid binding target (FR-003).
    metric = root / "mappings/demo_report_area/metrics/DemoCount.yaml"
    metric.write_text(
        metric.read_text(encoding="utf-8").replace(
            'status: "pass"', 'status: "not_started"'
        ),
        encoding="utf-8",
    )
    result = dc.next_action(root, _SUBJECT, tracked)
    b = _assert_blocked_shape(result)
    assert "DemoCount" in b.what


def test_orphan_visual_blocks(tmp_path: Path) -> None:
    root, tracked = _materialize(tmp_path)
    # Add a visual row whose bound_contract is empty -> orphan visual (SC-003).
    binding = root / _BINDING_REL
    text = binding.read_text(encoding="utf-8")
    orphan_row = "| v99 | table | q1 orphan detail |  | `[Unmapped]` |\n"
    # Insert the orphan row right after the v03 row (matched by a short unique key).
    anchor = "| v03 | bar | q1 sales by category | DemoSales |"
    line = next(ln for ln in text.splitlines(keepends=True) if ln.startswith(anchor))
    text = text.replace(line, line + orphan_row)
    binding.write_text(text, encoding="utf-8")
    result = dc.next_action(root, _SUBJECT, tracked)
    b = _assert_blocked_shape(result)
    assert "orphan" in b.what.lower() or "v99" in b.what


def test_visual_binding_unapproved_contract_blocks(tmp_path: Path) -> None:
    root, tracked = _materialize(tmp_path)
    # A visual binding a contract that is NOT among the approved contracts is an
    # orphan by SC-003 (traces to no approved contract), even if not blank.
    binding = root / _BINDING_REL
    binding.write_text(
        binding.read_text(encoding="utf-8").replace(
            "| v02 | card | q2 transaction volume | DemoCount | `[DemoCount]` |",
            "| v02 | card | q2 transaction volume | GhostMetric | `[GhostMetric]` |",
        ),
        encoding="utf-8",
    )
    result = dc.next_action(root, _SUBJECT, tracked)
    b = _assert_blocked_shape(result)
    assert "GhostMetric" in b.what or "orphan" in b.what.lower()


def test_missing_approval_stops_and_does_not_self_grant(tmp_path: Path) -> None:
    root, tracked = _materialize(tmp_path)
    # Remove the report_intent_approval decision from the store -> unapproved intent.
    (root / _STORE_REL).write_text("decisions: []\n", encoding="utf-8")
    result = dc.next_action(root, _SUBJECT, tracked)
    b = _assert_blocked_shape(result)
    assert "approval" in b.what.lower() or "intent" in b.what.lower()


def test_agent_identity_approval_is_rejected(tmp_path: Path) -> None:
    """No self-grant (FR-010/SC-008): an agent identity never satisfies approved_by,
    so an approval authored by 'agent' leaves the intent blocked."""
    root, tracked = _materialize(tmp_path)
    store = root / _STORE_REL
    store.write_text(
        store.read_text(encoding="utf-8").replace(
            'approved_by: "Dana Report (report_owner)"',
            'approved_by: "agent"',
        ),
        encoding="utf-8",
    )
    result = dc.next_action(root, _SUBJECT, tracked)
    _assert_blocked_shape(result)


def test_missing_intent_artifact_blocks(tmp_path: Path) -> None:
    root, tracked = _materialize(tmp_path)
    (root / _INTENT_REL).unlink()
    tracked = _tracked(root)
    result = dc.next_action(root, _SUBJECT, tracked)
    b = _assert_blocked_shape(result)
    assert "intent" in b.what.lower()
