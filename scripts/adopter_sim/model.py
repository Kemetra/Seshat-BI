"""Frozen value types and the categorical sets Adopter Sim evaluates against."""

from __future__ import annotations

from dataclasses import dataclass

# The shipped categorical set, verbatim. Adding to this is a spec change.
EXPECTED_BEHAVIORS = frozenset(
    {"proceed", "refuse", "block_for_evidence", "request_human_decision"}
)

# Outcomes the harness records for a step that was not evaluated.
NOT_EVALUABLE = "not_evaluable"
NOT_RUN = "not_run"


class AdopterSimError(Exception):
    """Any harness-level failure. Never used for a client finding."""


@dataclass(frozen=True)
class JourneyStep:
    number: int
    title: str
    prompt: str | None
    command: tuple[str, ...] | None
    expected_behavior: str | None
    depends_on: tuple[int, ...]

    @property
    def agent_driven(self) -> bool:
        return self.prompt is not None


@dataclass(frozen=True)
class Journey:
    name: str
    steps: tuple[JourneyStep, ...]

    def step(self, number: int) -> JourneyStep:
        for candidate in self.steps:
            if candidate.number == number:
                return candidate
        raise AdopterSimError(f"no such step: {number}")

    def dependents_of(self, number: int) -> tuple[int, ...]:
        """Every step whose depends_on chain reaches `number`, transitively."""
        reached: set[int] = set()
        frontier = {number}
        while frontier:
            nxt: set[int] = set()
            for candidate in self.steps:
                if candidate.number in reached or candidate.number == number:
                    continue
                if frontier & set(candidate.depends_on):
                    reached.add(candidate.number)
                    nxt.add(candidate.number)
            frontier = nxt
        return tuple(sorted(reached))
