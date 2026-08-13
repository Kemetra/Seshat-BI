"""Unit tests for the Studio technical approval boundary (T024).

These sit on the risk the whole phase exists to manage: Studio may grant a
technical permission, and may NEVER grant a governance ruling. Every assertion
here states the positive transformed form -- `authority == NAMED_HUMAN` and
`allow_permitted is False` -- rather than merely noting that some control is
absent, because an absence-only assertion also passes when the feature is
deleted outright.
"""

from __future__ import annotations

import pytest

from seshat.studio.approvals import (
    NAMED_HUMAN,
    TECHNICAL,
    ApprovalEnvelope,
    normalize_approval,
)

TECHNICAL_EVENT = {
    "approval_id": "turn-1-approval-1",
    "required_authority": "technical",
    "action": "run_command",
    "target": "pytest -q",
    "reason": "Verify the mapping change",
    "scope": "read_only",
    "risk": "low",
}

BUSINESS_EVENT = {
    "approval_id": "turn-1-approval-2",
    "required_authority": "named_human",
    "action": "apply_change",
    "target": "mappings/example/source-map.yaml",
    "reason": "Add the missing grain declaration",
    "scope": "propose_changes",
    "risk": "high",
}


def test_a_technical_approval_with_clear_readiness_permits_allow():
    envelope = normalize_approval(TECHNICAL_EVENT, [])
    assert envelope.authority == TECHNICAL
    assert envelope.allow_permitted is True
    assert envelope.forbidden_reasons == ()


def test_the_five_display_fields_survive_normalization_unaltered():
    envelope = normalize_approval(TECHNICAL_EVENT, [])
    assert envelope.action == "run_command"
    assert envelope.target == "pytest -q"
    assert envelope.reason == "Verify the mapping change"
    assert envelope.scope == "read_only"
    assert envelope.risk == "low"


def test_a_named_human_approval_is_never_allowable():
    envelope = normalize_approval(BUSINESS_EVENT, [])
    assert envelope.authority == NAMED_HUMAN
    assert envelope.allow_permitted is False


def test_readiness_forbidden_scope_blocks_a_technical_allow():
    envelope = normalize_approval(
        TECHNICAL_EVENT, ["no silver before mapping is cleared"]
    )
    assert envelope.authority == TECHNICAL
    assert envelope.allow_permitted is False
    assert envelope.forbidden_reasons == ("no silver before mapping is cleared",)


def test_an_unknown_authority_is_treated_as_named_human():
    envelope = normalize_approval(
        {**TECHNICAL_EVENT, "required_authority": "wharrgarbl"}, []
    )
    assert envelope.authority == NAMED_HUMAN
    assert envelope.allow_permitted is False


def test_a_missing_authority_is_treated_as_named_human():
    event = {k: v for k, v in TECHNICAL_EVENT.items() if k != "required_authority"}
    assert normalize_approval(event, []).allow_permitted is False


def test_the_envelope_is_immutable():
    envelope = normalize_approval(TECHNICAL_EVENT, [])
    with pytest.raises(Exception):
        envelope.allow_permitted = True  # type: ignore[misc]


def test_a_missing_display_field_becomes_an_explicit_unknown_not_a_crash():
    envelope = normalize_approval(
        {"approval_id": "x", "required_authority": "technical"}, []
    )
    assert envelope.action == "unknown"
    assert envelope.risk == "unknown"
    assert isinstance(envelope, ApprovalEnvelope)


# -- the readiness lookup (Task 2) ------------------------------------------- #


def test_forbidden_scope_reads_the_readiness_document(tmp_path, monkeypatch):
    from seshat.studio import approvals

    def fake_document(repo_root, table):
        return {"forbidden_scope": ["no silver before mapping is cleared"]}

    monkeypatch.setattr(approvals, "build_table_next_document", fake_document)
    assert approvals.forbidden_scope_for(tmp_path, "sales") == (
        "no silver before mapping is cleared",
    )


def test_a_readiness_lookup_failure_refuses_rather_than_permitting(
    tmp_path, monkeypatch
):
    from seshat.studio import approvals

    def exploding_document(repo_root, table):
        raise RuntimeError("no such table")

    monkeypatch.setattr(approvals, "build_table_next_document", exploding_document)
    reasons = approvals.forbidden_scope_for(tmp_path, "sales")
    assert len(reasons) == 1
    assert "could not be read" in reasons[0]
    # The point: a failed lookup must BLOCK an allow, not silently clear the gate.
    assert normalize_approval(TECHNICAL_EVENT, reasons).allow_permitted is False


def test_no_table_refuses_rather_than_permitting(tmp_path):
    from seshat.studio import approvals

    reasons = approvals.forbidden_scope_for(tmp_path, None)
    assert reasons != ()
    assert normalize_approval(TECHNICAL_EVENT, reasons).allow_permitted is False


# -- the decide-once ledger (Task 3) ----------------------------------------- #


def test_an_allow_once_decision_is_recorded_once():
    from seshat.studio.approvals import PendingApprovals

    ledger = PendingApprovals()
    ledger.register(normalize_approval(TECHNICAL_EVENT, []))
    assert ledger.decide("turn-1-approval-1", allow=True) == "allowed"


def test_a_repeated_decision_is_refused():
    from seshat.studio.approvals import PendingApprovals, StaleApproval

    ledger = PendingApprovals()
    ledger.register(normalize_approval(TECHNICAL_EVENT, []))
    ledger.decide("turn-1-approval-1", allow=True)
    with pytest.raises(StaleApproval):
        ledger.decide("turn-1-approval-1", allow=True)


def test_an_unknown_approval_id_is_refused():
    from seshat.studio.approvals import PendingApprovals, StaleApproval

    ledger = PendingApprovals()
    with pytest.raises(StaleApproval):
        ledger.decide("never-registered", allow=True)


def test_a_deny_is_recorded_and_also_burns_the_id():
    from seshat.studio.approvals import PendingApprovals, StaleApproval

    ledger = PendingApprovals()
    ledger.register(normalize_approval(TECHNICAL_EVENT, []))
    assert ledger.decide("turn-1-approval-1", allow=False) == "denied"
    with pytest.raises(StaleApproval):
        ledger.decide("turn-1-approval-1", allow=False)


def test_a_decision_under_the_wrong_thread_is_refused():
    from seshat.studio.approvals import PendingApprovals, StaleApproval

    ledger = PendingApprovals()
    ledger.register(normalize_approval(TECHNICAL_EVENT, [], thread_id="thread-a"))
    with pytest.raises(StaleApproval):
        ledger.decide("turn-1-approval-1", allow=True, thread_id="thread-b")
    # Still live: a mismatched attempt must not consume the approval.
    assert (
        ledger.decide("turn-1-approval-1", allow=True, thread_id="thread-a")
        == "allowed"
    )


def test_abandoning_a_thread_drops_only_its_own_approvals():
    from seshat.studio.approvals import PendingApprovals, StaleApproval

    ledger = PendingApprovals()
    ledger.register(normalize_approval(TECHNICAL_EVENT, [], thread_id="thread-a"))
    ledger.register(
        normalize_approval(
            {**TECHNICAL_EVENT, "approval_id": "other"}, [], thread_id="thread-b"
        )
    )
    assert ledger.abandon_thread("thread-a") == 1
    with pytest.raises(StaleApproval):
        ledger.decide("turn-1-approval-1", allow=True, thread_id="thread-a")
    # thread-b's approval is untouched.
    assert ledger.decide("other", allow=True, thread_id="thread-b") == "allowed"


def test_the_live_ledger_stays_bounded():
    from seshat.studio import approvals

    ledger = approvals.PendingApprovals()
    for index in range(approvals._LIVE_RETENTION + 25):
        ledger.register(
            normalize_approval({**TECHNICAL_EVENT, "approval_id": f"a-{index}"}, [])
        )
    assert len(ledger._live) <= approvals._LIVE_RETENTION
    # The most recent survives; the oldest is what went.
    newest = f"a-{approvals._LIVE_RETENTION + 24}"
    assert ledger.envelope(newest) is not None
    assert ledger.envelope("a-0") is None


def test_the_decided_ledger_stays_bounded():
    from seshat.studio import approvals

    ledger = approvals.PendingApprovals()
    for index in range(approvals._DECIDED_RETENTION + 25):
        event = {**TECHNICAL_EVENT, "approval_id": f"a-{index}"}
        ledger.register(normalize_approval(event, []))
        ledger.decide(f"a-{index}", allow=False)
    assert len(ledger._decided) <= approvals._DECIDED_RETENTION


def test_a_never_allowable_envelope_cannot_be_allowed_through_the_ledger():
    from seshat.studio.approvals import PendingApprovals, StaleApproval

    ledger = PendingApprovals()
    ledger.register(normalize_approval(BUSINESS_EVENT, []))
    # The ledger is the second gate, not a bypass of the first.
    with pytest.raises(StaleApproval):
        ledger.decide("turn-1-approval-2", allow=True)
    # ...but denying a business item is fine: it records no governance ruling.
    assert ledger.decide("turn-1-approval-2", allow=False) == "denied"
