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
    ContextInput,
    CoverageState,
    ReportsItsOwnAbsence,
    Requirement,
    any_tracked_file,
    census,
    coverage_for,
    uncovered_rule_ids,
    validate_declarations,
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
    record = coverage_for(_registered("X1"), missing=lambda _r: False)
    assert record.state is CoverageState.UNDECLARED
    assert record.rule_id == "X1"


def test_absent_declared_requirement_is_unevaluable_and_names_the_input() -> None:
    record = coverage_for(
        _registered("X2", (_needs("mappings/t/source-map.yaml"),)),
        missing=lambda _r: True,
    )
    assert record.state is CoverageState.UNEVALUABLE
    assert record.requirement == "mappings/t/source-map.yaml"
    assert record.reason


def test_present_requirements_yield_evaluated() -> None:
    record = coverage_for(
        _registered("X3", (_needs("warehouse/silver.sql"),)),
        missing=lambda _r: False,
    )
    assert record.state is CoverageState.EVALUATED


def test_present_but_empty_input_is_evaluated_not_unevaluable() -> None:
    """rules/sql.py:32 -- input present with nothing to match is still a real run.

    Pins the design decision: presence, not content, decides evaluability. A SQL
    file that legitimately contains no DDL is not a governance gap.
    """
    record = coverage_for(
        _registered("S1", (_needs("warehouse/empty.sql"),)),
        missing=lambda _r: False,
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
    record = coverage_for(_registered("X4", (requirement,)), missing=lambda _r: True)
    assert record.state is CoverageState.NOT_APPLICABLE
    assert record.basis == "Principle V: floor key IS the opt-in"


def test_unreadable_is_not_an_opt_in() -> None:
    """A requirement declared UNEVALUABLE never degrades to NOT_APPLICABLE."""
    record = coverage_for(
        _registered("X5", (_needs("locked.yaml"),)), missing=lambda _r: True
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
    records = census(rules, missing=lambda _r: False)
    assert {r.rule_id for r in records} == {r.id for r in rules}
    assert len(records) == len(rules)


def test_census_emits_exactly_one_record_per_rule() -> None:
    rules = (_registered("A"), _registered("B", (_needs("gone.yaml"),)))
    records = census(rules, missing=lambda r: r.target == "gone.yaml")
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
    records = census(rules, missing=lambda r: r.target in {"gone.yaml", "opt.yaml"})
    assert uncovered_rule_ids(records) == ("GONE", "RAW")


def test_coverage_record_is_immutable() -> None:
    """FrozenInstanceError -- a bare Exception would also pass on a typo'd attr."""
    record = coverage_for(_registered("X6"), missing=lambda _r: False)
    with pytest.raises(FrozenInstanceError):
        record.state = CoverageState.EVALUATED  # type: ignore[misc]


def test_record_to_dict_round_trips_state_as_its_string_value() -> None:
    """Matches Finding.to_dict: enums render as their string value for JSON."""
    record = coverage_for(
        _registered("X7", (_needs("gone.yaml"),)), missing=lambda _r: True
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
    """A rule registered WITHOUT `requires=` defaults to (), so it lands in
    UNDECLARED rather than being silently credited as EVALUATED.

    Asserts the DEFAULT, not the state of the live registry. An "all rules have
    requires == ()" phrasing would fail as soon as any rule migrates, turning
    progress into a red suite.
    """
    assert RegisteredRule(id="Z1", rule=_noop_rule, title="Z1").requires == ()
    assert (
        coverage_for(_registered("Z1"), missing=lambda _r: False).state
        is CoverageState.UNDECLARED
    )


def test_no_rule_reads_as_evaluated_without_declaring_its_inputs() -> None:
    """The durable invariant: coverage is never claimed without a declaration.

    Deliberately NOT "all 79 rules are UNDECLARED" -- that phrasing would fail the
    moment the first rule migrates, and a future session would read the failure as
    a regression rather than as progress. This assertion holds throughout migration
    and only breaks if a rule is credited as EVALUATED while declaring nothing.
    """
    rules = all_rules()
    records = {r.rule_id: r for r in census(rules, missing=lambda _r: False)}
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
    record = coverage_for(_registered("G1", (requirement,)), missing=lambda _r: True)
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


# --- the any-of group form ---------------------------------------------------


def test_a_group_is_present_when_any_one_alternative_is() -> None:
    """The reason the group form exists: a corpus selected by ALTERNATION.

    G3 accepts four suffixes and the decision store three files. Declaring the arms
    as separate requirements would AND them, reporting a rule that ran fine as
    unevaluable the moment any single arm was missing.
    """
    group = any_tracked_file("*.tmdl", "*.pbir", "*.pbism")
    record = coverage_for(
        _registered("G3", (group,)), missing=lambda r: r.pattern != "*.pbir"
    )
    assert record.state is CoverageState.EVALUATED


def test_a_group_is_absent_only_when_every_alternative_is() -> None:
    group = any_tracked_file("*.tmdl", "*.pbir", note="no model file is tracked")
    record = coverage_for(_registered("G3", (group,)), missing=lambda _r: True)
    assert record.state is CoverageState.UNEVALUABLE
    assert record.requirement == "any of: *.tmdl, *.pbir"
    assert record.reason == "no model file is tracked"


def test_a_group_still_ands_with_a_sibling_requirement() -> None:
    """Alternation is INSIDE the group; the requirement tuple keeps AND semantics."""
    rules = _registered(
        "X", (any_tracked_file("*.tmdl", "*.pbir"), _needs("docs/spine.yaml"))
    )
    record = coverage_for(rules, missing=lambda r: r.path == "docs/spine.yaml")
    assert record.state is CoverageState.UNEVALUABLE
    assert record.requirement == "docs/spine.yaml"


def test_the_factory_applies_one_exclusion_to_every_alternative() -> None:
    """A fixture exemption left off one arm is exactly how a declaration lies."""
    group = any_tracked_file("*.tmdl", "*.pbir", exclude=("tests/*",))
    assert [alt.exclude for alt in group.any_of] == [("tests/*",), ("tests/*",)]


def test_a_single_alternative_group_is_rejected() -> None:
    with pytest.raises(ValueError, match="single alternative"):
        Requirement(any_of=(Requirement(pattern="*.tmdl"),))


def test_a_group_alternative_may_not_carry_its_own_semantics() -> None:
    """A basis the group would ignore is a silently discarded authority claim."""
    with pytest.raises(ValueError, match="basis/note"):
        Requirement(
            any_of=(
                Requirement(pattern="*.tmdl", note="mine"),
                Requirement(pattern="*.pbir"),
            )
        )


def test_groups_do_not_nest() -> None:
    with pytest.raises(ValueError, match="groups do not nest"):
        Requirement(
            any_of=(
                any_tracked_file("*.tmdl", "*.pbir"),
                Requirement(pattern="*.json"),
            )
        )


def test_declaring_two_forms_at_once_is_rejected() -> None:
    with pytest.raises(ValueError, match="exactly ONE form"):
        Requirement(pattern="*.tmdl", context=ContextInput.COMMIT_SUBJECTS)


def test_exclude_is_rejected_where_it_would_be_inert() -> None:
    """An exclusion that LOOKS like it mirrors a rule's exemption but does nothing."""
    with pytest.raises(ValueError, match="exclude="):
        Requirement(path="docs/spine.yaml", exclude=("tests/*",))


# --- the invocation-field form -----------------------------------------------


def test_a_context_requirement_names_the_invocation_field() -> None:
    """P2's input is a commit subject, not a file -- and can still be missing."""
    requirement = Requirement(
        context=ContextInput.COMMIT_SUBJECTS, note="no subject was supplied"
    )
    assert requirement.target == ContextInput.COMMIT_SUBJECTS.value
    record = coverage_for(_registered("P2", (requirement,)), missing=lambda _r: True)
    assert record.state is CoverageState.UNEVALUABLE
    assert record.reason == "no subject was supplied"


def test_a_supplied_context_input_is_evaluated() -> None:
    requirement = Requirement(context=ContextInput.COMMIT_SUBJECTS)
    record = coverage_for(_registered("P2", (requirement,)), missing=lambda _r: False)
    assert record.state is CoverageState.EVALUATED


# --- the self-reporting form --------------------------------------------------


def test_a_self_reporting_rule_is_evaluated_and_says_what_it_reports() -> None:
    """A rule that ERRORs on absent input never went silent, so it ran."""
    declaration = ReportsItsOwnAbsence(
        note="G1 reports each missing .gitignore entry as an ERROR"
    )
    record = coverage_for(
        _registered("G1", (declaration,)),
        missing=lambda _r: True,  # nothing on disk; the claim is input-independent
    )
    assert record.state is CoverageState.EVALUATED
    assert record.reason == "G1 reports each missing .gitignore entry as an ERROR"
    assert record.basis is None


def test_a_self_reporting_claim_without_a_note_is_rejected() -> None:
    """The note IS the claim a test measures; an empty one asserts nothing."""
    with pytest.raises(ValueError, match="note"):
        ReportsItsOwnAbsence(note="   ")


def test_a_self_reporting_claim_cannot_sit_beside_a_requirement() -> None:
    """The two contradict, and the self-reporting form wins -- so it must be alone.

    Accepting the mix would silently discard a real requirement, quietly crediting
    a rule that a declared input can in fact silence.
    """
    with pytest.raises(ValueError, match="ONLY declaration"):
        validate_declarations(
            "G1", (ReportsItsOwnAbsence(note="reports absence"), _needs("x.yaml"))
        )


def test_validate_declarations_accepts_the_legitimate_shapes() -> None:
    assert validate_declarations("A", ()) == ()
    solo = (ReportsItsOwnAbsence(note="reports absence"),)
    assert validate_declarations("B", solo) == solo
    pair = (_needs("a.yaml"), _needs("b.yaml"))
    assert validate_declarations("C", pair) == pair
