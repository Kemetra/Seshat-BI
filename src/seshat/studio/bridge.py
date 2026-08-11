"""The provider-neutral `AgentBridge` and its deterministic fake (FR-014).

FR-014 requires the Codex integration hidden behind a version-tolerant protocol with a
deterministic fake for tests. Two decisions in here carry most of that weight:

**This fake declines to propose under `read_only`, but that is cooperation, not
enforcement.** A `Protocol` cannot constrain what a generator yields, so a bridge is
free to ignore the mode -- a bug, a provider quirk, or a prompt injection. The BINDING
refusal therefore lives in `agent_routes._record_turn`, which every bridge's output
passes through: write intent during a `read_only` turn raises `ReadOnlyViolation` and
never reaches the buffer.

An earlier revision of this docstring claimed the boundary was "enforced at the bridge",
which was false in the way that matters: a three-line rogue bridge got
`file_change_proposed` recorded under `read_only`, and Phase 5's provider would have
inherited no protection at all.

**Nothing hidden is constructed in the first place.** The event store strips reasoning
and raw envelopes, so a leaky bridge would still be scrubbed. That is precisely why the
fake never builds such a payload: relying on a downstream scrub means the day an event
is constructed outside the store, the leak ships.

`run_turn` yields already-normalized `StudioEvent`-shaped records, so a caller can
record them without knowing which provider produced them. It is a generator: a real
provider streams, and a bridge that had to complete before returning could not be
rendered incrementally.
"""

from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime
from typing import Any, Protocol, runtime_checkable

from seshat.studio.events import EVENT_TYPES, StudioEvent, normalize_payload

#: The contract's `StartTurnRequest.requested_mode` enum.
TURN_MODES: frozenset[str] = frozenset({"read_only", "propose_changes"})

#: Prompt ceiling from the contract (`maxLength: 20000`). Enforced here as well as at
#: the route so a bridge driven from a test or a future caller cannot exceed it.
MAX_PROMPT_LENGTH = 20_000


@runtime_checkable
class AgentBridge(Protocol):
    """What Studio requires of any agent provider.

    Deliberately small. Every method a bridge must implement is a method Studio has a
    reason to call; anything provider-specific stays behind the implementation, which is
    what makes the protocol version-tolerant.
    """

    def run_turn(
        self, *, prompt: str, turn_id: str, requested_mode: str
    ) -> Iterator[StudioEvent]:
        """Yield normalized events for one turn, ending with exactly one terminal."""
        ...  # pragma: no cover - protocol declaration

    def describe(self) -> dict[str, Any]:
        """Identify the bridge for the agent-health view, without provider internals."""
        ...  # pragma: no cover - protocol declaration


def validate_turn_request(prompt: str, requested_mode: str) -> str:
    """Shared validation for every bridge. Returns the cleaned prompt.

    Lives at module level rather than in a base class so an implementation that cannot
    inherit (a thin wrapper over a provider SDK, say) still validates identically.
    """
    if requested_mode not in TURN_MODES:
        raise ValueError(
            f"unknown requested_mode {requested_mode!r}; expected one of "
            f"{sorted(TURN_MODES)}"
        )
    cleaned = prompt.strip()
    if not cleaned:
        raise ValueError("prompt must not be empty")
    if len(cleaned) > MAX_PROMPT_LENGTH:
        raise ValueError(f"prompt exceeds {MAX_PROMPT_LENGTH} characters")
    return cleaned


def _event(
    event_type: str, payload: dict[str, Any], turn_id: str, sequence: int
) -> StudioEvent:
    """Build one normalized event.

    `sequence` here is bridge-local and provisional: the authoritative per-thread
    sequence is assigned by `ThreadEvents.append`. Numbering from 1 anyway keeps a
    bridge's output independently inspectable in tests.
    """
    if event_type not in EVENT_TYPES:
        raise ValueError(f"bridge emitted an unknown event type {event_type!r}")
    return StudioEvent(
        thread_id="",
        sequence=sequence,
        type=event_type,
        occurred_at=datetime.now(UTC).isoformat(),
        turn_id=turn_id,
        payload=normalize_payload(payload),
        ignored_for_state=False,
    )


#: Words that make a prompt "change-shaped". Used ONLY by the fake, to decide whether a
#: `propose_changes` turn has anything to propose -- a real bridge asks the provider.
_CHANGE_INTENT_WORDS = frozenset(
    {"fix", "add", "write", "change", "update", "rebuild", "create", "remove"}
)

#: Prompts short enough to be conversational get a shorter canned stream, so the fake
#: does not emit an identical script regardless of input.
_TRIVIAL_PROMPT_LENGTH = 12


class FakeAgentBridge:
    """A deterministic bridge for tests, demos, and offline development.

    Deterministic means the same prompt yields the same event TYPES every time -- which
    is what lets a test assert on a stream and what makes an offline demo reproducible.
    Timestamps still advance, because they are wall-clock facts rather than script.
    """

    def describe(self) -> dict[str, Any]:
        return {
            "bridge": "fake",
            "provider": "none",
            "deterministic": True,
        }

    def run_turn(
        self, *, prompt: str, turn_id: str, requested_mode: str
    ) -> Iterator[StudioEvent]:
        cleaned = validate_turn_request(prompt, requested_mode)
        sequence = 0

        def emit(event_type: str, payload: dict[str, Any]) -> StudioEvent:
            nonlocal sequence
            sequence += 1
            return _event(event_type, payload, turn_id, sequence)

        yield emit("turn_started", {"prompt_echo": cleaned[:200]})

        if len(cleaned) <= _TRIVIAL_PROMPT_LENGTH:
            # A short conversational prompt gets an answer, not a plan and tools.
            yield emit("agent_message", {"text": self._answer_for(cleaned)})
            yield emit("turn_completed", {"outcome": "answered"})
            return

        yield emit(
            "plan_updated",
            {
                "steps": [
                    {"label": "Read the committed readiness spine", "state": "running"},
                    {
                        "label": "Summarise what the evidence supports",
                        "state": "pending",
                    },
                ]
            },
        )
        yield emit(
            "tool_started",
            {"name": "read_workspace", "public_label": "Reading the workspace"},
        )
        yield emit(
            "tool_completed",
            {
                "name": "read_workspace",
                "public_label": "Read the workspace",
                "outcome": "ok",
            },
        )
        yield emit("agent_message", {"text": self._answer_for(cleaned)})

        if requested_mode == "propose_changes" and self._looks_like_a_change(cleaned):
            yield emit(
                "file_change_proposed",
                {
                    "path": "mappings/example/source-map.yaml",
                    "summary": "Add the missing grain declaration",
                    "diff_available": True,
                },
            )
            yield emit(
                "approval_required",
                {
                    "approval_id": f"{turn_id}-approval-1",
                    "question": "Apply the proposed mapping change?",
                    "required_authority": "named_human",
                },
            )

        yield emit("turn_completed", {"outcome": "answered"})

    # -- deterministic content -------------------------------------------------- #

    @staticmethod
    def _looks_like_a_change(prompt: str) -> bool:
        words = {word.strip(".,!?").lower() for word in prompt.split()}
        return bool(words & _CHANGE_INTENT_WORDS)

    @staticmethod
    def _answer_for(prompt: str) -> str:
        """A canned answer that names the prompt, so the stream is visibly a response.

        Never claims a readiness fact: this bridge has no access to the workspace, and a
        fake that asserted "gold is ready" would put a fabricated governance claim on
        screen during every demo.
        """
        return (
            f"This is the deterministic Studio bridge. It received: {prompt[:160]}. "
            "It reports no readiness facts of its own -- the deterministic views are "
            "the authority for those."
        )
