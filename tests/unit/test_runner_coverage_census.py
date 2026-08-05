"""The runner's coverage census (component 3) and its JSON surface (component 4).

Guards the two properties that make the census safe to ship: it never changes a
verdict, and the default text output -- whose line shape is a CI contract -- is
untouched. See docs/superpowers/specs/2026-08-04-rule-coverage-honesty-design.md.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

import seshat.rules  # noqa: F401  -- side-effecting: fires every @register decorator
from seshat.core import Finding, RegisteredRule, RuleContext, RuleTier, Severity
from seshat.registry import all_rules
from seshat.rule_coverage import (
    AbsenceSemantics,
    CoverageState,
    Requirement,
    uncovered_rule_ids,
)
from seshat.runner import coverage_census, run, run_json

pytestmark = pytest.mark.unit


def _ctx(tmp_path: Path) -> RuleContext:
    return RuleContext(repo_root=tmp_path, tracked_files=())


def _clean_rule(ctx: RuleContext) -> tuple[()]:
    return ()


def _erroring_rule(ctx: RuleContext) -> list[Finding]:
    return [Finding("E1", Severity.ERROR, "boom", "somewhere")]


def _reg(
    rule_id: str,
    rule=_clean_rule,
    requires: tuple[Requirement, ...] = (),
    tier: RuleTier = RuleTier.WORK_REPO,
) -> RegisteredRule:
    return RegisteredRule(
        id=rule_id, rule=rule, title=rule_id, tier=tier, requires=requires
    )


# --- the census ---------------------------------------------------------------


def test_absent_declared_input_is_unevaluable_against_a_real_tree(
    tmp_path: Path,
) -> None:
    rules = (_reg("R1", requires=(Requirement(path="warehouse/gold.sql"),)),)
    (record,) = coverage_census(rules, _ctx(tmp_path))
    assert record.state is CoverageState.UNEVALUABLE
    assert record.requirement == "warehouse/gold.sql"


def test_present_declared_input_is_evaluated_against_a_real_tree(
    tmp_path: Path,
) -> None:
    (tmp_path / "warehouse").mkdir()
    (tmp_path / "warehouse" / "gold.sql").write_text("select 1;", encoding="utf-8")
    rules = (_reg("R2", requires=(Requirement(path="warehouse/gold.sql"),)),)
    (record,) = coverage_census(rules, _ctx(tmp_path))
    assert record.state is CoverageState.EVALUATED


def test_empty_but_present_file_is_still_evaluated(tmp_path: Path) -> None:
    """Pins the design decision at the filesystem boundary, not just in the model."""
    (tmp_path / "empty.sql").write_text("", encoding="utf-8")
    rules = (_reg("R3", requires=(Requirement(path="empty.sql"),)),)
    (record,) = coverage_census(rules, _ctx(tmp_path))
    assert record.state is CoverageState.EVALUATED


def test_a_directory_where_a_file_is_required_is_unevaluable(tmp_path: Path) -> None:
    """A path that exists but cannot be opened as a file did not let the rule run."""
    (tmp_path / "gold.sql").mkdir()
    rules = (_reg("R4", requires=(Requirement(path="gold.sql"),)),)
    (record,) = coverage_census(rules, _ctx(tmp_path))
    assert record.state is CoverageState.UNEVALUABLE


def test_tier_gated_kit_self_rule_is_not_applicable_with_a_cited_basis(
    tmp_path: Path,
) -> None:
    """The Spec A tier gate is a ratified ruling, so it may legitimately be a basis."""
    rules = (_reg("K1", tier=RuleTier.KIT_SELF),)
    (record,) = coverage_census(rules, _ctx(tmp_path), bootstrapped=False)
    assert record.state is CoverageState.NOT_APPLICABLE
    assert record.basis and "FR-006" in record.basis


def test_kit_self_rule_in_a_bootstrapped_repo_is_not_excused(tmp_path: Path) -> None:
    rules = (_reg("K2", tier=RuleTier.KIT_SELF),)
    (record,) = coverage_census(rules, _ctx(tmp_path), bootstrapped=True)
    assert record.state is CoverageState.UNDECLARED


def test_census_covers_the_live_registry_by_set_equality(tmp_path: Path) -> None:
    rules = all_rules()
    assert rules
    records = coverage_census(rules, _ctx(tmp_path))
    assert {r.rule_id for r in records} == {r.id for r in rules}


# --- the safety properties ---------------------------------------------------


def test_coverage_never_changes_the_exit_code(tmp_path: Path, capsys) -> None:
    """The load-bearing guarantee: an unevaluable rule does NOT fail the build.

    Turning unevaluated into failing is Phase 3 and needs an owner ruling, because
    a fail-closed rule must be finding-free on main before it can land.
    """
    rules = (_reg("R5", requires=(Requirement(path="absent.sql"),)),)
    exit_code = run_json(rules, _ctx(tmp_path))
    payload = json.loads(capsys.readouterr().out)
    assert payload["coverage"][0]["state"] == "unevaluable"
    assert payload["findings"] == []
    assert exit_code == 0
    assert payload["exit_code"] == 0


def test_error_findings_still_fail_alongside_a_census(tmp_path: Path, capsys) -> None:
    rules = (_reg("R6", rule=_erroring_rule),)
    exit_code = run_json(rules, _ctx(tmp_path))
    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 1
    assert payload["exit_code"] == 1
    assert len(payload["coverage"]) == 1


def test_default_text_output_is_unchanged_by_the_census(tmp_path: Path, capsys) -> None:
    """run()'s line shape is a CI contract; the census must not appear in it."""
    rules = (_reg("R7", requires=(Requirement(path="absent.sql"),)),)
    exit_code = run(rules, _ctx(tmp_path))
    assert capsys.readouterr().out == ""
    assert exit_code == 0


def test_json_findings_are_unaffected_by_adding_coverage(
    tmp_path: Path, capsys
) -> None:
    rules = (_reg("R8", rule=_erroring_rule),)
    run_json(rules, _ctx(tmp_path))
    payload = json.loads(capsys.readouterr().out)
    assert payload["findings"] == [
        {
            "rule_id": "E1",
            "severity": "error",
            "message": "boom",
            "locator": "somewhere",
        }
    ]


def test_uncovered_ids_exclude_the_ratified_tier_gate(tmp_path: Path) -> None:
    """A cited opt-in is decided, so it is covered; only real gaps are reported."""
    rules = (
        _reg("K3", tier=RuleTier.KIT_SELF),
        _reg("R9", requires=(Requirement(path="absent.sql"),)),
    )
    records = coverage_census(rules, _ctx(tmp_path), bootstrapped=False)
    assert uncovered_rule_ids(records) == ("R9",)


def test_a_ratified_requirement_opt_in_survives_the_runner(tmp_path: Path) -> None:
    ratified = Requirement(
        path="optional.yaml",
        absence=AbsenceSemantics.NOT_APPLICABLE,
        basis="Principle V: floor key IS the opt-in",
    )
    rules = (_reg("R10", requires=(ratified,)),)
    (record,) = coverage_census(rules, _ctx(tmp_path))
    assert record.state is CoverageState.NOT_APPLICABLE
    assert record.basis == "Principle V: floor key IS the opt-in"


# --- the pattern (file-class) requirement form --------------------------------


def test_empty_corpus_is_unevaluable(tmp_path: Path) -> None:
    """The gap this form exists for: a rule scans a class of files and finds none.

    Such a rule returns no findings while having verified nothing, which is
    indistinguishable from a clean pass in the findings list alone.
    """
    from seshat.sql import WAREHOUSE_SQL_CORPUS

    rules = (_reg("S1", requires=(WAREHOUSE_SQL_CORPUS,)),)
    ctx = RuleContext(repo_root=tmp_path, tracked_files=("docs/readme.md",))
    (record,) = coverage_census(rules, ctx)
    assert record.state is CoverageState.UNEVALUABLE
    assert record.requirement == "warehouse/*.sql"


def test_non_empty_corpus_is_evaluated(tmp_path: Path) -> None:
    from seshat.sql import WAREHOUSE_SQL_CORPUS

    rules = (_reg("S1", requires=(WAREHOUSE_SQL_CORPUS,)),)
    ctx = RuleContext(
        repo_root=tmp_path, tracked_files=("warehouse/migrations/001_silver.sql",)
    )
    (record,) = coverage_census(rules, ctx)
    assert record.state is CoverageState.EVALUATED


def test_corpus_glob_matches_the_rules_own_iterator_exactly(tmp_path: Path) -> None:
    """Guards against the glob and iter_sql_files drifting apart.

    A declaration that disagreed with the iterator would be WORSE than no
    declaration: it would report `evaluated` for a rule that scanned nothing.
    """
    from seshat.core import RuleContext as Ctx
    from seshat.sql import WAREHOUSE_SQL_CORPUS, iter_sql_files

    candidates = (
        "warehouse/silver.sql",
        "warehouse/migrations/001_x.sql",
        "docs/x.sql",
        "warehouse/notes.md",
        "tests/fixtures/q.sql",
    )
    for candidate in candidates:
        ctx = Ctx(repo_root=tmp_path, tracked_files=(candidate,))
        iterator_saw_it = bool(iter_sql_files(ctx))
        (record,) = coverage_census(
            (_reg("S1", requires=(WAREHOUSE_SQL_CORPUS,)),), ctx
        )
        declared_ran = record.state is CoverageState.EVALUATED
        assert declared_ran == iterator_saw_it, candidate


def test_requirement_rejects_declaring_both_forms() -> None:
    with pytest.raises(ValueError, match="not both"):
        Requirement(path="a.sql", pattern="warehouse/*.sql")


def test_requirement_rejects_declaring_neither_form() -> None:
    with pytest.raises(ValueError, match="declares no input"):
        Requirement()
