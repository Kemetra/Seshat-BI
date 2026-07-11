"""Tests + verifier for the Approver Decision Surface (spec 115).

The verifier centers on REFUSAL-CASE COMPLETENESS (V1/V2) -- the real risk is a
refusal-eligible item silently landing in reassurance or dropped, not ordering
flake. Per contracts/verifier.md, the question-side completeness oracle is a
HAND-AUTHORED expected set, NEVER the production parser's own output (else a
parser bug drops the row from both sides and passes vacuously).
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

import pytest
import yaml

from seshat.approver_view import build_approver_view, render_view
from seshat.readiness_classify import CATEGORY_RANK

pytestmark = pytest.mark.unit


def _write(root: Path, table: str, status_yaml: str | None, questions_md: str | None):
    d = root / "mappings" / table
    d.mkdir(parents=True, exist_ok=True)
    if status_yaml is not None:
        (d / "readiness-status.yaml").write_text(status_yaml, encoding="utf-8")
    if questions_md is not None:
        (d / "unresolved-questions.md").write_text(questions_md, encoding="utf-8")


# --------------------------------------------------------------------------- #
# fixtures
# --------------------------------------------------------------------------- #
FULL_REFUSAL_STATUS = """
table: "t"
stages:
  source_ready:
    status: "pass"
  mapping_ready:
    status: "blocked"
    blocking_reasons:
      - "grain/PK not proven unique on the transformed data"
  silver_ready:
    status: "warning"
    blocking_reasons:
      - "live validation deferred: no DSN configured"
approvals: []
"""

# an approval-required stage that is 'pass' but has no valid approval
UNMET_APPROVAL_STATUS = """
table: "t"
stages:
  mapping_ready:
    status: "pass"
approvals: []
"""

ALL_PASS_STATUS = """
table: "t"
stages:
  mapping_ready:
    status: "pass"
approvals:
  - stage: "mapping_ready"
    owner: "Ahmed Shaaban (data_owner)"
    at: "2026-06-25"
"""

# open questions table with an OPEN governance row and an OPEN analyst row
QUESTIONS_OPEN = """
| ID | Question | Why | Who must answer | Default | Status | Resolution |
|----|----------|-----|-----------------|---------|--------|------------|
| Q1 | Is customer_id safe to publish? | PII | governance | drop | open | |
| Q2 | What does a blank mean? | metric | analyst | null | open | |
"""

# the AWKWARD-cell fixture (parser-under-test): backticked status, embedded pipe,
# padding. Q1 is answered (must NOT be a refusal), Q2 is open (must be).
QUESTIONS_AWKWARD = """
| ID | Question | Why | Who must answer | Default | Status | Res |
|----|----------|-----|-----------------|---------|--------|-----|
| `Q1` | Is `cust_id` safe? | PII | governance | drop | `answered` | keep |
| `Q2` |  weird spacing  | x | analyst | null | `open` |  |
"""


# --------------------------------------------------------------------------- #
# the completeness verifier (V1/V2/V3/V5), split into focused checks.
# The question-side oracle is HAND-AUTHORED (never the production parser output).
# --------------------------------------------------------------------------- #
_APPROVAL_STAGES = (
    "mapping_ready",
    "semantic_model_ready",
    "dashboard_ready",
    "publish_ready",
)


def _assert_blocked_reasons_present(block: dict, refusal_reasons: list[str]) -> None:
    if block.get("status") not in ("blocked", "warning"):
        return
    for reason in block.get("blocking_reasons") or []:
        assert reason in refusal_reasons, f"V1: dropped stage reason {reason!r}"


def _assert_unmet_approval_present(
    stage: str, block: dict, approved: set, refusal: list[dict]
) -> None:
    unmet = (
        block.get("status") == "pass"
        and stage in _APPROVAL_STAGES
        and stage not in approved
    )
    if unmet:
        assert any(stage in i["source"] for i in refusal), (
            f"V1: unmet approval for {stage} missing from refusal case"
        )


def _check_v1_stages(refusal: list[dict], status_yaml: dict) -> None:
    """Every blocked/warning reason + every unmet approval is in the refusal case."""
    approved = {
        a.get("stage")
        for a in (status_yaml.get("approvals") or [])
        if isinstance(a, dict)
    }
    reasons = [i["reason"] for i in refusal]
    for stage, block in (status_yaml.get("stages") or {}).items():
        if not isinstance(block, dict):
            continue
        _assert_blocked_reasons_present(block, reasons)
        _assert_unmet_approval_present(stage, block, approved, refusal)


def _check_v1_v2_questions(refusal: list[dict], expected_open_ids: set[str]) -> None:
    """V1: every hand-authored OPEN id present. V2 (non-vacuous): the question-
    sourced refusal COUNT equals the expected-open count -- too few = a dropped
    open, too many = a leaked ANSWERED (the backtick-parse bug the real fixture
    exposed). The guarantee sits ON the risk, not beside it."""
    srcs = " ".join(i["source"] for i in refusal)
    for qid in expected_open_ids:
        assert f"question {qid}" in srcs, (
            f"V1: open question {qid} missing from refusal case"
        )
    question_items = [i for i in refusal if "question " in i["source"]]
    assert len(question_items) == len(expected_open_ids), (
        f"V2: question refusal count {len(question_items)} != expected open "
        f"{len(expected_open_ids)} (dropped-open or leaked-answered)"
    )


def _check_v2_correct_side(refusal: list[dict], reassurance: list[dict]) -> None:
    text = " ".join(str(r) for r in reassurance)
    for reason in (i["reason"] for i in refusal):
        assert reason not in text, f"V2: refusal item in reassurance: {reason!r}"


def _check_v3_order(refusal: list[dict]) -> None:
    ranks = [i["rank"] for i in refusal]
    assert ranks == sorted(ranks), "V3: refusal not in fixed-rank order"
    for i in refusal:
        assert i["rank"] == CATEGORY_RANK.index(i["category"]), (
            "V3: rank is not the enum index"
        )


def _check_v5_no_score(view: dict) -> None:
    authored = re.sub(r'"[^"]*"', "", render_view(view))
    assert "N of M" not in authored, "V5: authored an N-of-M count"


def assert_refusal_case_complete(
    view: dict,
    status_yaml: dict,
    expected_open_question_ids: set[str],
) -> None:
    """V1 completeness + V2 correct-side + V3 order + V5 no-score.
    `expected_open_question_ids` is the hand-authored ground truth."""
    refusal = view["refusal_case"]
    _check_v1_stages(refusal, status_yaml)
    _check_v1_v2_questions(refusal, expected_open_question_ids)
    _check_v2_correct_side(refusal, view["reassurance"])
    _check_v3_order(refusal)
    _check_v5_no_score(view)


# --------------------------------------------------------------------------- #
# US1 -- refusal case first, fixed-rank order
# --------------------------------------------------------------------------- #
def test_refusal_first_order(tmp_path):
    _write(tmp_path, "t", FULL_REFUSAL_STATUS, QUESTIONS_OPEN)
    view = build_approver_view(tmp_path, "t")
    sm = yaml.safe_load(FULL_REFUSAL_STATUS)
    # governance question + grain blocker rank ABOVE the readiness/live items
    assert view["refusal_case"], "expected a non-empty refusal case"
    assert view["refusal_case"][0]["category"] == "approval"
    assert_refusal_case_complete(view, sm, expected_open_question_ids={"Q1", "Q2"})


def test_all_pass_nothing_to_refuse(tmp_path):
    _write(tmp_path, "t", ALL_PASS_STATUS, None)
    view = build_approver_view(tmp_path, "t")
    body = render_view(view)
    assert view["refusal_case"] == []
    assert "Nothing in the refusal case" in body
    # reassurance carries the pass stage + valid approval
    kinds = {r["kind"] for r in view["reassurance"]}
    assert "pass_stage" in kinds and "valid_approval" in kinds


def test_unmet_approval_is_refusal(tmp_path):
    _write(tmp_path, "t", UNMET_APPROVAL_STATUS, None)
    view = build_approver_view(tmp_path, "t")
    sm = yaml.safe_load(UNMET_APPROVAL_STATUS)
    assert any(i["category"] == "approval" for i in view["refusal_case"])
    assert_refusal_case_complete(view, sm, expected_open_question_ids=set())


# --------------------------------------------------------------------------- #
# US2 -- open questions owner-mapped; answered never a refusal
# --------------------------------------------------------------------------- #
def test_open_questions_owner_mapped(tmp_path):
    _write(tmp_path, "t", ALL_PASS_STATUS, QUESTIONS_OPEN)
    view = build_approver_view(tmp_path, "t")
    q = {i["source"].split("question ")[1]: i for i in view["refusal_case"]}
    # governance -> approval bucket (rank 0); analyst -> a later bucket
    assert q["Q1"]["category"] == "approval"
    assert q["Q1"]["rank"] < q["Q2"]["rank"]


def test_awkward_cells_answered_not_refusal(tmp_path):
    # PARSER-UNDER-TEST (V1 independent oracle): backticked/padded cells. Q1 is
    # answered -> must NOT be in the refusal case; Q2 open -> must be. This is the
    # exact bug the real fixture exposed (backticked `answered` mis-read as open).
    _write(tmp_path, "t", ALL_PASS_STATUS, QUESTIONS_AWKWARD)
    view = build_approver_view(tmp_path, "t")
    sm = yaml.safe_load(ALL_PASS_STATUS)
    srcs = " ".join(i["source"] for i in view["refusal_case"])
    assert "question Q2" in srcs, "open Q2 must be in the refusal case"
    assert "question Q1" not in srcs, "answered Q1 must NOT be in the refusal case"
    # hand-authored oracle: ONLY Q2 is open
    assert_refusal_case_complete(view, sm, expected_open_question_ids={"Q2"})


# --------------------------------------------------------------------------- #
# US3 -- missing input surfaced, not fabricated
# --------------------------------------------------------------------------- #
def test_missing_status_named(tmp_path):
    _write(tmp_path, "t", None, QUESTIONS_OPEN)
    view = build_approver_view(tmp_path, "t")
    body = render_view(view)
    assert any("readiness-status.yaml" in m for m in view["missing_inputs"])
    assert "Inputs not available" in body


def test_missing_questions_not_no_questions(tmp_path):
    _write(tmp_path, "t", ALL_PASS_STATUS, None)
    view = build_approver_view(tmp_path, "t")
    body = render_view(view)
    assert any("unresolved-questions.md" in m for m in view["missing_inputs"])
    # distinguishes "not available" from "no open questions"
    assert "NOT the same as" in body


# --------------------------------------------------------------------------- #
# no-write proof (V6) + generic (V8) + CLI
# --------------------------------------------------------------------------- #
def test_module_has_no_write_call():
    src = Path("src/seshat/approver_view.py").read_text(encoding="utf-8")
    assert "write_text" not in src
    assert ".write(" not in src
    assert "open(" not in src  # the read uses Path.read_text, not open()


def test_cli_writes_nothing(tmp_path):
    from seshat.cli.commands.approver_view import approver_view_main

    _write(tmp_path, "t", FULL_REFUSAL_STATUS, QUESTIONS_OPEN)
    tdir = tmp_path / "mappings" / "t"
    before = {p.name for p in tdir.iterdir()}
    args = argparse.Namespace(repo=str(tmp_path), table="t", output_format="text")
    assert approver_view_main(args) == 0
    after = {p.name for p in tdir.iterdir()}
    assert before == after, "approver-view must write nothing"


def test_generic_two_tables(tmp_path):
    _write(tmp_path, "one", FULL_REFUSAL_STATUS, QUESTIONS_OPEN)
    _write(tmp_path, "two", ALL_PASS_STATUS, None)
    v1 = build_approver_view(tmp_path, "one")
    v2 = build_approver_view(tmp_path, "two")
    assert v1["refusal_case"] and not v2["refusal_case"]
