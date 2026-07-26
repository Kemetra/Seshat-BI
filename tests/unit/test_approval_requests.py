"""Open ``approval-request-*.md`` surfacing (issue #517), including the
adversarial cases that defeated the reverted PR #516 design.

The forgery tests are the point of this file. PR #516 passed its own tests three
times while carrying a live fail-open, because it keyed trust on the request
markdown. Every ``test_forged_*`` below reproduces a bypass that WORKED against
that design and asserts it no longer silences a request.
"""

from __future__ import annotations

import pytest

from seshat.approval_requests import (
    OPEN_REQUEST_KIND,
    UNPARSED_REQUEST_KIND,
    has_open_request,
    open_request_caveats,
)

pytestmark = pytest.mark.unit

# A shape-valid approval naming a decision record: the ONLY thing that settles a
# request. Mirrors the committed retail_store_sales shape.
_VALID_APPROVAL = {
    "stage": "semantic_model_ready",
    "owner": "Ahmed Shaaban (metric_owner)",
    "at": "2026-07-05",
    "note": "AMENDMENT ... record: approval-decision-H9-time-intel.md.",
}


def _request(directory, qid: str, body: str = "- **status:** `open`\n") -> None:
    (directory / f"approval-request-{qid}.md").write_text(body, encoding="utf-8")


def _kinds(caveats) -> list[str]:
    return [c["kind"] for c in caveats]


def _qids(caveats) -> set[str]:
    """Question ids named in the caveat details."""
    return {c["detail"].split("'")[1] for c in caveats}


# --------------------------------------------------------------------------
# Core behaviour
# --------------------------------------------------------------------------


def test_request_with_shape_valid_approval_is_silent(tmp_path):
    _request(tmp_path, "H9-time-intel")
    assert open_request_caveats(tmp_path, [_VALID_APPROVAL]) == []


def test_request_without_any_approval_is_reported(tmp_path):
    _request(tmp_path, "narrative-brief-migration")
    caveats = open_request_caveats(tmp_path, [])
    assert _kinds(caveats) == [OPEN_REQUEST_KIND]
    assert "narrative-brief-migration" in caveats[0]["detail"]


def test_settled_and_open_requests_are_discriminated_together(tmp_path):
    """The real committed shape: two settled, two open, in one directory."""
    for qid in ("H9-time-intel", "YTD-year-start"):
        _request(tmp_path, qid)
    for qid in ("narrative-brief-migration", "source-profile-writethrough"):
        _request(tmp_path, qid)
    ytd = dict(_VALID_APPROVAL, note="record: approval-decision-YTD-year-start.md.")
    caveats = open_request_caveats(tmp_path, [_VALID_APPROVAL, ytd])
    assert _qids(caveats) == {
        "narrative-brief-migration",
        "source-profile-writethrough",
    }


def test_absent_or_missing_directory_yields_no_caveats(tmp_path):
    assert open_request_caveats(None, []) == []
    assert open_request_caveats(tmp_path / "nope", []) == []


def test_directory_with_no_requests_yields_no_caveats(tmp_path):
    (tmp_path / "readiness-status.yaml").write_text("x: 1", encoding="utf-8")
    assert open_request_caveats(tmp_path, []) == []


# --------------------------------------------------------------------------
# Adversarial: every one of these BYPASSED the reverted PR #516 design
# --------------------------------------------------------------------------


def test_forged_answered_status_does_not_silence_the_request(tmp_path):
    """Bypass 1: `status: answered` was a one-token edit that silenced it.

    The status field is never read now, so writing it changes nothing.
    """
    _request(tmp_path, "narrative-brief-migration", "- **status:** `answered`\n")
    assert _kinds(open_request_caveats(tmp_path, [])) == [OPEN_REQUEST_KIND]


def test_forged_bare_role_owner_does_not_silence_the_request(tmp_path):
    """Bypass 2: `owner: report_owner` -- a bare ROLE with no named person --
    passed the reverted design's substring authority check. It is rejected here
    because ``approval_is_shape_valid`` requires a named human."""
    _request(tmp_path, "narrative-brief-migration")
    forged = dict(
        _VALID_APPROVAL,
        owner="report_owner",
        note="record: approval-decision-narrative-brief-migration.md.",
    )
    assert _kinds(open_request_caveats(tmp_path, [forged])) == [OPEN_REQUEST_KIND]


def test_placeholder_ruling_fields_do_not_silence_the_request(tmp_path):
    """Bypass 3: `date: TBD` / `rationale: <pending>` counted as a complete
    ruling under presence-only checks. Here an approval missing a real date
    fails the shape check outright."""
    _request(tmp_path, "narrative-brief-migration")
    forged = dict(
        _VALID_APPROVAL,
        at="TBD",
        note="record: approval-decision-narrative-brief-migration.md.",
    )
    assert _kinds(open_request_caveats(tmp_path, [forged])) == [OPEN_REQUEST_KIND]


def test_decision_file_alone_does_not_silence_the_request(tmp_path):
    """A sibling decision document is NOT trust. Only a shape-valid
    ``approvals[]`` entry naming it counts -- writing the file is not enough."""
    _request(tmp_path, "narrative-brief-migration")
    (tmp_path / "approval-decision-narrative-brief-migration.md").write_text(
        "- **selected_option:** A\n- **owner:** Someone (data_owner)\n",
        encoding="utf-8",
    )
    assert _kinds(open_request_caveats(tmp_path, [])) == [OPEN_REQUEST_KIND]


def test_approval_for_a_different_question_does_not_silence_the_request(tmp_path):
    """A valid approval settling ANOTHER question must not settle this one."""
    _request(tmp_path, "narrative-brief-migration")
    assert _kinds(open_request_caveats(tmp_path, [_VALID_APPROVAL])) == [
        OPEN_REQUEST_KIND
    ]


@pytest.mark.parametrize("approvals", [None, "approved", 42, {}, [None], ["x"]])
def test_malformed_approvals_container_never_silences_a_request(tmp_path, approvals):
    """A non-list, or a list of non-dicts, contributes no trust."""
    _request(tmp_path, "narrative-brief-migration")
    assert _kinds(open_request_caveats(tmp_path, approvals)) == [OPEN_REQUEST_KIND]


# --------------------------------------------------------------------------
# Fail-closed: reported, never skipped (#453 posture)
# --------------------------------------------------------------------------


def test_undecodable_request_is_reported_not_skipped(tmp_path):
    path = tmp_path / "approval-request-broken.md"
    path.write_bytes(b"\xff\xfe\x00\x00 invalid utf-8 \xc3\x28")
    caveats = open_request_caveats(tmp_path, [])
    assert _kinds(caveats) == [UNPARSED_REQUEST_KIND]
    assert "reported rather than skipped" in caveats[0]["detail"]


def test_unreadable_request_still_counts_as_outstanding(tmp_path):
    """An unreadable request is not KNOWN to be settled, so it must keep the
    table in view rather than fall through as clean."""
    path = tmp_path / "approval-request-broken.md"
    path.write_bytes(b"\xff\xfe\x00\x00\xc3\x28")
    assert has_open_request(open_request_caveats(tmp_path, [])) is True


def test_has_open_request_is_false_for_unrelated_caveats():
    assert has_open_request([{"kind": "unverified_db_provenance"}]) is False
    assert has_open_request([]) is False


# --------------------------------------------------------------------------
# The two surfaces that make the caveat actionable rather than informational
# --------------------------------------------------------------------------


def test_terminal_pass_action_reaches_next_allowed_action():
    """A caveat alone is informational and a conductor routes past it, so the
    action field itself must change (issue #517)."""
    from seshat.agent_next import _next_allowed_action

    clean = {"outcome": "terminal_pass", "stage": None, "action_text": None}
    assert _next_allowed_action(clean).startswith("No pipeline action")

    with_request = dict(clean, action_text="Present the open approval request(s)")
    assert _next_allowed_action(with_request) == "Present the open approval request(s)"


def test_portfolio_rank_puts_a_request_bearing_table_ahead_of_a_clean_one():
    """Portfolio mode picks ONE focus; a request-bearing table must not be
    hidden behind a passing one -- while real pipeline work still outranks it."""
    from seshat.agent_next import _rank

    clean = {"outcome": "terminal_pass", "stage": None, "caveats": []}
    with_request = {
        "outcome": "terminal_pass",
        "stage": None,
        "caveats": [{"kind": OPEN_REQUEST_KIND, "detail": "x"}],
    }
    staged = {"outcome": "next_action", "stage": "gold_ready", "caveats": []}
    defect = {"outcome": "input_defect", "stage": None, "caveats": []}

    assert _rank(with_request) < _rank(clean)
    assert _rank(staged) < _rank(with_request)
    assert _rank(defect) < _rank(staged)
