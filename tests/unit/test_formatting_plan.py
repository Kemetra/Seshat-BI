"""Unit tests for DL7 (formatting-plan ledger well-formedness)."""

from __future__ import annotations

from pathlib import Path

import pytest

from retail.core import RuleContext, Severity
from retail.rules.formatting_plan import RULE_ID, check_formatting_plan

pytestmark = pytest.mark.unit

FIXTURES = Path(__file__).parent.parent / "fixtures" / "formatting_plan"


def _ctx(stem: str) -> RuleContext:
    # DL7 discovers files by the ``formatting-plan.md`` suffix, so every fixture
    # is named ``<stem>-formatting-plan.md``; the test refers to it by stem.
    return RuleContext(
        repo_root=FIXTURES, tracked_files=(f"{stem}-formatting-plan.md",)
    )


def test_clean_ledger_passes() -> None:
    assert list(check_formatting_plan(_ctx("clean"))) == []


def test_missing_principle_fails() -> None:
    f = list(check_formatting_plan(_ctx("bad_missing_principle")))
    assert any(x.rule_id == RULE_ID for x in f)
    assert any("principle" in x.message.lower() for x in f)


def test_unresolvable_principle_fails() -> None:
    f = list(check_formatting_plan(_ctx("bad_unresolvable_principle")))
    assert any("#99" in x.message or "resolve" in x.message.lower() for x in f)


def test_render_only_cited_as_resolved_fails() -> None:
    f = list(check_formatting_plan(_ctx("bad_render_only_resolved")))
    assert any("render-only" in x.message.lower() for x in f)


def test_score_field_fails() -> None:
    f = list(check_formatting_plan(_ctx("bad_has_score")))
    assert any("score" in x.message.lower() for x in f)


def test_agent_ratified_fails() -> None:
    f = list(check_formatting_plan(_ctx("bad_agent_ratified")))
    assert any("ratif" in x.message.lower() for x in f)


def test_out_of_allowlist_container_fails() -> None:
    f = list(check_formatting_plan(_ctx("bad_out_of_allowlist")))
    assert any("allow-list" in x.message.lower() for x in f)


def test_missing_token_fails() -> None:
    f = list(check_formatting_plan(_ctx("bad_missing_token")))
    assert any(x.rule_id == RULE_ID for x in f)
    assert any("token" in x.message.lower() for x in f)


def test_self_declared_outcome_status_fails() -> None:
    # A row may NEVER self-declare a human-render outcome (resolved) -- on ANY row,
    # not just render-only ones (never_self_grant_approval / Principle V).
    f = list(check_formatting_plan(_ctx("bad_self_resolved")))
    assert any("outcome" in x.message.lower() for x in f)


def test_score_in_rationale_prose_is_not_a_false_positive() -> None:
    # The word "score" inside a rationale CELL must not trip the field check
    # (line-anchored regex). clean.md's rationale has no "score:"; build one inline.
    import tempfile

    ledger = (
        "# fixture\n\n"
        "| target | container | group | property | value | principle_cited | "
        "token_cited | apply_verb | status | rationale |\n"
        "|---|---|---|---|---|---|---|---|---|---|\n"
        "| page:x | objects | labels | show | true | #4 | number_format.integer | "
        "B | proposed | improves clarity score for readers |\n\n"
        "## Ratification\n\n- ratification.ratified_by:\n"
    )
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "prose-formatting-plan.md"
        p.write_text(ledger, encoding="utf-8")
        ctx = RuleContext(
            repo_root=Path(d), tracked_files=("prose-formatting-plan.md",)
        )
        f = list(check_formatting_plan(ctx))
        assert not any("score" in x.message.lower() for x in f), (
            f"prose 'score' false-positived: {[x.message for x in f]}"
        )


def test_severity_is_error() -> None:
    f = list(check_formatting_plan(_ctx("bad_has_score")))
    assert all(x.severity is Severity.ERROR for x in f)


def test_test_fixtures_are_exempt_when_under_tests_path() -> None:
    ctx = RuleContext(
        repo_root=FIXTURES,
        tracked_files=(
            "tests/fixtures/formatting_plan/bad_has_score-formatting-plan.md",
        ),
    )
    assert list(check_formatting_plan(ctx)) == []
