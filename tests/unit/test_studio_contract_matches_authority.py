"""The Studio API contract must not drift from the readiness authority.

Spec 139's `studio-api.yaml` declares closed enums for readiness status and stage.
FR-007 forbids Studio from reimplementing readiness derivation and FR-008 requires
the categorical status to be PRESERVED, so those enums are not free choices --
they are copies of a vocabulary owned elsewhere:

* `templates/readiness-status.yaml` -- the documented four statuses,
* `schemas/agent-status.schema.json` -- the machine-checked status enum,
* `seshat.status_surface._STAGE_ORDER` -- the seven stage identifiers.

The contract shipped with `ready_for_review` in place of `warning`, and with stage
identifiers stripped of their `_ready` suffix. Neither value exists anywhere in the
shipped repository, so a truthful projection could not have validated against its own
contract: the closed enum had no slot for a `warning` stage, and every stage id would
have needed rewriting in transit.

These tests pin both directions so the drift cannot silently return.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

_REPO_ROOT = Path(__file__).resolve().parents[2]
_CONTRACT = _REPO_ROOT / "specs/139-seshat-studio-foundation/contracts/studio-api.yaml"
_AGENT_STATUS_SCHEMA = _REPO_ROOT / "schemas/agent-status.schema.json"


def _contract_schemas() -> dict:
    return yaml.safe_load(_CONTRACT.read_text(encoding="utf-8"))["components"][
        "schemas"
    ]


def _authority_status_enum() -> list[str]:
    """The status vocabulary the agent-status schema already enforces."""
    schema = json.loads(_AGENT_STATUS_SCHEMA.read_text(encoding="utf-8"))
    stage = schema["$defs"]["stageStatus"]
    return list(stage["properties"]["status"]["enum"])


def test_the_studio_status_enum_equals_the_agent_status_schema() -> None:
    studio = _contract_schemas()["StageState"]["properties"]["status"]["enum"]

    assert studio == _authority_status_enum(), (
        "StageState.status drifted from schemas/agent-status.schema.json; FR-008 "
        "requires the categorical status to be projected verbatim"
    )


def test_the_studio_status_enum_has_no_invented_value() -> None:
    """`ready_for_review` was the shipped defect: it exists in no authority."""
    studio = set(_contract_schemas()["StageState"]["properties"]["status"]["enum"])

    assert "ready_for_review" not in studio
    assert "warning" in studio, (
        "`warning` (advanced-with-a-recorded-issue) is a canonical status and must "
        "have a slot, or a truthful projection cannot validate"
    )


def test_the_studio_stage_enum_equals_status_surface_stage_order() -> None:
    from seshat.status_surface import _STAGE_ORDER

    studio = _contract_schemas()["ReadinessStage"]["enum"]

    assert studio == list(_STAGE_ORDER), (
        "ReadinessStage drifted from seshat.status_surface._STAGE_ORDER; Studio "
        "would have to rewrite stage identifiers in transit"
    )


def test_every_documented_status_appears_in_the_template() -> None:
    """The template is the human-facing authority; the enums must agree with it."""
    template = (_REPO_ROOT / "templates/readiness-status.yaml").read_text(
        encoding="utf-8"
    )

    for status in _authority_status_enum():
        assert status in template, (
            f"{status!r} is enforced by the schema but absent from "
            "templates/readiness-status.yaml"
        )


def test_current_stage_is_nullable() -> None:
    """Upstream sets `current_stage` to None when the source omits it.

    `seshat.status_surface._project_table` documents that it is "never fabricated",
    so a non-nullable contract field would force Studio to invent a stage or drop
    the table -- and FR-010 requires the gap to be reported instead.
    """
    current_stage = _contract_schemas()["TableJourney"]["properties"]["current_stage"]

    assert "oneOf" in current_stage, "current_stage must admit null"
    assert any(option.get("type") == "null" for option in current_stage["oneOf"]), (
        "current_stage must admit null"
    )


@pytest.mark.parametrize("bound", ["minItems", "maxItems"])
def test_the_stage_array_is_fixed_at_seven(bound: str) -> None:
    """Fixing the length is what makes a missing stage VISIBLE rather than absent.

    The upstream projection omits a stage block it cannot read. A variable-length
    array would let that omission pass as a valid short list; at exactly seven,
    Studio must fill the gap and raise an InputDefect (FR-010).
    """
    stages = _contract_schemas()["TableJourney"]["properties"]["stages"]

    assert stages[bound] == 7
