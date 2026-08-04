"""Rule coverage honesty (Phase 1): a rule that could not run is not a pass.

Pins the four coverage states, the basis gate on ``not_applicable`` (an agent must
not be able to self-grant a ratified opt-in), and the census reconciliation
invariant. See docs/superpowers/specs/2026-08-04-rule-coverage-honesty-design.md.
"""

from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

import seshat.rules  # noqa: F401  -- side-effecting: fires every @register decorator
from seshat.core import RegisteredRule
from seshat.registry import all_rules
from seshat.rule_coverage import (
    AbsenceSemantics,
    CoverageState,
    Requirement,
    census,
    coverage_for,
    uncovered_rule_ids,
)

pytestmark = pytest.mark.unit


def _noop_rule(ctx: object) -> tuple[()]:
    return ()


def _registered(rule_id: str, requires: tuple[Requirement, ...] = ()) -> RegisteredRule:
    return RegisteredRule(id=rule_id, rule=_noop_rule, title=rule_id, requires=requires)


def _needs(path: str) -> Requirement:
    return Requirement(path=path, absence=AbsenceSemantics.UNEVALUABLE)


# --- the four states ---------------------------------------------------------


def test_rule_without_a_declaration_is_undeclared() -> None:
    """The default for an unmigrated rule is UNDECLARED.

    Not EVALUATED (which would silently bless the very silence being fixed) and
    not UNEVALUABLE (which would flood the report with false alarms).
    """
    record = coverage_for(_registered("X1"), missing=lambda _p: False)
    assert record.state is CoverageState.UNDECLARED
    assert record.rule_id == "X1"


def test_absent_declared_requirement_is_unevaluable_and_names_the_input() -> None:
    record = coverage_for(
        _registered("X2", (_needs("mappings/t/source-map.yaml"),)),
        missing=lambda _p: True,
    )
    assert record.state is CoverageState.UNEVALUABLE
    assert record.requirement == "mappings/t/source-map.yaml"
    assert record.reason


def test_present_requirements_yield_evaluated() -> None:
    record = coverage_for(
        _registered("X3", (_needs("warehouse/silver.sql"),)),
        missing=lambda _p: False,
    )
    assert record.state is CoverageState.EVALUATED


def test_present_but_empty_input_is_evaluated_not_unevaluable() -> None:
    """rules/sql.py:32 -- input present with nothing to match is still a real run.

    Pins the design decision: presence, not content, decides evaluability. A SQL
    file that legitimately contains no DDL is not a governance gap.
    """
    record = coverage_for(
        _registered("S1", (_needs("warehouse/empty.sql"),)),
        missing=lambda _p: False,
    )
    assert record.state is CoverageState.EVALUATED


# --- the basis gate on not_applicable ---------------------------------------


def test_not_applicable_without_a_basis_is_a_schema_error() -> None:
    """An agent must not be able to declare a ratified opt-in.

    ``not_applicable`` asserts a named human ratified this absence; declaring it
    without citing that basis would be never_self_grant_approval.
    """
    with pytest.raises(ValueError, match="basis"):
        Requirement(path="x.yaml", absence=AbsenceSemantics.NOT_APPLICABLE)


def test_not_applicable_with_a_basis_is_accepted_and_carries_it() -> None:
    requirement = Requirement(
        path="x.yaml",
        absence=AbsenceSemantics.NOT_APPLICABLE,
        basis="Principle V: floor key IS the opt-in",
    )
    record = coverage_for(_registered("X4", (requirement,)), missing=lambda _p: True)
    assert record.state is CoverageState.NOT_APPLICABLE
    assert record.basis == "Principle V: floor key IS the opt-in"


def test_unreadable_is_not_an_opt_in() -> None:
    """A requirement declared UNEVALUABLE never degrades to NOT_APPLICABLE."""
    record = coverage_for(
        _registered("X5", (_needs("locked.yaml"),)), missing=lambda _p: True
    )
    assert record.state is CoverageState.UNEVALUABLE


# --- census reconciliation ---------------------------------------------------


def test_census_covers_every_registered_rule_by_set_equality() -> None:
    """Set equality against the live registry -- never a hardcoded rule count.

    A literal count would break the moment the next rule lands -- and would have
    encoded a wrong number: a grep over @register undercounted 79 rules as 50.
    Set equality catches a rule silently dropping out, which is the real risk.
    """
    rules = all_rules()
    assert rules, "registry is empty -- import seshat.rules first, or this is vacuous"
    records = census(rules, missing=lambda _p: False)
    assert {r.rule_id for r in records} == {r.id for r in rules}
    assert len(records) == len(rules)


def test_census_emits_exactly_one_record_per_rule() -> None:
    rules = (_registered("A"), _registered("B", (_needs("gone.yaml"),)))
    records = census(rules, missing=lambda p: p == "gone.yaml")
    assert [r.rule_id for r in records] == ["A", "B"]
    assert records[0].state is CoverageState.UNDECLARED
    assert records[1].state is CoverageState.UNEVALUABLE


def test_uncovered_rule_ids_reports_undeclared_and_unevaluable_only() -> None:
    """The Phase 3 precondition counter: EVALUATED and ratified opt-ins are covered."""
    ratified = Requirement(
        path="opt.yaml",
        absence=AbsenceSemantics.NOT_APPLICABLE,
        basis="Principle V",
    )
    rules = (
        _registered("OK", (_needs("here.yaml"),)),
        _registered("GONE", (_needs("gone.yaml"),)),
        _registered("RAW"),
        _registered("OPT", (ratified,)),
    )
    records = census(rules, missing=lambda p: p in {"gone.yaml", "opt.yaml"})
    assert uncovered_rule_ids(records) == ("GONE", "RAW")


def test_coverage_record_is_immutable() -> None:
    """FrozenInstanceError -- a bare Exception would also pass on a typo'd attr."""
    record = coverage_for(_registered("X6"), missing=lambda _p: False)
    with pytest.raises(FrozenInstanceError):
        record.state = CoverageState.EVALUATED  # type: ignore[misc]


def test_record_to_dict_round_trips_state_as_its_string_value() -> None:
    """Matches Finding.to_dict: enums render as their string value for JSON."""
    record = coverage_for(
        _registered("X7", (_needs("gone.yaml"),)), missing=lambda _p: True
    )
    payload = record.to_dict()
    assert payload["rule_id"] == "X7"
    assert payload["state"] == "unevaluable"
    assert payload["requirement"] == "gone.yaml"


# --- backward compatibility of the registry extension -----------------------


def test_every_currently_registered_rule_still_constructs() -> None:
    """The registry extension must not break any existing @register site.

    Deliberately asserts no rule count: the authoritative total is whatever the
    registry holds (79 as of 2026-08-04), and a literal would rot on rule 80.
    """
    rules = all_rules()
    assert rules
    assert all(isinstance(r.id, str) and r.id for r in rules)
    assert all(hasattr(r, "requires") for r in rules)


def test_registered_rule_requires_defaults_to_empty() -> None:
    """Existing @register(id, title) sites land in UNDECLARED, not EVALUATED."""
    rules = all_rules()
    assert rules
    assert all(r.requires == () for r in rules)


def test_no_rule_reads_as_evaluated_without_declaring_its_inputs() -> None:
    """The durable invariant: coverage is never claimed without a declaration.

    Deliberately NOT "all 79 rules are UNDECLARED" -- that phrasing would fail the
    moment the first rule migrates, and a future session would read the failure as
    a regression rather than as progress. This assertion holds throughout migration
    and only breaks if a rule is credited as EVALUATED while declaring nothing.
    """
    rules = all_rules()
    records = {r.rule_id: r for r in census(rules, missing=lambda _p: False)}
    assert records
    for rule in rules:
        if not rule.requires:
            assert records[rule.id].state is CoverageState.UNDECLARED, (
                f"{rule.id} declares no inputs yet is not UNDECLARED"
            )


def test_a_note_explains_why_an_input_is_required_without_claiming_authority() -> None:
    """note is representable on an UNEVALUABLE requirement; basis is not.

    The 39 gap rules need to say WHY an input is required. That must not require
    setting basis, which cites human authority and would be a self-granted opt-in.
    """
    requirement = Requirement(
        path="warehouse/gold.sql",
        absence=AbsenceSemantics.UNEVALUABLE,
        note="absence means the gold build never ran",
    )
    record = coverage_for(_registered("G1", (requirement,)), missing=lambda _p: True)
    assert record.state is CoverageState.UNEVALUABLE
    assert record.reason == "absence means the gold build never ran"
    assert record.basis is None


def test_basis_on_an_unevaluable_requirement_is_rejected() -> None:
    """basis stays narrow: it may only ever cite a ratified opt-in."""
    with pytest.raises(ValueError, match="note="):
        Requirement(
            path="x.yaml",
            absence=AbsenceSemantics.UNEVALUABLE,
            basis="I decided this is fine",
        )
