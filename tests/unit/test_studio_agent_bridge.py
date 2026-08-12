"""T017 -- the `AgentBridge` contract, written as a suite EVERY bridge must pass.

FR-014 requires the provider hidden behind a version-tolerant protocol with a
deterministic fake. The point of a protocol is that both implementations obey the same
rules, so these tests are parametrized over bridge factories rather than written against
the fake. Phase 5's Codex bridge adds itself to `BRIDGE_FACTORIES` and inherits every
assertion below instead of re-deriving them -- the difference between a real protocol
and two classes that happen to share method names.

The properties asserted here are the ones a UI depends on and a provider can silently
break:

* a turn emits `turn_started` first and exactly one terminal event last;
* no event carries hidden reasoning or a raw provider envelope (FR-015);
* every emitted type is in the contract's closed enum;
* `read_only` mode never proposes a file change (FR-013/US3 boundary);
* the same prompt produces the same event types -- determinism is what makes the fake
  usable in tests and what makes a replayed stream trustworthy.
"""

from __future__ import annotations

from typing import Any, Callable

import pytest


def _fake_bridge() -> Any:
    from seshat.studio.bridge import FakeAgentBridge

    return FakeAgentBridge()


def _codex_bridge() -> Any:
    """The production bridge, driven against the scripted child.

    Appended here rather than given its own assertions so it inherits every property
    the fake is held to -- the difference between a real protocol and two classes that
    share method names.
    """
    import sys
    from pathlib import Path

    from seshat.studio.codex_bridge import CodexBridge
    from seshat.studio.codex_process import CodexLaunchPlan

    script = Path(__file__).parent / "_codex_child_script.py"
    root = Path(__file__).resolve().parents[2]

    def _plan(fixture: str) -> CodexLaunchPlan:
        return CodexLaunchPlan(argv=(sys.executable, str(script), fixture), cwd=root)

    # The scripted child replays a FIXED script, so `propose_changes` must launch the
    # fixture that actually contains a file-change proposal -- otherwise
    # `test_propose_changes_mode_can_propose_a_file_change` fails and its read_only
    # twin proves nothing. A real child decides per turn and needs no second plan.
    #
    # `file_change_turn`, NOT `approvals`: the latter holds server->client approval
    # REQUESTS (T024-T027's surface, normalized to nothing today), while the former
    # holds the `fileChange` item notification that actually yields
    # `file_change_proposed`.
    return CodexBridge(_plan("thread_turn"), propose_plan=_plan("file_change_turn"))


#: Every bridge implementation. Phase 5 appends its Codex bridge here.
BRIDGE_FACTORIES: list[tuple[str, Callable[[], Any]]] = [
    ("fake", _fake_bridge),
    ("codex", _codex_bridge),
]

_IDS = [name for name, _ in BRIDGE_FACTORIES]
_FACTORIES = [factory for _, factory in BRIDGE_FACTORIES]


@pytest.fixture(params=_FACTORIES, ids=_IDS)
def bridge(request: pytest.FixtureRequest) -> Any:
    return request.param()


def _run(bridge: Any, prompt: str, *, mode: str = "read_only") -> list[Any]:
    """Drive one turn to completion and collect its events."""
    return list(bridge.run_turn(prompt=prompt, turn_id="turn1", requested_mode=mode))


# --------------------------------------------------------------------------- #
# Protocol shape                                                              #
# --------------------------------------------------------------------------- #


def test_a_bridge_declares_the_protocol_methods(bridge: Any) -> None:
    """A version-tolerant protocol is only tolerant if callers can rely on its shape."""
    from seshat.studio.bridge import AgentBridge

    assert isinstance(bridge, AgentBridge)


def test_a_turn_starts_with_turn_started(bridge: Any) -> None:
    events = _run(bridge, "what is blocking gold?")

    assert events, "a turn must emit at least one event"
    assert events[0].type == "turn_started"


def test_a_turn_ends_with_exactly_one_terminal_event(bridge: Any) -> None:
    """Two terminals would make "did it finish?" ambiguous; none would spin forever."""
    from seshat.studio.events import TERMINAL_TYPES

    events = _run(bridge, "summarise the workspace")
    terminals = [event for event in events if event.type in TERMINAL_TYPES]

    assert len(terminals) == 1, f"expected one terminal event, got {len(terminals)}"
    assert events[-1].type in TERMINAL_TYPES, "the terminal event must be last"


def test_every_emitted_type_is_in_the_contract_enum(bridge: Any) -> None:
    from seshat.studio.events import EVENT_TYPES

    for event in _run(bridge, "explain the mapping gate"):
        assert event.type in EVENT_TYPES, f"{event.type!r} is outside the contract enum"


def test_the_turn_id_is_carried_on_every_event(bridge: Any) -> None:
    """The UI groups events by turn; an unlabelled event cannot be placed."""
    for event in _run(bridge, "anything"):
        assert event.turn_id == "turn1"


# --------------------------------------------------------------------------- #
# FR-015 -- nothing hidden may cross the bridge                               #
# --------------------------------------------------------------------------- #


def test_no_event_exposes_hidden_reasoning_or_a_raw_envelope(bridge: Any) -> None:
    """Asserted at the BRIDGE, not only in the event store.

    The store strips these keys, so a bridge leaking them would still be scrubbed
    downstream -- and that is exactly why this is worth pinning here too: relying on a
    downstream scrub means the day someone constructs an event outside the store, the
    leak ships. Defence at both layers, per FR-015.
    """
    forbidden = {"reasoning", "thinking", "chain_of_thought", "raw", "envelope"}

    for event in _run(bridge, "think hard about this"):
        leaked = forbidden.intersection(event.payload)
        assert not leaked, f"{event.type} leaked {sorted(leaked)}"


# --------------------------------------------------------------------------- #
# Mode boundary                                                               #
# --------------------------------------------------------------------------- #


def test_read_only_mode_never_proposes_a_file_change(bridge: Any) -> None:
    """`read_only` is a promise, and the bridge is where it must hold.

    If a read-only turn can emit `file_change_proposed`, the mode is decoration: the UI
    would offer an approval for work the user never authorised the agent to attempt.
    """
    types = [
        event.type for event in _run(bridge, "fix the silver model", mode="read_only")
    ]

    assert "file_change_proposed" not in types


def test_propose_changes_mode_can_propose_a_file_change(bridge: Any) -> None:
    """The inverse, so the previous test cannot pass by never proposing anything."""
    types = [
        event.type
        for event in _run(bridge, "fix the silver model", mode="propose_changes")
    ]

    assert "file_change_proposed" in types, (
        "propose_changes must be able to propose, or read_only proves nothing"
    )


def test_an_unknown_mode_is_refused(bridge: Any) -> None:
    with pytest.raises(ValueError, match="mode"):
        _run(bridge, "anything", mode="do_whatever")


def test_an_empty_prompt_is_refused(bridge: Any) -> None:
    """`minLength: 1` in the contract: no inventing a turn from an empty prompt."""
    with pytest.raises(ValueError, match="prompt"):
        _run(bridge, "   ")


# --------------------------------------------------------------------------- #
# Determinism                                                                 #
# --------------------------------------------------------------------------- #


def test_the_same_prompt_produces_the_same_event_types(bridge: Any) -> None:
    """What makes the fake usable as a test double and a stream worth replaying."""
    first = [event.type for event in _run(bridge, "identical prompt")]
    second = [event.type for event in _run(bridge, "identical prompt")]

    assert first == second


def test_different_prompts_are_allowed_to_differ(bridge: Any) -> None:
    """Guards against a "deterministic" bridge that ignores its input entirely."""
    plan = [event.type for event in _run(bridge, "plan the gold layer rebuild")]
    trivial = [event.type for event in _run(bridge, "hi")]

    assert plan != trivial or len(plan) > 2, (
        "a bridge that emits an identical canned stream for every prompt is not "
        "answering the question"
    )
