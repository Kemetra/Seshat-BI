"""T015 -- the Studio event state machine, written before it exists.

The named cases: monotonic sequence, bounded retention, `Last-Event-ID` replay, expired
replay, duplicate input, late-after-terminal events, and interruption. [FR-015, FR-016]

Two constraints shape the design more than anything else:

* **FR-015 forbids exposing hidden reasoning content**, and `data-model.md` is blunter
  still: "Hidden reasoning and raw provider envelopes are never legal payload fields."
  Normalizing a provider event therefore means DROPPING its internal channel, not
  forwarding it, so a fixture carrying reasoning is fed in and asserted absent.
* **FR-035 forbids a database.** Retention is a bounded in-memory buffer, which is
  exactly why replay can EXPIRE -- and an expired replay must be a named refusal rather
  than a silently short stream, since a browser that silently missed events would render
  a state that never existed.

`data-model.md` also settles the subtlest case: a terminal event arriving after the turn
already ended is "retained in sequence with `ignored_for_state=true`" -- retained, not
dropped, and it does not reopen the turn.
"""

from __future__ import annotations

import pytest

# --------------------------------------------------------------------------- #
# Monotonic sequence                                                          #
# --------------------------------------------------------------------------- #


def test_sequences_start_at_one_and_increase_by_one() -> None:
    """The contract declares `sequence` an integer with `minimum: 1`."""
    from seshat.studio import events

    thread = events.ThreadEvents("t1")
    first = thread.append("thread_started", {})
    second = thread.append("turn_started", {}, turn_id="turn1")

    assert (first.sequence, second.sequence) == (1, 2)


def test_sequence_never_repeats_or_regresses() -> None:
    from seshat.studio import events

    thread = events.ThreadEvents("t1")
    sequences = [
        thread.append("agent_message", {"text": f"m{i}"}).sequence for i in range(20)
    ]

    assert sequences == sorted(sequences)
    assert len(set(sequences)) == len(sequences)


def test_two_threads_number_independently() -> None:
    """Sequences are per-thread: one thread's traffic cannot skew another's replay."""
    from seshat.studio import events

    first = events.ThreadEvents("t1")
    second = events.ThreadEvents("t2")
    first.append("agent_message", {"text": "a"})
    first.append("agent_message", {"text": "b"})

    assert second.append("agent_message", {"text": "c"}).sequence == 1


def test_an_event_is_immutable_once_recorded() -> None:
    """Rewriting history would let a browser and the server disagree about the past."""
    from seshat.studio import events

    thread = events.ThreadEvents("t1")
    event = thread.append("agent_message", {"text": "hello"})

    with pytest.raises(Exception):  # frozen dataclass
        event.sequence = 99  # type: ignore[misc]


# --------------------------------------------------------------------------- #
# FR-015 -- hidden reasoning and raw envelopes never survive normalization     #
# --------------------------------------------------------------------------- #


def test_hidden_reasoning_is_dropped_not_forwarded() -> None:
    """`data-model.md`: "Hidden reasoning ... never legal payload fields"."""
    from seshat.studio import events

    thread = events.ThreadEvents("t1")
    event = thread.append(
        "agent_message",
        {
            "text": "Here is the answer.",
            "reasoning": "internal chain of thought the user must not see",
            "thinking": "more of the same",
        },
    )

    assert "reasoning" not in event.payload
    assert "thinking" not in event.payload
    assert event.payload["text"] == "Here is the answer."


def test_a_raw_provider_envelope_is_dropped() -> None:
    from seshat.studio import events

    thread = events.ThreadEvents("t1")
    event = thread.append(
        "tool_started",
        {"name": "read_file", "raw": {"jsonrpc": "2.0", "id": 7}, "envelope": "..."},
    )

    assert "raw" not in event.payload
    assert "envelope" not in event.payload
    assert event.payload["name"] == "read_file"


def test_an_unknown_event_type_is_refused() -> None:
    """The contract's `type` is a closed enum; a producer must not widen it."""
    from seshat.studio import events

    thread = events.ThreadEvents("t1")

    with pytest.raises(ValueError, match="event type"):
        thread.append("reticulating_splines", {})


# --------------------------------------------------------------------------- #
# Bounded retention (FR-035: memory only, so it must have a ceiling)          #
# --------------------------------------------------------------------------- #


def test_retention_is_bounded() -> None:
    from seshat.studio import events

    thread = events.ThreadEvents("t1", retention=5)
    for index in range(12):
        thread.append("agent_message", {"text": str(index)})

    assert len(thread.retained()) == 5


def test_the_newest_events_are_the_ones_retained() -> None:
    """Dropping the newest would make the live stream useless."""
    from seshat.studio import events

    thread = events.ThreadEvents("t1", retention=3)
    for index in range(10):
        thread.append("agent_message", {"text": str(index)})

    assert [event.sequence for event in thread.retained()] == [8, 9, 10]


def test_sequence_keeps_counting_past_the_retention_ceiling() -> None:
    """Retention bounds MEMORY, not the counter: reused numbers would break replay."""
    from seshat.studio import events

    thread = events.ThreadEvents("t1", retention=2)
    for _ in range(9):
        thread.append("agent_message", {})

    assert thread.append("agent_message", {}).sequence == 10


# --------------------------------------------------------------------------- #
# Last-Event-ID replay, and its expiry                                        #
# --------------------------------------------------------------------------- #


def test_replay_returns_only_events_after_the_last_seen_id() -> None:
    from seshat.studio import events

    thread = events.ThreadEvents("t1", retention=10)
    for index in range(5):
        thread.append("agent_message", {"text": str(index)})

    assert [event.sequence for event in thread.replay_after(3)] == [4, 5]


def test_replay_from_zero_returns_everything_retained() -> None:
    """A fresh browser sends no `Last-Event-ID`, which the caller normalises to 0."""
    from seshat.studio import events

    thread = events.ThreadEvents("t1", retention=10)
    for index in range(3):
        thread.append("agent_message", {"text": str(index)})

    assert len(thread.replay_after(0)) == 3


def test_replay_of_the_latest_id_returns_nothing_rather_than_repeating() -> None:
    from seshat.studio import events

    thread = events.ThreadEvents("t1")
    last = thread.append("agent_message", {}).sequence

    assert thread.replay_after(last) == ()


def test_an_expired_replay_is_refused_not_silently_shortened() -> None:
    """The case a bounded buffer makes inevitable.

    If the browser asks to resume from a sequence already evicted, returning "everything
    I still have" would silently skip events and leave it rendering a state that never
    existed. The contract answers this with a 409 on the endpoint, so the store must
    raise something the route can turn into one.
    """
    from seshat.studio import events

    thread = events.ThreadEvents("t1", retention=3)
    for _ in range(10):
        thread.append("agent_message", {})

    with pytest.raises(events.ReplayExpired):
        thread.replay_after(2)


def test_a_replay_id_from_the_future_is_refused() -> None:
    """A sequence this thread never issued means the client is talking to the wrong
    thread or a restarted process -- worth refusing rather than answering emptily."""
    from seshat.studio import events

    thread = events.ThreadEvents("t1")
    thread.append("agent_message", {})

    with pytest.raises(events.ReplayExpired):
        thread.replay_after(999)


def test_the_contiguous_resume_boundary_is_served_not_refused() -> None:
    """The other side of expiry, and the easier one to break.

    A client that saw everything up to the eviction line can be continued exactly:
    `last_event_id == lowest_retained - 1` leaves NO gap. Refusing it would force a
    full reload on every ordinary reconnect, so this off-by-one is the difference
    between a working stream and a client that can never resume. Only the refusal side
    was covered above; this pins the boundary from inside.
    """
    from seshat.studio import events

    thread = events.ThreadEvents("t1", retention=3)
    for _ in range(10):
        thread.append("agent_message", {})

    lowest = thread.retained()[0].sequence

    assert [event.sequence for event in thread.replay_after(lowest - 1)] == [8, 9, 10]
    with pytest.raises(events.ReplayExpired):
        thread.replay_after(lowest - 2)


def test_a_fresh_connect_to_an_empty_thread_is_not_an_expiry() -> None:
    """No events yet is "you are up to date", not a gap.

    Refusing here would make a newly created thread unstreamable until something
    happened to it, so absent `Last-Event-ID` (normalised to 0) must be answerable.
    """
    from seshat.studio import events

    assert events.ThreadEvents("t1").replay_after(0) == ()


# --------------------------------------------------------------------------- #
# Turn lifecycle: duplicates, terminal states, late events, interruption       #
# --------------------------------------------------------------------------- #


def test_a_duplicate_turn_start_is_refused() -> None:
    """Two live turns in one thread would make "the current turn" ambiguous."""
    from seshat.studio import events

    thread = events.ThreadEvents("t1")
    thread.append("turn_started", {}, turn_id="turn1")

    with pytest.raises(ValueError, match="already active"):
        thread.append("turn_started", {}, turn_id="turn2")


def test_a_turn_may_start_after_the_previous_one_completed() -> None:
    from seshat.studio import events

    thread = events.ThreadEvents("t1")
    thread.append("turn_started", {}, turn_id="turn1")
    thread.append("turn_completed", {}, turn_id="turn1")

    assert thread.append("turn_started", {}, turn_id="turn2").turn_id == "turn2"


@pytest.mark.parametrize("terminal", ["turn_completed", "turn_failed"])
def test_an_event_after_a_terminal_one_is_retained_but_ignored(terminal: str) -> None:
    """`data-model.md`: retained in sequence with `ignored_for_state=true`.

    Retained, not dropped -- the browser should still see it happened -- and it does not
    reopen the turn.
    """
    from seshat.studio import events

    thread = events.ThreadEvents("t1")
    thread.append("turn_started", {}, turn_id="turn1")
    thread.append(terminal, {}, turn_id="turn1")

    late = thread.append("agent_message", {"text": "late"}, turn_id="turn1")

    assert late.ignored_for_state is True
    assert late in thread.retained()
    assert thread.active_turn_id is None


def test_an_event_during_a_live_turn_is_not_ignored() -> None:
    from seshat.studio import events

    thread = events.ThreadEvents("t1")
    thread.append("turn_started", {}, turn_id="turn1")

    assert (
        thread.append("agent_message", {}, turn_id="turn1").ignored_for_state is False
    )


def test_interruption_ends_the_turn_and_ignores_what_follows() -> None:
    from seshat.studio import events

    thread = events.ThreadEvents("t1")
    thread.append("turn_started", {}, turn_id="turn1")
    thread.interrupt("turn1")

    assert thread.active_turn_id is None
    assert thread.append("agent_message", {}, turn_id="turn1").ignored_for_state is True


def test_interrupting_an_inactive_turn_is_refused() -> None:
    from seshat.studio import events

    thread = events.ThreadEvents("t1")

    with pytest.raises(ValueError, match="no active turn"):
        thread.interrupt("turn1")


def test_interruption_is_recorded_as_an_event_not_just_a_flag() -> None:
    """The browser learns the turn ended from the STREAM, so it needs an event."""
    from seshat.studio import events

    thread = events.ThreadEvents("t1")
    thread.append("turn_started", {}, turn_id="turn1")
    thread.interrupt("turn1")

    assert thread.retained()[-1].type == "turn_failed"


# --------------------------------------------------------------------------- #
# Contract conformance of the serialized event                                #
# --------------------------------------------------------------------------- #


def test_a_serialized_event_validates_against_the_contract() -> None:
    import sys
    from pathlib import Path

    import yaml

    jsonschema = pytest.importorskip("jsonschema")
    from seshat.studio import events

    repo_root = Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(repo_root))
    document = yaml.safe_load(
        (
            repo_root / "specs/139-seshat-studio-foundation/contracts/studio-api.yaml"
        ).read_text(encoding="utf-8")
    )
    schema = {"$ref": "#/components/schemas/StudioEvent", **document}
    validator = jsonschema.validators.validator_for(document)(schema)

    thread = events.ThreadEvents("t1")
    thread.append("turn_started", {}, turn_id="turn1")
    payload = thread.append("agent_message", {"text": "hi"}, turn_id="turn1").as_dict()

    errors = [
        f"{list(e.absolute_path)}: {e.message}" for e in validator.iter_errors(payload)
    ]
    assert not errors, "StudioEvent violates the contract:\n  " + "\n  ".join(errors)


def test_the_event_type_enum_matches_the_contract_in_both_directions() -> None:
    """ "Gate must match reader": the enum is pinned symmetrically, on purpose.

    `test_a_serialized_event_validates_against_the_contract` only catches this code
    EMITTING a type the contract forbids. It cannot catch the opposite drift -- the
    contract gaining a type this module refuses -- which would make a legitimate
    provider event raise `ValueError` at record time and lose the event entirely. One
    set comparison closes both directions.
    """
    from pathlib import Path

    import yaml

    from seshat.studio import events

    document = yaml.safe_load(
        (
            Path(__file__).resolve().parents[2]
            / "specs/139-seshat-studio-foundation/contracts/studio-api.yaml"
        ).read_text(encoding="utf-8")
    )
    contract_types = set(
        document["components"]["schemas"]["StudioEvent"]["properties"]["type"]["enum"]
    )

    assert events.EVENT_TYPES == contract_types, (
        "the event type enum drifted from the contract: "
        f"only in code={sorted(events.EVENT_TYPES - contract_types)}, "
        f"only in contract={sorted(contract_types - events.EVENT_TYPES)}"
    )
