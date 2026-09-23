"""``doctor --format json`` keeps the Principle-I marker (audit finding F148).

The text digest always carries the "`check` gate exit code remains the authority"
pointer and the next allowed action. The machine surface must carry the same
boundary, or a clean ``finding_count: 0`` reads as a gate pass.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from seshat.doctor import _GATE_POINTER, format_digest, run_doctor

pytestmark = pytest.mark.unit


def test_doctor_json_marks_itself_advisory_and_names_the_gate(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    code = run_doctor(tmp_path, strict=False, prog="retail", output_format="json")
    parsed = json.loads(capsys.readouterr().out)

    assert code == 0
    assert parsed["advisory"] is True
    assert parsed["gate_authority"] == "retail check"
    assert isinstance(parsed["next_allowed_action"], str)
    assert parsed["next_allowed_action"]


def test_format_digest_pointer_is_built_from_the_single_constant() -> None:
    from seshat.core import Finding, Severity

    finding = Finding("A1", Severity.WARNING, "route missing", "docs/x.md")
    text = format_digest([finding], "retail")

    assert text.endswith(_GATE_POINTER.format(prog="retail"))
