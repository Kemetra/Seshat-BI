"""Tests for the read-only run-next readiness surface (spec 080)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from seshat.cli import main
from seshat.run_next import build_run_next_response

pytestmark = pytest.mark.unit


def _write_status(tmp_path: Path, table_dir: str, body: str) -> Path:
    path = tmp_path / "mappings" / table_dir / "readiness-status.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")
    return path


def test_missing_status_starts_at_source_ready(tmp_path: Path) -> None:
    result = build_run_next_response(tmp_path, "silver.new_table")
    assert result["table"] == "silver.new_table"
    assert result["outcome"] == "next_action"
    assert result["stage"] == "source_ready"
    assert "Source Ready" in result["action_text"]
    assert result["read_only_proof"] is True


def test_forward_action_uses_earliest_non_pass_stage(tmp_path: Path) -> None:
    _write_status(
        tmp_path,
        "orders",
        """\
table: "silver.orders"
current_stage: "mapping_ready"
stages:
  source_ready:
    status: "pass"
    evidence: ["mappings/orders/source-profile.md"]
  mapping_ready:
    status: "not_started"
  silver_ready:
    status: "not_started"
  gold_ready:
    status: "not_started"
  semantic_model_ready:
    status: "not_started"
  dashboard_ready:
    status: "not_started"
  publish_ready:
    status: "not_started"
approvals: []
next_action: "Begin Mapping Ready (Stage 2) -- the source-mapping gate."
""",
    )

    result = build_run_next_response(tmp_path, "silver.orders")
    assert result["outcome"] == "next_action"
    assert result["stage"] == "mapping_ready"
    assert "Mapping Ready" in result["action_text"]


def test_blocked_stage_stops_with_verbatim_reasons(tmp_path: Path) -> None:
    _write_status(
        tmp_path,
        "orders",
        """\
table: "silver.orders"
current_stage: "mapping_ready"
stages:
  source_ready:
    status: "pass"
    evidence: ["mappings/orders/source-profile.md"]
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
""",
    )

    result = build_run_next_response(tmp_path, "orders")
    assert result["outcome"] == "stop_blocked"
    assert result["stage"] == "mapping_ready"
    assert result["blocking_reasons"] == ["grain not confirmed unique on data"]
    assert result["action_text"] is None


def test_pass_stage_missing_shape_valid_approval_requires_human(tmp_path: Path) -> None:
    _write_status(
        tmp_path,
        "orders",
        """\
table: "silver.orders"
current_stage: "semantic_model_ready"
stages:
  source_ready:
    status: "pass"
    evidence: ["mappings/orders/source-profile.md"]
  mapping_ready:
    status: "pass"
    evidence: ["mappings/orders/source-map.yaml"]
  silver_ready:
    status: "pass"
    evidence: ["warehouse/migrations/0001_silver.sql"]
  gold_ready:
    status: "pass"
    evidence: ["warehouse/migrations/0002_gold.sql", "retail validate exit 0"]
  semantic_model_ready:
    status: "pass"
    evidence: ["powerbi/Orders.SemanticModel"]
  dashboard_ready: {status: "not_started"}
  publish_ready: {status: "not_started"}
approvals:
  - {stage: mapping_ready, owner: "Ada Lovelace (analyst)", at: "2026-07-01"}
  - {stage: semantic_model_ready, owner: "metric_owner", at: "2026-07-01"}
next_action: "done"
""",
    )

    result = build_run_next_response(tmp_path, "orders")
    assert result["outcome"] == "approval_required"
    assert result["stage"] == "semantic_model_ready"
    assert result["required_authority"] == "metric_owner"
    # An approval_required response now CARRIES its guidance (issue #487): with
    # action_text None the default `next --table` text surface rendered no action
    # line at all, so the reader was told to obtain an approval but never what a
    # valid one looks like. The gate itself is unchanged -- the bare-role owner
    # above still fails, which is why this is approval_required.
    action_text = result["action_text"]
    assert action_text is not None
    assert "never self-grant it" in action_text
    assert "approvals" in action_text


def test_terminal_pass_when_all_approvals_are_shape_valid(tmp_path: Path) -> None:
    _write_status(
        tmp_path,
        "orders",
        """\
table: "silver.orders"
current_stage: "publish_ready"
stages:
  source_ready: {status: "pass", evidence: ["profile"]}
  mapping_ready: {status: "pass", evidence: ["map"]}
  silver_ready: {status: "pass", evidence: ["silver"]}
  gold_ready: {status: "pass", evidence: ["gold"]}
  semantic_model_ready: {status: "pass", evidence: ["model"]}
  dashboard_ready: {status: "pass", evidence: ["dashboard"]}
  publish_ready: {status: "pass", evidence: ["handoff"]}
approvals:
  - {stage: mapping_ready, owner: "Ada Lovelace (analyst)", at: "2026-07-01"}
  - stage: semantic_model_ready
    owner: "Grace Hopper (metric_owner)"
    at: "2026-07-01"
  - {stage: dashboard_ready, owner: "Katherine Johnson (governance)", at: "2026-07-01"}
  - {stage: publish_ready, owner: "Ahmed Shaaban (data_owner)", at: "2026-07-01"}
next_action: "done"
""",
    )

    result = build_run_next_response(tmp_path, "orders")
    assert result["outcome"] == "terminal_pass"
    assert result["stage"] is None
    assert result["action_text"] is None


def test_pass_without_evidence_is_caveated_not_silently_hidden(tmp_path: Path) -> None:
    _write_status(
        tmp_path,
        "orders",
        """\
table: "silver.orders"
current_stage: "silver_ready"
stages:
  source_ready: {status: "pass", evidence: ["profile"]}
  mapping_ready: {status: "pass", evidence: []}
  silver_ready: {status: "not_started"}
  gold_ready: {status: "not_started"}
  semantic_model_ready: {status: "not_started"}
  dashboard_ready: {status: "not_started"}
  publish_ready: {status: "not_started"}
approvals:
  - {stage: mapping_ready, owner: "Ada Lovelace (analyst)", at: "2026-07-01"}
next_action: "write silver"
""",
    )

    result = build_run_next_response(tmp_path, "orders")
    assert result["outcome"] == "next_action"
    assert result["stage"] == "silver_ready"
    assert any(c["kind"] == "pass_without_evidence" for c in result["caveats"])


def test_cli_next_json_is_read_only_and_score_free(tmp_path: Path, capsys) -> None:
    _write_status(
        tmp_path,
        "orders",
        """\
table: "silver.orders"
current_stage: "mapping_ready"
stages:
  source_ready: {status: "pass", evidence: ["profile"]}
  mapping_ready: {status: "not_started"}
  silver_ready: {status: "not_started"}
  gold_ready: {status: "not_started"}
  semantic_model_ready: {status: "not_started"}
  dashboard_ready: {status: "not_started"}
  publish_ready: {status: "not_started"}
approvals: []
next_action: "Begin Mapping Ready (Stage 2) -- the source-mapping gate."
""",
    )
    before = sorted(p.relative_to(tmp_path) for p in tmp_path.rglob("*") if p.is_file())

    exit_code = main(
        [
            "next",
            "--repo",
            str(tmp_path),
            "--table",
            "silver.orders",
            "--format",
            "json",
        ]
    )

    assert exit_code == 0
    parsed = json.loads(capsys.readouterr().out)
    assert parsed["outcome"] == "next_action"
    dumped = json.dumps(parsed).lower()
    for banned in ("score", "confidence", "health", "maturity"):
        assert banned not in dumped
    after = sorted(p.relative_to(tmp_path) for p in tmp_path.rglob("*") if p.is_file())
    assert before == after


# --------------------------------------------------------------------------- #
# Open approval requests must be REACHABLE through the product interface.
#
# Codex review of PR #516 (P1): a packaged approval-request document created an
# `open` owner decision, but `next` returned a bare `terminal_pass` because it
# reads readiness STAGES only -- so an agent following the conductor path stopped
# and the pending decision was unreachable. The stages are legitimately `pass`
# (the signed design IS complete), so the honest surface is a CAVEAT on the
# non-blocking verdict, not a fabricated `blocked`.
# --------------------------------------------------------------------------- #

_ALL_PASS_STATUS = """\
table: "silver.orders"
current_stage: "publish_ready"
stages:
  source_ready: {status: "pass", evidence: ["profile"]}
  mapping_ready: {status: "pass", evidence: ["map"]}
  silver_ready: {status: "pass", evidence: ["silver"]}
  gold_ready: {status: "pass", evidence: ["gold"]}
  semantic_model_ready: {status: "pass", evidence: ["model"]}
  dashboard_ready: {status: "pass", evidence: ["dashboard"]}
  publish_ready: {status: "pass", evidence: ["handoff"]}
approvals:
  - {stage: mapping_ready, owner: "Ada Lovelace (analyst)", at: "2026-07-01"}
  - stage: semantic_model_ready
    owner: "Grace Hopper (metric_owner)"
    at: "2026-07-01"
  - {stage: dashboard_ready, owner: "Katherine Johnson (governance)", at: "2026-07-01"}
  - {stage: publish_ready, owner: "Ahmed Shaaban (data_owner)", at: "2026-07-01"}
next_action: "done"
"""

_OPEN_REQUEST = """\
# Approval Request -- `narrative-brief-migration`

- **question_id:** `narrative-brief-migration`
- **stage:** `dashboard_ready`
- **status:** `open`
"""


def _write_request(root: Path, table: str, name: str, body: str) -> None:
    target = root / "mappings" / table / f"approval-request-{name}.md"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(body, encoding="utf-8")


def test_open_approval_request_surfaces_as_a_caveat_on_terminal_pass(
    tmp_path: Path,
) -> None:
    """An `open` request must be VISIBLE on the otherwise-clean verdict, so the
    conductor can present it instead of stopping at a bare `terminal_pass`."""
    _write_status(tmp_path, "orders", _ALL_PASS_STATUS)
    _write_request(tmp_path, "orders", "narrative-brief-migration", _OPEN_REQUEST)

    result = build_run_next_response(tmp_path, "orders")

    assert result["outcome"] == "terminal_pass"
    caveats = [c for c in result["caveats"] if c["kind"] == "open_approval_request"]
    assert caveats, f"expected an open_approval_request caveat, got {result['caveats']}"
    detail = caveats[0]["detail"]
    assert "narrative-brief-migration" in detail
    assert "approval-request-narrative-brief-migration.md" in detail


_DECISION = """\
# Approval Decision -- `already-ruled`

- **question_id:** `already-ruled`
- **selected_option:** `D1=A`
- **owner:** `Ahmed Shaaban (report_owner)`
- **date:** `2026-07-26`
- **rationale:** the named owner ruled as recorded above.
"""


def _write_decision(root: Path, table: str, name: str, body: str) -> None:
    target = root / "mappings" / table / f"approval-decision-{name}.md"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(body, encoding="utf-8")


def _answered_request(root: Path) -> None:
    _write_status(root, "orders", _ALL_PASS_STATUS)
    _write_request(
        root, "orders", "already-ruled", _OPEN_REQUEST.replace("`open`", "`answered`")
    )


def test_answered_request_goes_quiet_only_with_a_valid_decision_file(
    tmp_path: Path,
) -> None:
    """`answered` is honoured ONLY when the paired decision file corroborates it
    (matching question_id + a named owner). Then the request is settled."""
    _answered_request(tmp_path)
    _write_decision(tmp_path, "orders", "already-ruled", _DECISION)

    result = build_run_next_response(tmp_path, "orders")

    assert result["outcome"] == "terminal_pass"
    kinds = {c["kind"] for c in result["caveats"]}
    assert "open_approval_request" not in kinds
    assert "unverified_answered_request" not in kinds


def test_answered_without_a_decision_file_is_not_trusted(tmp_path: Path) -> None:
    """THE FORGERY GUARD: flipping `status:` to `answered` must NOT silence the
    request when no paired decision file exists. A one-token edit cannot make the
    product behave as though a named human ruled."""
    _answered_request(tmp_path)

    result = build_run_next_response(tmp_path, "orders")

    caveats = [
        c for c in result["caveats"] if c["kind"] == "unverified_answered_request"
    ]
    assert caveats, f"an unbacked `answered` must stay visible, got {result['caveats']}"
    assert "no paired approval-decision-already-ruled.md exists" in caveats[0]["detail"]


def test_answered_with_a_mismatched_decision_question_id_is_not_trusted(
    tmp_path: Path,
) -> None:
    """A decision file for a DIFFERENT question does not settle this request."""
    _answered_request(tmp_path)
    _write_decision(
        tmp_path,
        "orders",
        "already-ruled",
        _DECISION.replace("question_id:** `already-ruled`", "question_id:** `other`"),
    )

    result = build_run_next_response(tmp_path, "orders")

    assert [c for c in result["caveats"] if c["kind"] == "unverified_answered_request"]


def test_answered_with_an_ownerless_decision_file_is_not_trusted(
    tmp_path: Path,
) -> None:
    """A decision record naming no owner is not a named-human ruling.

    Complete in every OTHER respect, so this test isolates the ownerless risk
    rather than tripping the completeness check first.
    """
    _answered_request(tmp_path)
    _write_decision(
        tmp_path,
        "orders",
        "already-ruled",
        _DECISION.replace("- **owner:** `Ahmed Shaaban (report_owner)`\n", ""),
    )

    result = build_run_next_response(tmp_path, "orders")

    caveats = [
        c for c in result["caveats"] if c["kind"] == "unverified_answered_request"
    ]
    assert caveats and "names no owner" in caveats[0]["detail"]


def test_unknown_request_status_is_reported_not_skipped(tmp_path: Path) -> None:
    """An unrecognized status word must not fall through as a silent pass."""
    _write_status(tmp_path, "orders", _ALL_PASS_STATUS)
    _write_request(
        tmp_path, "orders", "typo-status", _OPEN_REQUEST.replace("`open`", "`opne`")
    )

    result = build_run_next_response(tmp_path, "orders")

    kinds = {c["kind"] for c in result["caveats"]}
    assert "unparsed_approval_request" in kinds


def test_open_request_caveat_does_not_fabricate_a_blocked_verdict(
    tmp_path: Path,
) -> None:
    """The signed stages stay `pass`: an open follow-up decision is a caveat, not
    a blocker. Flipping a real approval to `blocked` would falsify it."""
    _write_status(tmp_path, "orders", _ALL_PASS_STATUS)
    _write_request(tmp_path, "orders", "narrative-brief-migration", _OPEN_REQUEST)

    result = build_run_next_response(tmp_path, "orders")

    assert result["outcome"] == "terminal_pass"
    assert result["stage"] is None
    assert result.get("blocking_reasons") in (None, [], ())


def test_unreadable_request_is_reported_not_silently_skipped(tmp_path: Path) -> None:
    """A request whose `status:` cannot be parsed must NOT be treated as
    answered -- a silent skip on an unreadable artifact is a fail-open."""
    _write_status(tmp_path, "orders", _ALL_PASS_STATUS)
    _write_request(
        tmp_path, "orders", "no-status-field", "# Approval Request\n\nprose\n"
    )

    result = build_run_next_response(tmp_path, "orders")

    kinds = {c["kind"] for c in result["caveats"]}
    assert "unparsed_approval_request" in kinds, (
        f"an unreadable request must be reported, got {result['caveats']}"
    )


# --------------------------------------------------------------------------- #
# A decision file must be a COMPLETE, CORRECTLY-AUTHORIZED ruling.
#
# Codex review of PR #516 (P1): corroborating only "filename-derived id + any
# nonempty owner" let a two-line stub naming the WRONG authority class close a
# request. The request declares `owner_required`, and its protocol requires
# selected_option / date / rationale -- so both are checked here.
# --------------------------------------------------------------------------- #

_REQUEST_WITH_AUTHORITY = """\
# Approval Request -- `needs-report-owner`

- **question_id:** `needs-report-owner`
- **owner_required:** `report-owner`
- **status:** `answered`
"""

_COMPLETE_DECISION = """\
# Approval Decision -- `needs-report-owner`

- **question_id:** `needs-report-owner`
- **selected_option:** `D1=A, D2=B`
- **owner:** `Ahmed Shaaban (report_owner)`
- **date:** `2026-07-26`
- **rationale:** the named report owner ruled as recorded above.
"""


def _authority_case(root: Path, decision: str) -> dict:
    _write_status(root, "orders", _ALL_PASS_STATUS)
    _write_request(root, "orders", "needs-report-owner", _REQUEST_WITH_AUTHORITY)
    _write_decision(root, "orders", "needs-report-owner", decision)
    return build_run_next_response(root, "orders")


def _unverified(result: dict) -> list[dict]:
    return [c for c in result["caveats"] if c["kind"] == "unverified_answered_request"]


def test_complete_correctly_authorized_decision_settles_the_request(
    tmp_path: Path,
) -> None:
    """The positive control: a ruling that IS complete and correctly authorized
    genuinely settles the request, so the guard is not simply always-on."""
    result = _authority_case(tmp_path, _COMPLETE_DECISION)

    assert not _unverified(result), result["caveats"]


def test_decision_from_the_wrong_authority_class_does_not_settle_it(
    tmp_path: Path,
) -> None:
    """THE AUTHORITY GUARD: a `metric_owner` signature cannot close a request
    whose `owner_required` is `report-owner`."""
    result = _authority_case(
        tmp_path,
        _COMPLETE_DECISION.replace(
            "Ahmed Shaaban (report_owner)", "Mallory (metric_owner)"
        ),
    )

    caveats = _unverified(result)
    assert caveats, "a wrong-authority ruling must not settle the request"
    assert "does not carry the required" in caveats[0]["detail"]


def test_incomplete_decision_does_not_settle_the_request(tmp_path: Path) -> None:
    """A stub missing the protocol's fields is not a ruling, even from the right
    owner: it answers none of the sub-decisions."""
    result = _authority_case(
        tmp_path,
        "# Approval Decision\n\n- **question_id:** `needs-report-owner`\n"
        "- **owner:** `Ahmed Shaaban (report_owner)`\n",
    )

    caveats = _unverified(result)
    assert caveats, "an incomplete ruling must not settle the request"
    assert "incomplete ruling" in caveats[0]["detail"]
    detail = caveats[0]["detail"]
    assert "selected_option" in detail and "date" in detail and "rationale" in detail


def test_hyphen_vs_underscore_authority_still_matches(tmp_path: Path) -> None:
    """`report-owner` and `report_owner` name the same class -- a decision must
    not be rejected over a separator."""
    result = _authority_case(tmp_path, _COMPLETE_DECISION)

    assert not _unverified(result)


def test_request_without_owner_required_accepts_any_named_owner(
    tmp_path: Path,
) -> None:
    """The check cannot invent a requirement the request never made."""
    result = _authority_case(
        tmp_path,
        _COMPLETE_DECISION.replace(
            "Ahmed Shaaban (report_owner)", "Someone Else (governance)"
        ),
    )
    # This request DOES declare owner_required, so the above must be rejected...
    assert _unverified(result)

    # ...but one that does not declare it accepts the same owner.
    _write_request(
        tmp_path,
        "orders",
        "no-authority-stated",
        _REQUEST_WITH_AUTHORITY.replace(
            "- **owner_required:** `report-owner`\n", ""
        ).replace("needs-report-owner", "no-authority-stated"),
    )
    _write_decision(
        tmp_path,
        "orders",
        "no-authority-stated",
        _COMPLETE_DECISION.replace("needs-report-owner", "no-authority-stated").replace(
            "Ahmed Shaaban (report_owner)", "Someone Else (governance)"
        ),
    )
    second = build_run_next_response(tmp_path, "orders")
    assert not [
        c
        for c in second["caveats"]
        if c["kind"] == "unverified_answered_request"
        and "no-authority-stated" in c["detail"]
    ]
