"""The ratification grammars must agree with the policy authority (spec 151).

Three places describe what a ratified spec looks like, and before spec 151 they
disagreed:

* ``seshat.spec_status_policy`` -- the authority, lowercase ``ratified``
  (ADR 0019);
* ``.claude/workflows/implement.js`` -- the H3 gate, which REFUSED the merged
  ``specs/150-dbt-evidence-consumer`` because its regex required capital
  ``Ratified (Name, date)``;
* ``.claude/workflows/idea-to-spec.js`` -- the PRODUCER, which instructs authors
  to write that same capital form.

These tests read the real regexes out of the real workflow file rather than
restating them, so the two verifiers cannot silently drift apart (FR-011).
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from seshat.spec_status_policy import validate_status_line

pytestmark = pytest.mark.unit

REPO = Path(__file__).resolve().parents[2]
IMPLEMENT_JS = REPO / ".claude/workflows/implement.js"
IDEA_TO_SPEC_JS = REPO / ".claude/workflows/idea-to-spec.js"

#: The canonical ratified form the authority accepts, per ADR 0019.
CANONICAL_RATIFIED = "**Status**: ratified -- Ahmed Shaaban, 2026-08-08"

#: The legacy form already committed across ~40 specs. Widening is ADDITIVE
#: (FR-010), so this must keep working.
LEGACY_RATIFIED = "**Status**: Ratified (Ahmed Shaaban, 2026-08-08)"


def _js_regex(name: str, source: str) -> re.Pattern[str]:
    """Extract a JS regex literal from the workflow and port it to Python.

    Reading the REAL pattern is the point: a copy in this file would be a third
    restatement of the thing these tests exist to keep singular.
    """
    match = re.search(rf"const {name}\s*=\s*/(?P<body>.+?)/(?P<flags>[a-z]*)\n", source)
    assert match, f"{name} not found in the workflow source"
    body = match.group("body")
    flags = 0
    if "i" in match.group("flags"):
        flags |= re.IGNORECASE
    if "m" in match.group("flags"):
        flags |= re.MULTILINE
    return re.compile(body, flags)


@pytest.fixture(scope="module")
def implement_source() -> str:
    return IMPLEMENT_JS.read_text(encoding="utf-8")


# --------------------------------------------------------------------------
# T008a -- the canonical form must be accepted by the H3 gate (FR-010)
# --------------------------------------------------------------------------


def test_the_authority_accepts_the_canonical_ratified_form() -> None:
    assert validate_status_line(CANONICAL_RATIFIED).ok


def test_h3_accepts_the_canonical_ratified_form(implement_source: str) -> None:
    """The defect spec 151 fixes.

    Before reconciliation this failed: H3 required capital `Ratified (...)`, so
    a spec ratified exactly as ADR 0019 instructs was refused by the workflow
    that consumes ratification.
    """
    ratified = _js_regex("H3_RATIFIED_RE", implement_source)
    assert ratified.search(CANONICAL_RATIFIED), (
        "H3 refuses the canonical ADR-0019 ratified form; the authority and the "
        "gate disagree (spec 151 FR-010)"
    )


def test_h3_still_accepts_the_legacy_form(implement_source: str) -> None:
    """Widening is additive: an already-ratified spec cannot be invalidated."""
    ratified = _js_regex("H3_RATIFIED_RE", implement_source)
    assert ratified.search(LEGACY_RATIFIED)


def test_h3_accepts_the_real_merged_spec_150_line(implement_source: str) -> None:
    """The concrete artifact that proved the defect, pinned as a regression."""
    spec = REPO / "specs/150-dbt-evidence-consumer/spec.md"
    if not spec.exists():  # pragma: no cover - present on main
        pytest.skip("spec 150 not present in this tree")
    ratified = _js_regex("H3_RATIFIED_RE", implement_source)
    assert ratified.search(spec.read_text(encoding="utf-8"))


# --------------------------------------------------------------------------
# T008a-history -- the widening must not swallow a history line (FR-012a)
# --------------------------------------------------------------------------


def test_the_draft_grammar_ignores_a_status_history_line(implement_source: str) -> None:
    """The regression a naive widening introduces.

    Widening the prefix to `\\*\\*Status[^*]*\\*\\*` makes `**Status history**:
    draft` match the DRAFT regex, which would refuse a correctly ratified spec
    that carries the ADR-mandated history line -- including spec 150.
    """
    draft = _js_regex("H3_DRAFT_RE", implement_source)
    assert not draft.search("**Status history**: draft"), (
        "the draft grammar matches a **Status history**: line; a ratified spec "
        "carrying its history would be wrongly refused (spec 151 FR-012a)"
    )


def test_a_ratified_spec_with_history_passes_the_whole_h3_shape(
    implement_source: str,
) -> None:
    """The composite gate, as `implement.js` actually evaluates it."""
    ratified = _js_regex("H3_RATIFIED_RE", implement_source)
    draft = _js_regex("H3_DRAFT_RE", implement_source)
    blocked = _js_regex("H3_BLOCKED_RE", implement_source)
    text = f"{CANONICAL_RATIFIED}\n\n**Status history**: draft\n"
    assert ratified.search(text) and not draft.search(text) and not blocked.search(text)


# --------------------------------------------------------------------------
# T008b/T008c -- the gate stays fail-closed (FR-012)
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "line",
    (
        "**Status**: ratified",
        "**Status**: ratified -- Ahmed Shaaban",
        "**Status**: ratified -- , 2026-08-08",
        "**Status**: draft",
        # Codex P2 on PR #600: `\s+` backtracked, so a lone space satisfied the
        # "named human" requirement in BOTH validators.
        "**Status**: ratified --  , 2026-08-08",
        "**Status**: Ratified ( , 2026-08-08)",
        # Codex P2 on PR #600: the prefix-only match let trailing text through
        # H3 while the authority rejected the same line -- the grammar
        # "agreement" had a hole on exactly the input that authorizes a build.
        "**Status**: ratified -- Name, 2026-08-08 trailing",
        "**Status**: Ratified (Name, 2026-08-08) trailing",
    ),
)
def test_h3_refuses_an_unnamed_undated_or_trailing_ratification(
    implement_source: str, line: str
) -> None:
    """Reconciliation must not loosen the gate into accepting anything."""
    ratified = _js_regex("H3_RATIFIED_RE", implement_source)
    assert not ratified.search(line)


@pytest.mark.parametrize(
    "line",
    (
        "**Status**: ratified --  , 2026-08-08",
        "**Status**: ratified -- Name, 2026-08-08 trailing",
    ),
)
def test_the_two_validators_agree_on_the_codex_findings(
    implement_source: str, line: str
) -> None:
    """The whole point of FR-011: both verifiers reach the SAME verdict.

    Each of these lines was accepted by one validator and rejected by the other
    before the PR #600 review.
    """
    ratified = _js_regex("H3_RATIFIED_RE", implement_source)
    assert not ratified.search(line)
    assert not validate_status_line(line).ok


@pytest.mark.parametrize(
    "line",
    (
        "**Status**: ratified",
        "**Status**: ratified -- Ahmed Shaaban",
        "**Status**: ratified -- , 2026-08-08",
    ),
)
def test_the_authority_refuses_the_same_incomplete_ratifications(line: str) -> None:
    """The two verifiers agree on rejection, not only on acceptance.

    `**Status**: draft` is deliberately NOT in this list: it is a valid draft
    status that the authority accepts, and which H3 separately refuses to treat
    as ratified. The two verifiers answer different questions about it, and
    that is correct.
    """
    assert not validate_status_line(line).ok


# --------------------------------------------------------------------------
# T008d -- the third grammar, the producer (FR-026)
# --------------------------------------------------------------------------


def test_the_producer_instructs_the_canonical_form() -> None:
    """`idea-to-spec.js` tells the human what to write; it must not teach a form
    the authority rejects."""
    source = IDEA_TO_SPEC_JS.read_text(encoding="utf-8")
    assert "ratified -- <name>" in source or "ratified -- " in source, (
        "idea-to-spec.js still instructs only the legacy capital form; the "
        "producer and the authority disagree (spec 151 FR-026)"
    )


def test_the_producer_still_cannot_emit_a_ratified_status() -> None:
    """Reconciling the instruction must not weaken the self-ratification bar."""
    source = IDEA_TO_SPEC_JS.read_text(encoding="utf-8")
    assert "FORBIDDEN" in source
    assert "human" in source
