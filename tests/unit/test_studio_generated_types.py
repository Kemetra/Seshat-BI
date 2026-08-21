"""The generated browser types must not drift from the contract (T012, FR-034).

`studio-ui/src/api/types.ts` is generated from `studio-api.yaml`. A hand-edited or
stale copy would let the browser hold a different idea of a payload than the server
serves -- the same drift class that produced this feature's earlier contract defects,
one layer further out.

Regenerating and comparing makes that mechanical: an unsynchronised edit fails here
rather than surfacing as a runtime shape mismatch a user discovers.
"""

from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
_GENERATED = _REPO_ROOT / "studio-ui/src/api/types.ts"

sys.path.insert(0, str(_REPO_ROOT / "scripts"))


def _render() -> str:
    from generate_studio_types import render_types

    return render_types()


def test_the_generated_types_are_current() -> None:
    """FAILS if someone edits the contract without regenerating, or edits the .ts."""
    assert _GENERATED.exists(), "run `python scripts/generate_studio_types.py`"

    assert _GENERATED.read_text(encoding="utf-8") == _render(), (
        "studio-ui/src/api/types.ts is stale; regenerate it with "
        "`python scripts/generate_studio_types.py`"
    )


def test_the_generated_types_declare_the_canonical_statuses() -> None:
    """The corrected vocabulary must reach the browser, not the invented one."""
    generated = _GENERATED.read_text(encoding="utf-8")

    for status in ("not_started", "blocked", "warning", "pass"):
        assert f'"{status}"' in generated

    assert "ready_for_review" not in generated, (
        "the invented status reached the browser types"
    )


def test_the_generated_types_keep_the_ready_suffix() -> None:
    """Stage identifiers must match `status_surface._STAGE_ORDER` exactly."""
    from seshat.status_surface import _STAGE_ORDER

    generated = _GENERATED.read_text(encoding="utf-8")

    for stage in _STAGE_ORDER:
        assert f'"{stage}"' in generated


def test_the_generated_file_is_marked_as_generated() -> None:
    """A reader must not mistake it for a hand-maintained module."""
    head = _GENERATED.read_text(encoding="utf-8")[:400]

    assert "GENERATED FILE" in head
    assert "generate_studio_types.py" in head


def test_business_decision_recording_is_typed_as_a_runtime_boolean() -> None:
    """Spec 140 made recording real, so the type must let the browser branch on it.

    Under Foundation the contract pinned `const: false` and the generated type was the
    literal `false` -- correct then, because recording was ABSENT rather than merely
    disabled. Spec 140 (ratified 2026-08-21, anticipated by FR-022 as "the next
    governed-workbench spec") ships `POST /decisions/record`, and the flag is derived
    from that route being reachable. A literal `false` in the type would now be a lie
    the compiler enforces, and would stop the UI from ever showing the control.
    """
    generated = _GENERATED.read_text(encoding="utf-8")

    assert "business_decision_recording: boolean;" in generated
    assert "business_decision_recording: false;" not in generated
