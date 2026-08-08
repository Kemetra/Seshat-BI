"""The spec `**Status**:` vocabulary (ADR 0019) stays closed and evidence-backed.

`specs/` held 127 directories whose Status lines tracked reality in neither
direction -- `131-portfolio-watch` read "Ratified" while shipping code, and
`104-rename-impact-refactor-guard` read "Draft" while its rule module was already
on `main`. Nothing read the directory at all, so nothing caught it.

These tests hold three things together: the vocabulary the ADR declares, the values
the spec template offers a new author, and the migrated specs' actual Status lines.
Enforcement of the `implemented` claims themselves is rule `SC1` over
`docs/quality/status-claims.yaml`; these tests guard what SC1 cannot see.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

import pytest

from seshat.spec_status_policy import VOCABULARY

REPO = Path(__file__).resolve().parents[2]
ADR = REPO / "docs/decisions/0019-spec-status-closed-vocabulary.md"
TEMPLATE = REPO / ".specify/templates/spec-template.md"
CLAIMS = REPO / "docs/quality/status-claims.yaml"

# VOCABULARY is imported, never redeclared (spec 151 FR-002). Before spec 151
# this module declared its own tuple AND read the template to learn the policy
# it then checked -- the artifact under validation was also the source of the
# expectation. The authority is now `seshat.spec_status_policy`.

#: `**Status**: implemented -- artifact `path``
_IMPLEMENTED = re.compile(
    r"^\*\*Status\*\*:\s*implemented\s+--\s+artifact\s+`([^`]+)`\s*$"
)


def _tracked_files() -> set[str]:
    out = subprocess.run(
        ["git", "ls-files"], cwd=REPO, capture_output=True, text=True, check=True
    ).stdout
    return set(out.splitlines())


def _status_line(spec: Path) -> str:
    for line in spec.read_text(encoding="utf-8").splitlines():
        if line.startswith("**Status**:"):
            return line
    return ""


def _specs_claiming_implemented() -> list[Path]:
    return [
        spec
        for spec in sorted((REPO / "specs").glob("*/spec.md"))
        if _IMPLEMENTED.match(_status_line(spec))
    ]


@pytest.mark.unit
def test_the_adr_declares_exactly_the_four_values() -> None:
    text = ADR.read_text(encoding="utf-8")
    assert "draft | ratified | implemented | superseded" in text
    for value in VOCABULARY:
        assert f"`{value}`" in text, f"ADR 0019 does not describe {value!r}"


@pytest.mark.unit
def test_the_upstream_template_carries_no_seshat_policy() -> None:
    """Spec Kit owns Spec Kit (spec 151 FR-013).

    This assertion is the INVERSE of the one it replaces. Before spec 151 this
    test asserted the template CONTAINED the vocabulary block -- which is what
    made an upstream-managed file the home of a Seshat governance decision, and
    what an ordinary `specify` upgrade silently reverted. The policy now lives
    in `seshat.spec_status_policy`; the template must be clean.
    """
    text = TEMPLATE.read_text(encoding="utf-8")
    assert "draft | ratified | implemented | superseded" not in text, (
        "the Seshat vocabulary block is back in the upstream template; "
        "the policy belongs in seshat.spec_status_policy (spec 151)"
    )
    assert "ADR 0019" not in text, "Seshat governance content is back in the template"


@pytest.mark.unit
def test_a_scaffolded_spec_normalizes_into_the_vocabulary() -> None:
    """The seeded upstream value is normalized, not excused (FR-025).

    Restoring the upstream template reintroduces `**Status**: Draft`, which is
    OUTSIDE the closed vocabulary -- FR-006 carries no exception list. The
    Seshat-owned post-scaffold step is what closes that gap.
    """
    from seshat.spec_status_policy import (
        is_vocabulary_value,
        normalize_status_line,
        status_line_of,
    )

    text = TEMPLATE.read_text(encoding="utf-8")
    seeded = status_line_of(text)
    assert seeded is not None, "the upstream template seeds no **Status**: line"

    normalized = normalize_status_line(seeded)
    value = normalized[len("**Status**:") :].strip().split()[0]
    assert is_vocabulary_value(value), (
        f"normalizing the seeded line produced {value!r}, "
        "which is outside the vocabulary"
    )


@pytest.mark.unit
def test_the_migrated_batch_is_not_empty() -> None:
    """Guards against the migration being silently reverted to free text."""
    assert len(_specs_claiming_implemented()) >= 9


@pytest.mark.unit
def test_every_implemented_spec_names_a_tracked_artifact() -> None:
    """The one mechanically checkable claim: the artifact must actually exist."""
    tracked = _tracked_files()
    for spec in _specs_claiming_implemented():
        artifact = _IMPLEMENTED.match(_status_line(spec)).group(1)  # type: ignore[union-attr]
        assert artifact in tracked, (
            f"{spec.relative_to(REPO).as_posix()} claims implemented via {artifact!r}, "
            "which is not a tracked file"
        )


@pytest.mark.unit
def test_every_implemented_spec_has_an_sc1_claim() -> None:
    """SC1 is the enforcement; a migrated spec without a claim is unguarded."""
    registered = CLAIMS.read_text(encoding="utf-8")
    for spec in _specs_claiming_implemented():
        number = spec.parent.name.split("-", 1)[0]
        claim_id = f"spec-{number}-implemented"
        assert claim_id in registered, (
            f"{spec.relative_to(REPO).as_posix()} claims implemented but "
            f"{claim_id!r} is absent from docs/quality/status-claims.yaml"
        )


@pytest.mark.unit
def test_migration_preserves_the_previous_wording() -> None:
    """A recorded human ratification survives the change (ADR 0019 section 4)."""
    for spec in _specs_claiming_implemented():
        text = spec.read_text(encoding="utf-8")
        assert "**Status history**:" in text, (
            f"{spec.relative_to(REPO).as_posix()} was migrated without preserving its "
            "previous Status wording"
        )


@pytest.mark.unit
def test_no_implemented_status_line_carries_a_score() -> None:
    """Status is a categorical value plus evidence, never a number (hard rule #9)."""
    for spec in _specs_claiming_implemented():
        line = _status_line(spec).lower()
        for token in ("confidence", "score", "%"):
            assert token not in line, f"{spec.parent.name} Status carries {token!r}"
