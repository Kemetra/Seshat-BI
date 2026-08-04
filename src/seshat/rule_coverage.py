"""Rule coverage: distinguish "checked and clean" from "never checked".

A rule contributing no findings is ambiguous today -- it can mean the rule ran
against real input and found nothing wrong, or that its required input was absent
so it early-returned. A human reading a clean gate cannot tell those apart, which
is the same defect class the gate exists to prevent, located inside the gate.

This module is the vocabulary for that distinction. It is pure: no I/O, no writes,
no network. Presence of an input is supplied by the caller as a ``missing``
predicate, which keeps the states unit-testable without a filesystem.

Design: docs/superpowers/specs/2026-08-04-rule-coverage-honesty-design.md
Precedent: ``RuleTier.KIT_SELF`` (core.py) already established "absence is not
drift" by emitting one INFO finding on skip; what it lacks is a machine-readable
census, which is what this module adds.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Callable, Iterable, TypedDict

from .core import RegisteredRule


class AbsenceSemantics(str, Enum):
    """What it MEANS that a declared requirement is absent.

    ``UNEVALUABLE`` is the honest default: the input should have been there, so
    the rule could not do its job and must not read as a pass.

    ``NOT_APPLICABLE`` asserts that a named human ratified this absence as an
    intentional opt-in. It therefore requires a ``basis`` -- see
    :class:`Requirement`.
    """

    UNEVALUABLE = "unevaluable"
    NOT_APPLICABLE = "not-applicable"


class CoverageState(str, Enum):
    """The outcome of asking "did this rule actually run?"."""

    EVALUATED = "evaluated"  # ran on present input; empty findings = verified clean
    UNEVALUABLE = "unevaluable"  # required input absent/unreadable -- the honesty gap
    UNDECLARED = "undeclared"  # rule has not declared its applicability yet
    NOT_APPLICABLE = "not-applicable"  # ratified opt-in, carries its basis


class CoverageDict(TypedDict):
    """Serialized shape of a :class:`CoverageRecord`."""

    rule_id: str
    state: str
    requirement: str | None
    reason: str | None
    basis: str | None


@dataclass(frozen=True)
class Requirement:
    """An input a rule needs in order to run, plus what its absence means.

    ``basis`` is mandatory when ``absence`` is ``NOT_APPLICABLE`` and forbidden
    otherwise. That asymmetry is deliberate and load-bearing: ``NOT_APPLICABLE``
    claims a human ratified the opt-in, so an agent that could set it without
    citing a source would be self-granting an approval. Making the omission a
    construction-time ``ValueError`` means the code cannot express the
    unauthorized state at all, rather than relying on review to catch it.

    ``note`` is the separate, ungated place to say WHY this input is required
    (e.g. "absence means the gold build never ran"). It is deliberately not
    ``basis``: keeping ``basis`` narrow -- it cites human authority and nothing
    else -- is what stops it becoming a free-text field an agent can fill in to
    manufacture an opt-in. A note is documentation; a basis is a citation.
    """

    path: str
    absence: AbsenceSemantics = AbsenceSemantics.UNEVALUABLE
    basis: str | None = None
    note: str | None = None

    def __post_init__(self) -> None:
        # Branches on the absence semantics rather than testing compound
        # conditions, so each rule about `basis` reads on its own line.
        if self.absence is AbsenceSemantics.NOT_APPLICABLE:
            if not (self.basis or "").strip():
                raise ValueError(
                    f"requirement {self.path!r}: absence=not-applicable claims a "
                    "ratified opt-in and so requires a basis naming the ruling "
                    "that authorized it (an agent may not self-grant one)"
                )
        elif self.basis is not None:
            raise ValueError(
                f"requirement {self.path!r}: basis cites the human ruling behind "
                "absence=not-applicable and is meaningful only there; to explain "
                "why this input is required, use note="
            )


@dataclass(frozen=True)
class CoverageRecord:
    """Exactly one per registered rule per run."""

    rule_id: str
    state: CoverageState
    requirement: str | None = None
    reason: str | None = None
    basis: str | None = None

    def to_dict(self) -> CoverageDict:
        """Plain-dict view; state renders as its string value, as Finding does."""
        return {
            "rule_id": self.rule_id,
            "state": self.state.value,
            "requirement": self.requirement,
            "reason": self.reason,
            "basis": self.basis,
        }


# A caller-supplied "is this input absent?" predicate. Keeping presence out of
# this module is what makes every state reachable in a unit test with no tmpdir.
MissingPredicate = Callable[[str], bool]


def _first_absent(
    requires: tuple[Requirement, ...], missing: MissingPredicate
) -> Requirement | None:
    """The absent requirement that decides the state.

    An absent ``UNEVALUABLE`` requirement outranks an absent ``NOT_APPLICABLE``
    one: if any input the rule genuinely needed is gone, the rule did not run,
    and a ratified opt-in elsewhere must not launder that into coverage.
    """
    absent = [req for req in requires if missing(req.path)]
    if not absent:
        return None
    for req in absent:
        if req.absence is AbsenceSemantics.UNEVALUABLE:
            return req
    return absent[0]


def coverage_for(
    registered: RegisteredRule, *, missing: MissingPredicate
) -> CoverageRecord:
    """Classify one rule's coverage for this run."""
    requires = getattr(registered, "requires", ())
    if not requires:
        return CoverageRecord(
            rule_id=registered.id,
            state=CoverageState.UNDECLARED,
            reason=(
                "rule has not declared the inputs it requires, so whether it ran "
                "cannot be established"
            ),
        )

    decisive = _first_absent(requires, missing)
    if decisive is None:
        return CoverageRecord(rule_id=registered.id, state=CoverageState.EVALUATED)

    if decisive.absence is AbsenceSemantics.NOT_APPLICABLE:
        return CoverageRecord(
            rule_id=registered.id,
            state=CoverageState.NOT_APPLICABLE,
            requirement=decisive.path,
            reason="absent by a ratified opt-in",
            basis=decisive.basis,
        )

    default_reason = (
        f"required input {decisive.path!r} is absent or unreadable, so this "
        "rule did not run and its silence is not a pass"
    )
    return CoverageRecord(
        rule_id=registered.id,
        state=CoverageState.UNEVALUABLE,
        requirement=decisive.path,
        # An author-supplied note is more specific than the generic sentence, so
        # it wins -- this is the text a human reads in the coverage report.
        reason=(decisive.note or "").strip() or default_reason,
    )


def census(
    rules: Iterable[RegisteredRule], *, missing: MissingPredicate
) -> tuple[CoverageRecord, ...]:
    """One record per rule, in registry order.

    The reconciliation invariant -- that the returned ids equal the registry's ids
    as a SET -- is asserted in tests rather than here, so a census can still be
    rendered for a filtered subset of rules.
    """
    return tuple(coverage_for(rule, missing=missing) for rule in rules)


#: States that do NOT establish the rule ran. ``NOT_APPLICABLE`` is absent from
#: this set because a ratified opt-in IS a decided outcome; ``EVALUATED`` because
#: the rule ran. Phase 3's fail-closed precondition is that this is empty.
UNCOVERED_STATES = (CoverageState.UNEVALUABLE, CoverageState.UNDECLARED)


def uncovered_rule_ids(records: Iterable[CoverageRecord]) -> tuple[str, ...]:
    """Rule ids whose silence has not been accounted for, in census order."""
    return tuple(r.rule_id for r in records if r.state in UNCOVERED_STATES)
