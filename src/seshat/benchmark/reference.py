"""The deterministic scripted reference participant (spec 120, US7).

The reference participant answers every scenario from the scenario's own
declared expected behavior and observable evidence -- a script, not a model.
It exists so every scenario is independently reproducible (SC-008) and so
the harness itself is testable: custom scripts can seed mismatches and
over-refusals without any stochastic system.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .model import OBSERVED_BEHAVIORS, BenchmarkError, Participant, Scenario

REFERENCE_PARTICIPANT = Participant(name="seshat-reference", kind="scripted")


@dataclass(frozen=True)
class ScriptedParticipant:
    """Deterministic participant: scenario_id -> (behavior, evidence).
    Unscripted scenarios fall back to the scenario's declared expectation."""

    participant: Participant = REFERENCE_PARTICIPANT
    script: dict[str, tuple[str, tuple[str, ...]]] = field(default_factory=dict)

    def respond(self, scenario: Scenario) -> tuple[str, tuple[str, ...]]:
        behavior, evidence = self.script.get(
            scenario.scenario_id,
            (scenario.expected_behavior, scenario.observable_evidence),
        )
        if behavior not in OBSERVED_BEHAVIORS:
            raise BenchmarkError(
                f"scripted behavior {behavior!r} is not an observable category"
            )
        return behavior, tuple(evidence)


def reference_participant() -> ScriptedParticipant:
    """The canonical reference participant: demonstrates the declared
    boundary for every scenario, deterministically."""
    return ScriptedParticipant()
