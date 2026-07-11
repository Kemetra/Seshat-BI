"""Scenario loading, run execution, and disclosure validation (spec 120, US7).

Loading is fail-closed: a malformed, vendor-naming, or non-synthetic scenario
never silently drops out -- it raises :class:`BenchmarkError` naming the
defect. Runs capture every repetition, surface observed variation, and
validate the FR-041 disclosure set; a run missing disclosure is ``incomplete``
and is never rendered as a comparable result.
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any

from ..artifact_identity import resolve_within
from .model import (
    BEHAVIORS,
    SCHEMA_VERSION,
    BenchmarkError,
    BenchmarkRun,
    Observation,
    RunConditions,
    Scenario,
)
from .reference import ScriptedParticipant

# Vendor neutrality (FR-042): scenario text may not name an agent vendor or
# model family; the boundary being tested is Seshat's, not any vendor's.
_VENDOR_TERMS = (
    "openai",
    "gpt",
    "chatgpt",
    "anthropic",
    "claude",
    "gemini",
    "copilot",
    "llama",
    "mistral",
    "grok",
)

_REQUIRED_SCENARIO_FIELDS = (
    "scenario_id",
    "title",
    "principle",
    "fixture",
    "prompt",
    "expected_behavior",
    "observable_evidence",
    "vendor_neutral",
)


def _scenario_error(scenario_id: object, message: str) -> BenchmarkError:
    return BenchmarkError(f"scenario {scenario_id!r}: {message}")


def _require_fields(item: dict[str, Any]) -> None:
    for field_name in _REQUIRED_SCENARIO_FIELDS:
        if field_name not in item:
            raise _scenario_error(
                item.get("scenario_id"), f"missing required field {field_name!r}"
            )


def _check_expected_behavior(item: dict[str, Any]) -> None:
    if item["expected_behavior"] not in BEHAVIORS:
        raise _scenario_error(
            item["scenario_id"],
            f"expected_behavior must be one of {', '.join(BEHAVIORS)}",
        )


def _check_vendor_neutrality(item: dict[str, Any]) -> None:
    scenario_id = item["scenario_id"]
    if item["vendor_neutral"] is not True:
        raise _scenario_error(scenario_id, "vendor_neutral must be true (FR-042)")
    searchable = " ".join(
        str(item[key]) for key in ("title", "principle", "prompt")
    ).lower()
    for term in _VENDOR_TERMS:
        if term in searchable:
            raise _scenario_error(
                scenario_id, f"scenario text names a vendor term ({term!r})"
            )


def _check_evidence(item: dict[str, Any]) -> list[Any]:
    evidence = item["observable_evidence"]
    if not isinstance(evidence, list) or not evidence:
        raise _scenario_error(
            item["scenario_id"], "observable_evidence must be non-empty"
        )
    return evidence


def _check_fixture(item: dict[str, Any], root: Path) -> str:
    scenario_id = item["scenario_id"]
    fixture = str(item["fixture"])
    try:
        fixture_path = resolve_within(root, fixture)
    except ValueError as exc:
        raise _scenario_error(scenario_id, "fixture escapes the workspace") from exc
    if not fixture_path.is_file():
        raise _scenario_error(scenario_id, f"fixture {fixture!r} is absent")
    return fixture


def _validate_scenario(item: dict[str, Any], root: Path) -> Scenario:
    _require_fields(item)
    _check_expected_behavior(item)
    _check_vendor_neutrality(item)
    evidence = _check_evidence(item)
    fixture = _check_fixture(item, root)
    return Scenario(
        scenario_id=str(item["scenario_id"]),
        title=str(item["title"]),
        principle=str(item["principle"]),
        fixture=fixture,
        prompt=str(item["prompt"]),
        expected_behavior=item["expected_behavior"],
        observable_evidence=tuple(str(entry) for entry in evidence),
        vendor_neutral=True,
    )


def _load_manifest_yaml(root: Path, manifest_path: Path | str) -> Any:
    import yaml  # lazy: keep module import stdlib-light (B1/B3)

    try:
        resolved = resolve_within(root, manifest_path)
        raw = resolved.read_text(encoding="utf-8-sig")
    except (ValueError, OSError) as exc:
        raise BenchmarkError(
            f"scenario manifest is unreadable: {manifest_path}"
        ) from exc
    try:
        return yaml.safe_load(raw)
    except yaml.YAMLError as exc:
        raise BenchmarkError(
            f"scenario manifest is not valid YAML: {manifest_path}"
        ) from exc


def _read_manifest_entries(
    root: Path, manifest_path: Path | str
) -> list[dict[str, Any]]:
    document = _load_manifest_yaml(root, manifest_path)
    entries = document.get("scenarios") if isinstance(document, dict) else None
    if not isinstance(entries, list):
        raise BenchmarkError(
            f"scenario manifest must hold a 'scenarios' list: {manifest_path}"
        )
    if not all(isinstance(item, dict) for item in entries):
        raise BenchmarkError("scenario entries must be mappings")
    return entries


def load_scenarios(
    repo_root: Path | str, *manifest_paths: Path | str
) -> list[Scenario]:
    """Load and validate scenario manifests; fail closed on any defect."""
    root = Path(repo_root).resolve()
    scenarios: list[Scenario] = []
    seen: set[str] = set()
    for manifest_path in manifest_paths:
        for item in _read_manifest_entries(root, manifest_path):
            scenario = _validate_scenario(item, root)
            if scenario.scenario_id in seen:
                raise _scenario_error(scenario.scenario_id, "duplicate scenario_id")
            seen.add(scenario.scenario_id)
            scenarios.append(scenario)
    return scenarios


def _variation_note(counts: Counter) -> str | None:
    if len(counts) <= 1:
        return None
    detail = ", ".join(
        f"{behavior} x{count}" for behavior, count in counts.most_common()
    )
    return f"observed variation across repetitions: {detail}"


def _evidence_for(responses: list[tuple[str, tuple]], observed: str) -> tuple:
    return next(
        (tuple(item) for behavior, item in responses if behavior == observed), ()
    )


def _observe(
    scenario: Scenario, participant: ScriptedParticipant, repetitions: int
) -> Observation:
    responses = [participant.respond(scenario) for _ in range(repetitions)]
    counts = Counter(behavior for behavior, _ in responses)
    observed, _ = counts.most_common(1)[0]
    return Observation(
        scenario_id=scenario.scenario_id,
        expected_behavior=scenario.expected_behavior,
        observed_behavior=observed,
        evidence=_evidence_for(responses, observed),
        variation_note=_variation_note(counts),
    )


def run_benchmark(
    scenarios: list[Scenario],
    participant: ScriptedParticipant,
    conditions: RunConditions,
) -> BenchmarkRun:
    if conditions.repetitions < 1:
        raise BenchmarkError("repetitions must be at least 1")
    if not scenarios:
        raise BenchmarkError("a run needs at least one scenario")
    observations = tuple(
        _observe(scenario, participant, conditions.repetitions)
        for scenario in scenarios
    )
    digest = hashlib.sha256(conditions.instructions.encode("utf-8")).hexdigest()
    identity = hashlib.sha256(
        json.dumps(
            [participant.participant.name, digest, [s.scenario_id for s in scenarios]],
            sort_keys=True,
        ).encode("utf-8")
    ).hexdigest()
    return BenchmarkRun(
        run_id=f"run-{identity[:16]}",
        participant=participant.participant,
        instructions_digest=digest,
        environment=dict(conditions.environment),
        repetitions=conditions.repetitions,
        started_at=conditions.started_at,
        completed_at=conditions.completed_at,
        observations=observations,
    )


def _kind_disclosure(participant: dict[str, Any]) -> list[str]:
    missing = []
    if participant.get("kind") not in ("scripted", "stochastic"):
        missing.append("participant.kind")
    if participant.get("kind") == "stochastic" and not participant.get("model"):
        missing.append("participant.model")
    return missing


def _participant_disclosure(document: dict[str, Any]) -> list[str]:
    participant = document.get("participant")
    if not isinstance(participant, dict):
        return ["participant.name", "participant.kind"]
    missing = [] if participant.get("name") else ["participant.name"]
    return missing + _kind_disclosure(participant)


def _repetitions_undisclosed(document: dict[str, Any]) -> bool:
    repetitions = document.get("repetitions")
    return not isinstance(repetitions, int) or repetitions < 1


def _observations_undisclosed(document: dict[str, Any]) -> bool:
    observations = document.get("observations")
    return not isinstance(observations, list) or not observations


def _run_condition_disclosure(document: dict[str, Any]) -> list[str]:
    missing: list[str] = []
    if not document.get("instructions_digest"):
        missing.append("instructions_digest")
    if not isinstance(document.get("environment"), dict):
        missing.append("environment")
    if _repetitions_undisclosed(document):
        missing.append("repetitions")
    if not document.get("started_at"):
        missing.append("started_at")
    if _observations_undisclosed(document):
        missing.append("observations")
    return missing


def missing_disclosure(document: dict[str, Any]) -> list[str]:
    """FR-041 disclosure set. A non-empty result means the run is
    ``incomplete`` and cannot be published as a comparable result."""
    missing: list[str] = []
    if document.get("schema_version") != SCHEMA_VERSION:
        missing.append("schema_version")
    missing.extend(_participant_disclosure(document))
    missing.extend(_run_condition_disclosure(document))
    return missing
