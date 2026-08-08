"""The Seshat-owned spec-status policy authority (spec 151, ADR 0019).

Before spec 151 the vocabulary lived in two places, neither of them Seshat code:
an 11-line comment inside `.specify/templates/spec-template.md` -- a file
upstream Spec Kit owns and regenerates -- and a tuple inside the test that
validated that comment. The test read the template to learn the policy it then
checked, so the artifact under validation was also the source of the
expectation.

These tests pin the replacement: one importable authority in `src/seshat/`,
which must NOT read the template (FR-004), must reject everything outside the
closed vocabulary with no exception list (FR-006), and must fail closed on an
absent or unparseable line (FR-018/FR-019).
"""

from __future__ import annotations

import inspect
from pathlib import Path

import pytest

from seshat import spec_status_policy as policy

pytestmark = pytest.mark.unit


# --------------------------------------------------------------------------
# T003 -- the vocabulary
# --------------------------------------------------------------------------


def test_the_vocabulary_is_exactly_the_four_adr_values() -> None:
    assert policy.VOCABULARY == ("draft", "ratified", "implemented", "superseded")


@pytest.mark.parametrize("value", ("draft", "ratified", "implemented", "superseded"))
def test_each_canonical_value_is_recognized(value: str) -> None:
    assert policy.is_vocabulary_value(value)


def test_the_canonical_case_is_lowercase() -> None:
    assert policy.canonical_case("Draft") == "draft"
    assert policy.canonical_case("RATIFIED") == "ratified"


# --------------------------------------------------------------------------
# T003 / FR-006 -- rejection, with NO exception list
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "value",
    (
        "Draft",
        "Ratified",
        "Implemented",
        "Shipped",
        "**BUILT**",
        "Finalized",
        "Planned",
        "Approved for planning",
        "",
    ),
)
def test_real_corpus_values_outside_the_vocabulary_are_rejected(value: str) -> None:
    """Every value in this list occurs in the committed corpus today.

    110 of 139 specs carry one. The authority must be CAPABLE of rejecting each
    (FR-024) even though this feature does not apply it corpus-wide (FR-023).
    """
    assert not policy.is_vocabulary_value(value)


def test_capital_draft_is_rejected_and_carries_no_carve_out() -> None:
    """FR-006 has no exception list.

    The seeded upstream ``Draft`` is handled by normalizing it at scaffold time
    (FR-025), never by excusing it in the vocabulary rule. If this test ever
    fails, the exception list has been reintroduced.
    """
    assert not policy.is_vocabulary_value("Draft")
    verdict = policy.validate_status_line("**Status**: Draft")
    assert not verdict.ok
    assert "draft" in verdict.detail


# --------------------------------------------------------------------------
# T004 -- fail closed (FR-018 / FR-019)
# --------------------------------------------------------------------------


def test_absent_status_line_is_a_named_defect(tmp_path: Path) -> None:
    spec = tmp_path / "spec.md"
    spec.write_text("# Feature Specification\n\nno status here\n", encoding="utf-8")
    verdict = policy.validate_spec_file(spec)
    assert not verdict.ok
    assert "no `**Status**:` line" in verdict.detail


def test_unparseable_status_line_is_a_named_defect() -> None:
    verdict = policy.validate_status_line("**Status**:")
    assert not verdict.ok
    assert verdict.detail


def test_unreadable_file_is_reported_not_skipped(tmp_path: Path) -> None:
    """A read failure must surface, never degrade into a silent pass."""
    missing = tmp_path / "does-not-exist.md"
    verdict = policy.validate_spec_file(missing)
    assert not verdict.ok
    assert "could not be read" in verdict.detail


def test_absence_is_never_ok() -> None:
    for line in ("", "   ", "**Statue**: draft"):
        assert not policy.validate_status_line(line).ok


# --------------------------------------------------------------------------
# T003 -- evidence requirements per value
# --------------------------------------------------------------------------


def test_ratified_requires_a_name_and_a_date() -> None:
    assert policy.validate_status_line(
        "**Status**: ratified -- Ahmed Shaaban, 2026-08-08"
    ).ok
    assert not policy.validate_status_line("**Status**: ratified").ok
    assert not policy.validate_status_line("**Status**: ratified -- Ahmed Shaaban").ok


def test_implemented_requires_a_named_artifact() -> None:
    assert policy.validate_status_line(
        "**Status**: implemented -- artifact `src/seshat/foo.py`"
    ).ok
    assert not policy.validate_status_line("**Status**: implemented").ok


def test_draft_needs_no_evidence() -> None:
    assert policy.validate_status_line("**Status**: draft").ok


def test_superseded_requires_a_superseding_id() -> None:
    assert policy.validate_status_line("**Status**: superseded -- by spec 152").ok
    assert not policy.validate_status_line("**Status**: superseded").ok


# --------------------------------------------------------------------------
# T005 -- anti-circularity (FR-004)
# --------------------------------------------------------------------------


def _executable_source(module) -> str:
    """Module source with docstrings and comments stripped.

    The risk is that the authority READS the upstream template, not that it
    mentions one -- its own docstring necessarily names the file it must not
    open. Grepping raw source would conflate a code path with prose, so the
    oracle is put on the executable statements instead.
    """
    import ast

    tree = ast.parse(inspect.getsource(module))
    for node in ast.walk(tree):
        if (
            isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef))
            and ast.get_docstring(node) is not None
        ):
            node.body = node.body[1:]
    return ast.unparse(tree)


def test_the_authority_never_reads_the_upstream_template() -> None:
    """A checker that derives its expectation from the artifact it validates
    proves nothing. This is the defect spec 151 exists to remove, so it is
    pinned rather than trusted."""
    source = _executable_source(policy)
    assert "spec-template" not in source
    assert ".specify" not in source
    assert "templates" not in source


def test_the_authority_declares_no_readiness_vocabulary() -> None:
    """FR-003: not a second state machine, and not the readiness spine."""
    source = _executable_source(policy)
    for token in ("not_started", "readiness_status", "gold_ready"):
        assert token not in source


# --------------------------------------------------------------------------
# T008-scaffold -- normalization (FR-025 / FR-025a)
# --------------------------------------------------------------------------


def test_normalizes_the_upstream_seeded_value() -> None:
    assert policy.normalize_status_line("**Status**: Draft") == "**Status**: draft"


def test_normalization_is_idempotent() -> None:
    once = policy.normalize_status_line("**Status**: Draft")
    assert policy.normalize_status_line(once) == once


def test_normalization_preserves_evidence() -> None:
    line = "**Status**: Ratified -- Ahmed Shaaban, 2026-08-08"
    assert (
        policy.normalize_status_line(line)
        == "**Status**: ratified -- Ahmed Shaaban, 2026-08-08"
    )


def test_normalization_fails_closed_on_an_unparseable_line() -> None:
    """FR-025a: an unknown line is reported, not silently rewritten."""
    with pytest.raises(policy.StatusPolicyError):
        policy.normalize_status_line("**Status**: Approved for planning")


def test_normalization_leaves_a_history_line_alone() -> None:
    """`**Status history**:` is not the status line and must not be rewritten."""
    line = "**Status history**: draft"
    assert policy.normalize_status_line(line) == line
