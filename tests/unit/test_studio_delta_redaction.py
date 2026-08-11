"""A credential split across streamed deltas must still be redacted.

Codex streams an agent message as many `item/agentMessage/delta` notifications.
Each was scrubbed independently, so a credential straddling a chunk boundary
evaded every rule: the fragment ending `Authorization: Bearer ` scrubbed to a bare
`<redacted>` marker with no value to catch, and the NEXT fragment -- carrying only
the token -- matched no rule and was delivered to the browser verbatim.

These tests assert the POSITIVE transformed form rather than the absence of the
secret. An absence assertion (`"sk-live-..." not in text`) passes just as happily
when the fix drops the held-back tail on the floor, which would silently truncate
the analyst's answer. So each test also reconstructs the full emitted text and
pins the surrounding non-secret content.
"""

from __future__ import annotations

from pathlib import Path

from seshat.studio.codex_protocol import (
    NormalizationContext,
    normalize_notification,
)

WORKSPACE = Path("/workspace")

_SECRET = "sk-live-SEKRET99"


def _delta(text: str, *, item_id: str = "item_msg") -> dict:
    return {
        "jsonrpc": "2.0",
        "method": "item/agentMessage/delta",
        "params": {"itemId": item_id, "delta": text},
    }


def _completed(item_id: str = "item_msg") -> dict:
    return {
        "jsonrpc": "2.0",
        "method": "item/completed",
        "params": {"item": {"id": item_id, "type": "agentMessage", "text": ""}},
    }


def _emitted(frames: list[dict], context: NormalizationContext) -> str:
    """The full text the browser would render, in order."""
    parts: list[str] = []
    for frame in frames:
        for event_type, payload in normalize_notification(frame, context=context):
            if event_type == "agent_message":
                parts.append(payload["text"])
    return "".join(parts)


def _context() -> NormalizationContext:
    return NormalizationContext(workspace_root=WORKSPACE)


def test_a_credential_split_across_two_deltas_is_redacted() -> None:
    """The reported defect: the token arrived in its own frame, unscrubbed."""
    frames = [
        _delta("Use header Authorization: Bearer "),
        _delta(f"{_SECRET} now"),
        _completed(),
    ]

    text = _emitted(frames, _context())

    assert _SECRET not in text, f"the split credential was delivered verbatim: {text!r}"
    assert "<redacted>" in text, (
        f"nothing was redacted -- the tail may have been dropped instead: {text!r}"
    )
    assert text.endswith(" now"), (
        f"the non-secret tail after the credential was lost: {text!r}"
    )
    assert text.startswith("Use header "), f"leading content was lost: {text!r}"


def test_ordinary_streamed_text_survives_intact() -> None:
    """The hold-back must not truncate or reorder a message with no credential."""
    frames = [_delta("Two tables "), _delta("are mapping ready."), _completed()]

    assert _emitted(frames, _context()) == "Two tables are mapping ready."


def test_interleaved_items_never_borrow_each_other_s_text() -> None:
    """Buffers are keyed per item: splicing item A onto item B is its own leak."""
    frames = [
        _delta("Alpha says Authorization: Bearer ", item_id="item_a"),
        _delta("Beta says nothing secret. ", item_id="item_b"),
        _delta(f"{_SECRET} end-a", item_id="item_a"),
        _completed("item_a"),
        _completed("item_b"),
    ]
    context = _context()

    per_item: dict[str, str] = {}
    for frame in frames:
        item_id = frame["params"].get("itemId") or frame["params"]["item"]["id"]
        for event_type, payload in normalize_notification(frame, context=context):
            if event_type == "agent_message":
                per_item[item_id] = per_item.get(item_id, "") + payload["text"]

    assert _SECRET not in "".join(per_item.values())
    assert "Beta says nothing secret." in per_item["item_b"]
    assert _SECRET not in per_item["item_b"], "item A's credential leaked into item B"
    assert "Alpha says" in per_item["item_a"]


def test_a_held_tail_is_flushed_when_the_turn_ends() -> None:
    """A tail held at turn end must still be emitted, not silently swallowed."""
    frames = [
        _delta("The final answer is complete"),
        {
            "jsonrpc": "2.0",
            "method": "turn/completed",
            "params": {"turn": {"status": "completed"}},
        },
    ]

    assert _emitted(frames, _context()) == "The final answer is complete"


def test_a_redaction_that_rewrites_already_sent_text_never_leaks() -> None:
    """The specific way a naive cumulative implementation leaks.

    `"Authorization: Bearer "` redacts to `"Authorization: <redacted> "` and is
    emitted. Once the token arrives, the WHOLE accumulation redacts to
    `"Authorization: <redacted>"` -- which is no longer an extension of what was
    already sent. Computing the "new" suffix by raw-input offset against that
    diverged string is exactly how the credential escapes.
    """
    frames = [
        _delta("Authorization: Bearer "),
        _delta(_SECRET),
        _delta(" -- use it"),
        _completed(),
    ]

    text = _emitted(frames, _context())

    assert _SECRET not in text, (
        f"the rewritten redaction leaked the credential: {text!r}"
    )
    assert "<redacted>" in text, f"nothing was redacted at all: {text!r}"
    assert "use it" in text, f"trailing non-secret content was lost: {text!r}"
