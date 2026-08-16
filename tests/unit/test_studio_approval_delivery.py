"""The approval round trip actually closes (T024, T026).

Phase 6 shipped a relay that ACCEPTED a decision and burned its id, but nothing sent
it to a provider: `AgentBridge` had `run_turn` and `describe` and no respond seam, so a
real Codex turn -- which sends `item/*/requestApproval` as a JSON-RPC server request
carrying an `id` and BLOCKS on the response -- would have waited forever. These tests
pin the delivery half, and they are written to fail if the reply is merely *recorded*
rather than *written to the provider*.

**Why every assertion here inspects a written frame.** A test that asserted only
`decide()` returned "allowed" would go green against the very build this file exists to
reject. The subject under test is the bytes the provider receives, so that is what each
case reads -- the same discipline as the repo's emitted-command tests, which must RUN
the command rather than assert its shape.

The frame shapes are taken from `tests/fixtures/codex_app_server/approvals.jsonl`,
which was captured from a real signed-in Codex app-server. That fixture is the
authority: an earlier session invented a protocol rule that fixtures and client both
shared, and the invention survived until an integration test read the real bytes.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from seshat.studio.approvals import (
    PendingApprovals,
    StaleApproval,
    normalize_approval,
)

FIXTURE = (
    Path(__file__).resolve().parents[1]
    / "fixtures"
    / "codex_app_server"
    / "approvals.jsonl"
)


def _fixture_requests() -> list[dict[str, Any]]:
    """The real `requestApproval` server requests, straight from the capture."""
    frames = [
        json.loads(line)
        for line in FIXTURE.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    return [f for f in frames if str(f.get("method", "")).endswith("requestApproval")]


class _Recorder:
    """A session that records frames instead of writing them to a child process."""

    def __init__(self) -> None:
        self.sent: list[dict[str, Any]] = []

    def send(self, frame: dict[str, Any]) -> None:
        self.sent.append(frame)


# --------------------------------------------------------------------------- #
# The fixture is the authority on the wire shape                              #
# --------------------------------------------------------------------------- #


def test_the_real_capture_sends_approvals_as_requests_carrying_an_id():
    """Guards the premise the whole seam rests on.

    If Codex sent approvals as notifications, no response would be owed and the seam
    would be unnecessary. Reading it from the committed capture keeps that premise
    falsifiable rather than remembered.
    """
    requests = _fixture_requests()
    assert requests, "the capture must contain at least one approval request"
    for frame in requests:
        assert "id" in frame, f"{frame['method']} must carry a JSON-RPC id"
        assert frame.get("jsonrpc") == "2.0"


# --------------------------------------------------------------------------- #
# The id survives normalization (T025)                                        #
# --------------------------------------------------------------------------- #


def test_the_jsonrpc_request_id_is_carried_on_the_envelope():
    """Without this the decision cannot be addressed back to the right request.

    The provider correlates by `id`, not by approval name, so an envelope that forgets
    it can be decided but never answered.
    """
    envelope = normalize_approval(
        {"approval_id": "a1", "required_authority": "technical"},
        [],
        thread_id="t1",
        request_id=20,
    )
    assert envelope.request_id == 20


def test_an_approval_with_no_request_id_is_still_normalizable():
    """The fake bridge raises approvals with no JSON-RPC layer beneath them.

    Phase 4's `FakeAgentBridge` streams `approval_required` without any provider
    request behind it, so `request_id` must be optional or the fake stops working.
    """
    envelope = normalize_approval(
        {"approval_id": "a1", "required_authority": "technical"}, []
    )
    assert envelope.request_id is None


# --------------------------------------------------------------------------- #
# The decision reaches the provider                                           #
# --------------------------------------------------------------------------- #


def test_an_allowed_decision_is_written_to_the_provider_keyed_to_its_request_id():
    """The core of the round trip: a reply the provider can correlate and unblock on."""
    from seshat.studio.approval_delivery import deliver_decision

    session = _Recorder()
    envelope = normalize_approval(
        {"approval_id": "a1", "required_authority": "technical"},
        [],
        thread_id="t1",
        request_id=20,
    )
    deliver_decision(session, envelope, allow=True)

    assert len(session.sent) == 1, "exactly one reply per decision"
    reply = session.sent[0]
    assert reply["jsonrpc"] == "2.0"
    assert reply["id"] == 20, "the reply must be keyed to the request it answers"
    assert reply["result"]["decision"] == "accept"
    assert "error" not in reply


def test_a_denied_decision_is_also_written_rather_than_dropped():
    """A deny that is never sent leaves the provider blocked exactly like an allow.

    Silence is not a denial on this protocol -- it is a hang.
    """
    from seshat.studio.approval_delivery import deliver_decision

    session = _Recorder()
    envelope = normalize_approval(
        {"approval_id": "a1", "required_authority": "technical"},
        [],
        thread_id="t1",
        request_id=21,
    )
    deliver_decision(session, envelope, allow=False)

    assert len(session.sent) == 1
    assert session.sent[0]["id"] == 21
    assert session.sent[0]["result"]["decision"] == "decline"


def test_the_reply_decision_values_match_the_generated_protocol_vocabulary():
    """`accept`/`decline` are the provider's words, not Studio's internal ones.

    Studio's own vocabulary is `allow_once`/`deny` at the HTTP edge. Sending those
    across the wire would be a plausible-looking frame the provider cannot read.
    """
    from seshat.studio.approval_delivery import APPROVED, DENIED

    assert APPROVED == "accept"
    assert DENIED == "decline"


def test_an_envelope_with_no_request_id_delivers_nothing_and_says_so():
    """A fake-bridge approval has nothing to answer, and inventing an id would be worse.

    Returns False rather than raising: the DECISION is still validly recorded, there is
    simply no provider waiting on it. A raise here would turn the fake bridge's
    perfectly legitimate approval into an error.
    """
    from seshat.studio.approval_delivery import deliver_decision

    session = _Recorder()
    envelope = normalize_approval(
        {"approval_id": "a1", "required_authority": "technical"}, []
    )
    assert deliver_decision(session, envelope, allow=True) is False
    assert session.sent == []


def test_delivery_reports_failure_rather_than_pretending_it_wrote():
    """A dead provider must not read as a delivered decision (degrade-without-report).

    The relay's caller decides what to tell the analyst; what this function must never
    do is swallow the failure and let a 204 claim the round trip closed.
    """
    from seshat.studio.approval_delivery import DeliveryFailed, deliver_decision

    class _Dead:
        def send(self, frame: dict[str, Any]) -> None:
            raise RuntimeError("session is not started")

    envelope = normalize_approval(
        {"approval_id": "a1", "required_authority": "technical"},
        [],
        thread_id="t1",
        request_id=20,
    )
    with pytest.raises(DeliveryFailed):
        deliver_decision(_Dead(), envelope, allow=True)


# --------------------------------------------------------------------------- #
# Delivery does not weaken the decide-once ledger                             #
# --------------------------------------------------------------------------- #


def test_a_second_decision_is_refused_before_any_second_frame_is_written():
    """Decide-once must hold at the WIRE, not merely in the ledger.

    If the burn happened after delivery, a replayed allow would write a second reply to
    a request the provider already considers answered.
    """
    from seshat.studio.approval_delivery import deliver_decision

    session = _Recorder()
    ledger = PendingApprovals()
    envelope = normalize_approval(
        {"approval_id": "a1", "required_authority": "technical"},
        [],
        thread_id="t1",
        request_id=20,
    )
    ledger.register(envelope)

    ledger.decide("a1", allow=True, thread_id="t1")
    deliver_decision(session, envelope, allow=True)

    with pytest.raises(StaleApproval):
        ledger.decide("a1", allow=True, thread_id="t1")
    assert len(session.sent) == 1, "the refused replay must not reach the provider"


def test_a_forbidden_scope_approval_is_never_delivered_as_approved():
    """Readiness forbidding the scope must stop the frame, not just the button.

    A UI that hides the allow control while the seam still writes `approved` would be a
    boundary in appearance only.
    """
    from seshat.studio.approval_delivery import DeliveryRefused, deliver_decision

    session = _Recorder()
    envelope = normalize_approval(
        {"approval_id": "a1", "required_authority": "technical"},
        ["gold.sales is not mapping_ready"],
        thread_id="t1",
        request_id=22,
    )
    assert envelope.allow_permitted is False

    with pytest.raises(DeliveryRefused):
        deliver_decision(session, envelope, allow=True)
    assert session.sent == [], "no frame may be written for an impermissible allow"


def test_a_named_human_approval_is_never_delivered_as_approved():
    """The authority split has to reach the wire too (FR-021/FR-022)."""
    from seshat.studio.approval_delivery import DeliveryRefused, deliver_decision

    session = _Recorder()
    envelope = normalize_approval(
        {"approval_id": "a1", "required_authority": "named_human"},
        [],
        thread_id="t1",
        request_id=22,
    )
    with pytest.raises(DeliveryRefused):
        deliver_decision(session, envelope, allow=True)
    assert session.sent == []


def test_a_named_human_approval_may_still_be_DENIED_to_unblock_the_provider():
    """Refusing to grant is not the same as refusing to answer.

    A named-human request Studio may not approve still leaves Codex blocked. Denying it
    is within Studio's authority and is the only thing that releases the turn.
    """
    from seshat.studio.approval_delivery import deliver_decision

    session = _Recorder()
    envelope = normalize_approval(
        {"approval_id": "a1", "required_authority": "named_human"},
        [],
        thread_id="t1",
        request_id=22,
    )
    assert deliver_decision(session, envelope, allow=False) is True
    assert session.sent[0]["result"]["decision"] == "decline"
