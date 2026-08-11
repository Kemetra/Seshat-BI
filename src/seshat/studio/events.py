"""Ordered, normalized, redacted Studio events held in memory (FR-015, FR-016, FR-035).

Four properties carry the weight here, and each exists because its absence produces a
specific lie:

* **Per-thread monotonic sequence.** The sequence is the `Last-Event-ID` a browser
  resumes from, so reusing or regressing a number would make replay return the wrong
  slice. Retention bounds MEMORY, never the counter.
* **Normalization drops, never forwards.** FR-015 forbids exposing hidden reasoning,
  and `data-model.md` is blunter: "Hidden reasoning and raw provider envelopes are
  never legal payload fields." So `_FORBIDDEN_PAYLOAD_KEYS` are stripped on the way
  IN -- redaction into the buffer rather than at serialization, because replay reads
  the buffer and a leak stored is a leak eventually served.
* **A refused replay, not a shortened one.** FR-035 forbids a database, so the buffer
  has a ceiling and a resume point can genuinely expire. Answering "everything I still
  have" would silently skip events and leave the browser rendering a state that never
  existed, so an un-servable resume point raises `ReplayExpired` for the route to turn
  into the contract's 409.
* **Late events are retained and flagged, not dropped.** An event arriving after its
  turn ended keeps its place in sequence with `ignored_for_state=True`. Dropping it
  would make a provider bug look like a clean turn; the flag keeps the anomaly
  auditable while refusing to let it reopen the turn.

This module deliberately imports no web framework. `app.py` imports `events`; never the
reverse. That keeps the deterministic views available when the `studio` extra is absent
and keeps the package-contract tests honest.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from seshat.studio.redaction import scrub_payload

#: The contract's closed `StudioEvent.type` enum. A producer must not widen it: the
#: browser switches on this value, so an unknown type would render as nothing at all.
EVENT_TYPES: frozenset[str] = frozenset(
    {
        "thread_started",
        "turn_started",
        "agent_message",
        "plan_updated",
        "tool_started",
        "tool_completed",
        "file_change_proposed",
        "approval_required",
        "turn_completed",
        "turn_failed",
        "connection_state",
    }
)

#: Types that end a turn. Both are terminal; `turn_failed` also carries interruption.
TERMINAL_TYPES: frozenset[str] = frozenset({"turn_completed", "turn_failed"})

#: Payload keys that must never survive normalization (FR-015). Hidden reasoning and
#: raw provider envelopes are dropped rather than redacted: there is no safe rendering
#: of them, so the honest transform is removal.
_FORBIDDEN_PAYLOAD_KEYS: frozenset[str] = frozenset(
    {
        "reasoning",
        "reasoning_content",
        "thinking",
        "thought",
        "chain_of_thought",
        "raw",
        "raw_event",
        "envelope",
        "provider_envelope",
    }
)

#: Default in-memory retention. Bounded by FR-035; large enough that an ordinary
#: reconnect replays cleanly rather than tripping `ReplayExpired`.
DEFAULT_RETENTION = 512


class ReplayExpired(Exception):
    """A `Last-Event-ID` this store can no longer serve contiguously.

    Raised for a resume point already evicted AND for one this thread never issued.
    Both mean the same thing to the browser -- the stream it holds cannot be continued
    without a gap -- and the route turns both into the contract's 409 so the client
    reloads instead of rendering a state that never existed.
    """


def normalize_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Strip forbidden keys, then redact what remains.

    Order matters: dropping first means the redactor never sees reasoning text at all,
    so it cannot partially redact it into something that still reads as thought.
    """
    kept = {
        key: value
        for key, value in payload.items()
        if key.lower() not in _FORBIDDEN_PAYLOAD_KEYS
    }
    scrubbed = scrub_payload(kept)
    return scrubbed if isinstance(scrubbed, dict) else {}


@dataclass(frozen=True, slots=True)
class StudioEvent:
    """One recorded event. Frozen: rewriting history would let the browser and the
    server disagree about the past, and `ignored_for_state` in particular must reflect
    the turn state AT RECORD TIME rather than being re-derived later."""

    thread_id: str
    sequence: int
    type: str
    occurred_at: str
    turn_id: str | None
    payload: dict[str, Any] = field(default_factory=dict)
    ignored_for_state: bool = False

    def as_dict(self) -> dict[str, Any]:
        """The contract's `StudioEvent` shape, field for field."""
        return {
            "thread_id": self.thread_id,
            "sequence": self.sequence,
            "type": self.type,
            "occurred_at": self.occurred_at,
            "turn_id": self.turn_id,
            "payload": dict(self.payload),
            "ignored_for_state": self.ignored_for_state,
        }


class ThreadEvents:
    """One thread's bounded event log and turn state.

    Not thread-safe by design: a single-user loopback tool serves one browser, and a
    lock here would imply a concurrency guarantee the rest of Studio does not make.
    """

    __slots__ = ("thread_id", "_retention", "_events", "_next_sequence", "_active_turn")

    def __init__(self, thread_id: str, *, retention: int = DEFAULT_RETENTION) -> None:
        if retention < 1:
            raise ValueError("retention must be at least 1 event")
        self.thread_id = thread_id
        self._retention = retention
        self._events: deque[StudioEvent] = deque(maxlen=retention)
        self._next_sequence = 1
        self._active_turn: str | None = None

    @property
    def active_turn_id(self) -> str | None:
        """The live turn, or `None`. Terminal events and interruption both clear it."""
        return self._active_turn

    def append(
        self,
        event_type: str,
        payload: dict[str, Any],
        *,
        turn_id: str | None = None,
    ) -> StudioEvent:
        """Normalize, sequence, and record one event.

        Refuses an unknown type and a second concurrent turn; everything else is
        recorded, including events arriving after their turn ended.
        """
        if event_type not in EVENT_TYPES:
            raise ValueError(
                f"unknown event type {event_type!r}; the contract's enum is closed"
            )
        if event_type == "turn_started" and self._active_turn is not None:
            raise ValueError(
                f"turn {self._active_turn!r} is already active; "
                "two live turns would make 'the current turn' ambiguous"
            )

        # Computed BEFORE the state transition below, so a terminal event is itself
        # counted (it is not ignored) while what follows it is.
        ignored = self._is_ignored(event_type, turn_id)
        event = StudioEvent(
            thread_id=self.thread_id,
            sequence=self._next_sequence,
            type=event_type,
            occurred_at=datetime.now(UTC).isoformat(),
            turn_id=turn_id,
            payload=normalize_payload(payload),
            ignored_for_state=ignored,
        )
        self._next_sequence += 1
        self._events.append(event)

        if not ignored:
            self._apply_transition(event_type, turn_id)
        return event

    def interrupt(self, turn_id: str) -> StudioEvent:
        """End a live turn and record it as a `turn_failed` event.

        Recorded as an EVENT rather than only a flag: the browser learns the turn ended
        from the stream, so a silent flag would leave it spinning forever.
        """
        if self._active_turn is None or self._active_turn != turn_id:
            raise ValueError(f"no active turn {turn_id!r} to interrupt")
        return self.append(
            "turn_failed", {"reason": "interrupted_by_user"}, turn_id=turn_id
        )

    def retained(self) -> tuple[StudioEvent, ...]:
        """Everything still in memory, oldest first."""
        return tuple(self._events)

    def replay_after(self, last_event_id: int) -> tuple[StudioEvent, ...]:
        """Events strictly after `last_event_id`, or `ReplayExpired`.

        Deciding WHETHER a resume point is servable is separated from slicing, because
        the decision carries every subtle boundary while the slice is one line. Reading
        them together made both harder to check.
        """
        self._refuse_unservable_resume(last_event_id)
        return tuple(event for event in self._events if event.sequence > last_event_id)

    def _refuse_unservable_resume(self, last_event_id: int) -> None:
        """Raise unless the retained window can continue the client's stream exactly.

        Two independent questions, asked in order: is the resume point inside the range
        this thread has ever issued, and is it contiguous with what is still retained?
        They fail for different reasons and are checked separately so neither hides the
        other.
        """
        if last_event_id < 0:
            raise ValueError("last_event_id cannot be negative")
        self._refuse_a_sequence_never_issued(last_event_id)
        self._refuse_an_evicted_resume(last_event_id)

    def _refuse_a_sequence_never_issued(self, last_event_id: int) -> None:
        """A resume point ahead of the latest event means the client is out of sync.

        A restarted process or the wrong thread. Worth refusing rather than answering
        emptily, because an empty answer reads as "you are up to date".
        """
        latest = self._next_sequence - 1
        if last_event_id > latest:
            raise ReplayExpired(
                f"sequence {last_event_id} is ahead of this thread's latest ({latest})"
            )

    def _refuse_an_evicted_resume(self, last_event_id: int) -> None:
        """A resume point below the retained window would leave a gap.

        `last_event_id == lowest_retained - 1` is the contiguous boundary and is VALID:
        the client saw everything up to the eviction line, so the retained window
        continues its stream exactly.
        """
        if not self._events:
            # Nothing retained: only "resume from the latest" is answerable, and it
            # answers empty. Anything earlier would be a gap.
            if last_event_id != self._next_sequence - 1:
                raise ReplayExpired("no events are retained to replay")
            return

        lowest_retained = self._events[0].sequence
        if last_event_id < lowest_retained - 1:
            raise ReplayExpired(
                f"sequence {last_event_id} was evicted; the oldest retained event is "
                f"{lowest_retained}, so replaying would skip events"
            )

    # -- turn state ------------------------------------------------------------ #

    def _is_ignored(self, event_type: str, turn_id: str | None) -> bool:
        """Whether this event must not affect turn state.

        Scoped to the turn, not global: an event citing a turn that has already ended
        is ignored, while a new `turn_started` after a completed one is honoured.
        """
        if event_type == "turn_started":
            return False
        if turn_id is None:
            return False
        return turn_id != self._active_turn

    def _apply_transition(self, event_type: str, turn_id: str | None) -> None:
        if event_type == "turn_started":
            self._active_turn = turn_id
        elif event_type in TERMINAL_TYPES and turn_id == self._active_turn:
            self._active_turn = None


class ThreadStore:
    """Every thread in this process. No database (FR-035)."""

    __slots__ = ("_threads", "_retention")

    def __init__(self, *, retention: int = DEFAULT_RETENTION) -> None:
        self._threads: dict[str, ThreadEvents] = {}
        self._retention = retention

    def thread(self, thread_id: str) -> ThreadEvents:
        """The named thread, created on first use."""
        existing = self._threads.get(thread_id)
        if existing is not None:
            return existing
        created = ThreadEvents(thread_id, retention=self._retention)
        self._threads[thread_id] = created
        return created

    def known_thread_ids(self) -> tuple[str, ...]:
        return tuple(self._threads)

    def has_thread(self, thread_id: str) -> bool:
        return thread_id in self._threads
