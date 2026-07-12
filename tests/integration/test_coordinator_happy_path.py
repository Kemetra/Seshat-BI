"""Integration test: the US2 coordinator happy path + traceability (spec 123,
FR-002a, SC-003, SC-012).

Given the hand-authored approved-intent fixture (T017) -- an approved Report
Intent, a ready semantic model, and approved metric contracts -- the coordinator's
next-action sequence authorizes the reviewable design (page blueprints, visual
specs, report composition) and STOPS at the human blueprint-review seam without
self-granting `dashboard_ready: pass` (FR-010). Every visual traces to an approved
contract + a mapped field (SC-003 zero orphans), and each blueprint
`business_question` traces to a question declared in the committed Report Intent
(FR-002a).

The oracle drives the REAL helper against the REAL committed fixture tree.
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


def _materialize(tmp_path: Path) -> tuple[Path, tuple[str, ...]]:
    root = tmp_path / "ws"
    shutil.copytree(_FIXTURE, root)
    for rel in (_FLOW_REL, _AUTHORITY_REL):
        dest = root / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(
            (_REPO_ROOT / rel).read_text(encoding="utf-8"), encoding="utf-8"
        )
    intent_sha = hashlib.sha256((root / _INTENT_REL).read_bytes()).hexdigest()
    store = root / _STORE_REL
    store.write_text(
        store.read_text(encoding="utf-8").replace("__EVIDENCE_SHA__", intent_sha),
        encoding="utf-8",
    )
    tracked = tuple(
        p.relative_to(root).as_posix() for p in sorted(root.rglob("*")) if p.is_file()
    )
    return root, tracked


def test_happy_path_authorizes_design_and_stops_at_human_review(tmp_path: Path) -> None:
    root, tracked = _materialize(tmp_path)
    result = dc.next_action(root, _SUBJECT, tracked)

    # With all preconditions met and the design authored, the one next allowed
    # action is the human blueprint review seam -- NOT a self-granted pass.
    assert result.outcome == "next_action", result
    assert result.blocked is None
    assert result.action is not None
    assert "review" in result.action.lower()
    # Never self-grant dashboard_ready: pass (FR-010).
    assert "self" not in result.action.lower() or "never" in result.action.lower()
    assert result.stage != "dashboard_ready:pass"


def test_happy_path_zero_orphan_visuals_all_trace_to_approved_contract(
    tmp_path: Path,
) -> None:
    """SC-003: every visual in the approved blueprint traces to an approved contract
    and a mapped semantic field (binding-map coverage complete)."""
    root, tracked = _materialize(tmp_path)
    trace = dc.trace_design(root, _SUBJECT)

    assert trace.orphan_visuals == ()
    assert trace.visuals  # non-empty
    approved = set(trace.approved_contracts)
    for visual in trace.visuals:
        assert visual.bound_contract, f"visual {visual.visual_id} has no contract"
        assert visual.bound_contract in approved, (
            f"visual {visual.visual_id} binds {visual.bound_contract!r}, "
            f"not among approved {sorted(approved)}"
        )
        assert visual.field, f"visual {visual.visual_id} has no mapped field"


def test_happy_path_blueprint_questions_trace_to_intent(tmp_path: Path) -> None:
    """FR-002a: a blueprint business_question traces to a question declared in the
    committed Report Intent (no orphan question)."""
    root, tracked = _materialize(tmp_path)
    trace = dc.trace_design(root, _SUBJECT)

    intent_qids = set(trace.intent_question_ids)
    assert intent_qids == {"q1", "q2"}
    assert trace.orphan_questions == ()
    for visual in trace.visuals:
        # Each visual's business_question references a committed intent question id.
        assert any(qid in visual.business_question for qid in intent_qids), (
            f"visual {visual.visual_id} question {visual.business_question!r} "
            f"traces to no intent question {sorted(intent_qids)}"
        )


def test_trace_flags_orphan_question(tmp_path: Path) -> None:
    """A blueprint business_question with no matching intent question is surfaced as
    an orphan (FR-002a coherence)."""
    root, tracked = _materialize(tmp_path)
    binding = root / "mappings/demo_report_area/design/visual-contract-binding-map.md"
    binding.write_text(
        binding.read_text(encoding="utf-8").replace(
            "| v03 | bar | q1 sales by category | DemoSales |",
            "| v03 | bar | q7 unlisted question | DemoSales |",
        ),
        encoding="utf-8",
    )
    trace = dc.trace_design(root, _SUBJECT)
    assert any("q7" in q for q in trace.orphan_questions)
