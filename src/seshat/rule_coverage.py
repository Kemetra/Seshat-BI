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

Four declaration forms exist because the 80 registered rules select their input
four different ways, measured rule by rule:

* one artifact (``path=``) -- e.g. a single manifest a rule opens;
* a CLASS of tracked files (``pattern=``) -- most rules scan a corpus;
* ANY of several classes (``any_of=``) -- a rule whose corpus is an alternation
  (``.tmdl`` OR ``.pbir`` OR ``.json`` OR ``.pbism``; any of three decision-store
  files). Declaring one arm alone reports a rule that ran as unevaluable; declaring
  the arms as separate requirements is worse, because requirements are ANDed;
* an invocation field (``context=``) -- P2 judges commit subjects handed to the
  run, which are not a tracked file at all.

:class:`ReportsItsOwnAbsence` is the fifth, non-``Requirement`` case: a rule with
no silent-skip path, because it emits a finding when its input is missing. That
claim is verified against an empty repository by
``tests/unit/test_rule_coverage_declarations.py``, not taken on the author's word.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Callable, Iterable, TypedDict

from .core import RegisteredRule

#: fnmatch pattern for the committed-test-fixture exemption ``core.is_test_path``
#: applies. Almost every file-scanning rule skips ``tests/`` (fixtures carry
#: deliberately non-conforming content), so a corpus declaration that counted them
#: would report ``evaluated`` for a rule whose iterator skipped every match --
#: strictly worse than no declaration.
TEST_FIXTURES = "tests/*"


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


class ContextInput(str, Enum):
    """An input that arrives on the INVOCATION, not as a file in the tree.

    The rule-coverage question ("did this rule actually run?") is the same, but
    the presence test is not a filesystem lookup: it asks what the caller passed.
    Kept as a closed enum rather than free text so an unknown value fails loud in
    the resolver instead of silently resolving to "present".

    ``COMMIT_SUBJECTS`` is P2's input. A bare ``retail check`` on a repo with no
    HEAD, and no ``--commit-msg-file`` / ``--commit-range``, gives P2 no subject
    to judge -- it returns no findings while having validated nothing.
    """

    COMMIT_SUBJECTS = "commit subjects (--commit-msg-file / --commit-range / HEAD)"


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

    A requirement names EXACTLY ONE form: ``path`` (one artifact), ``pattern``
    (a class of tracked files, an fnmatch glob), ``any_of`` (a group of leaf
    requirements, satisfied when ANY one of them is present) or ``context`` (an
    invocation field). ``exclude`` narrows a ``pattern`` by the same fnmatch
    matching, so a declaration can mirror the exemptions its rule's own iterator
    applies (``tests/`` fixtures, a blank template) instead of over-crediting.
    """

    path: str | None = None
    pattern: str | None = None
    any_of: tuple["Requirement", ...] = ()
    context: ContextInput | None = None
    exclude: tuple[str, ...] = ()
    absence: AbsenceSemantics = AbsenceSemantics.UNEVALUABLE
    basis: str | None = None
    note: str | None = None

    @property
    def target(self) -> str:
        """The declared input, for display: the artifact, glob, group or field."""
        if self.any_of:
            return "any of: " + ", ".join(alt.target for alt in self.any_of)
        if self.context is not None:
            return self.context.value
        return self.path or self.pattern or ""

    def __post_init__(self) -> None:
        self._validate_form()
        self._validate_group()
        self._validate_exclude()
        # Branches on the absence semantics rather than testing compound
        # conditions, so each rule about `basis` reads on its own line.
        if self.absence is AbsenceSemantics.NOT_APPLICABLE:
            if not (self.basis or "").strip():
                raise ValueError(
                    f"requirement {self.target!r}: absence=not-applicable claims "
                    "a ratified opt-in and so requires a basis naming the ruling "
                    "that authorized it (an agent may not self-grant one)"
                )
        elif self.basis is not None:
            raise ValueError(
                f"requirement {self.target!r}: basis cites the human ruling behind "
                "absence=not-applicable and is meaningful only there; to explain "
                "why this input is required, use note="
            )

    def _declared_forms(self) -> tuple[str, ...]:
        return tuple(
            name
            for name in ("path", "pattern", "any_of", "context")
            if getattr(self, name)
        )

    def _validate_form(self) -> None:
        """Exactly one form. None would silently match nothing; two is ambiguous."""
        forms = self._declared_forms()
        if not forms:
            raise ValueError(
                "requirement declares no input: set path= for one artifact, "
                "pattern= for a class of tracked files, any_of= for an "
                "alternation of those, or context= for an invocation field"
            )
        if len(forms) > 1:
            raise ValueError(
                f"requirement declares {' + '.join(forms)}: set exactly ONE form "
                "-- a requirement names one artifact, one class of files, one "
                "alternation of those, or one invocation field"
            )

    def _validate_group(self) -> None:
        """An any-of group holds >= 2 plain alternatives that carry no semantics.

        A single-arm group is a plain requirement written the long way. A member
        carrying its own ``absence`` / ``basis`` / ``note`` would be silently
        ignored -- the GROUP decides the state -- and a silently ignored ``basis``
        is exactly the false-authority failure the basis gate exists to prevent.
        """
        if not self.any_of:
            return
        if len(self.any_of) < 2:
            raise ValueError(
                "any_of declares a single alternative: use path= or pattern= "
                "directly, or name the other alternatives"
            )
        for alt in self.any_of:
            if alt.any_of or alt.context is not None:
                raise ValueError(
                    f"any_of alternative {alt.target!r} must be a plain path= or "
                    "pattern= requirement (groups do not nest)"
                )
            if alt.basis is not None or alt.note is not None:
                raise ValueError(
                    f"any_of alternative {alt.target!r} carries basis/note, which "
                    "the group would ignore: put them on the group itself"
                )
            if alt.absence is not AbsenceSemantics.UNEVALUABLE:
                raise ValueError(
                    f"any_of alternative {alt.target!r} sets absence, which the "
                    "group would ignore: declare it on the group itself"
                )

    def _validate_exclude(self) -> None:
        """``exclude`` narrows a glob; on any other form it would be inert.

        Silently accepting it on a ``path=`` requirement would let a declaration
        LOOK like it mirrors its rule's template/fixture exemption while doing
        nothing -- so it is a construction error, and a group's alternatives carry
        their own (see :func:`any_tracked_file`).
        """
        if self.exclude and self.pattern is None:
            raise ValueError(
                f"requirement {self.target!r}: exclude= narrows a pattern= glob "
                "and is inert on any other form (a group's alternatives carry "
                "their own exclude)"
            )


def any_tracked_file(
    *patterns: str,
    exclude: tuple[str, ...] = (),
    note: str | None = None,
    absence: AbsenceSemantics = AbsenceSemantics.UNEVALUABLE,
    basis: str | None = None,
) -> Requirement:
    """A requirement satisfied by any tracked file matching ANY of ``patterns``.

    The ergonomic form of the group: it applies one ``exclude`` to every
    alternative, so a rule whose corpus is an alternation (four TMDL/PBIR
    suffixes; three decision-store paths) declares the whole corpus in one
    expression and cannot leave the fixture exemption off one arm.
    """
    return Requirement(
        any_of=tuple(Requirement(pattern=p, exclude=exclude) for p in patterns),
        note=note,
        absence=absence,
        basis=basis,
    )


@dataclass(frozen=True)
class ReportsItsOwnAbsence:
    """Declares that a rule has NO silent-skip path: it SAYS SO when input is gone.

    Some rules never go quiet on absent input -- they report it. G1 emits one
    ERROR per missing ``.gitignore`` entry, G2 emits ``no PBIP project present``,
    and every ``KIT_SELF`` rule ERRORs on the kit manifest it cannot find. Their
    silence is therefore already unambiguous, and they cannot be expressed as a
    ``Requirement``: there is no input whose absence would stop them running.

    This is the one declaration that credits a rule without naming an input, so it
    is the one an author could abuse to manufacture coverage. What keeps it honest
    is that the claim is machine-checkable and IS checked:
    ``tests/unit/test_rule_coverage_declarations.py`` runs every rule declaring
    this form against an empty repository and asserts it emits at least one
    finding. Declaring it for a rule that goes quiet turns the suite red rather
    than crediting the rule.

    ``note`` is mandatory and records WHAT the rule says instead of going silent.
    It is not a ``basis``: it claims no human authority, only observable behavior.
    """

    note: str

    def __post_init__(self) -> None:
        if not self.note.strip():
            raise ValueError(
                "ReportsItsOwnAbsence requires a note recording WHAT the rule "
                "reports instead of going silent (it is the claim a test verifies)"
            )


#: What a rule may declare about its inputs. ``Requirement`` names an input;
#: ``ReportsItsOwnAbsence`` states there is no input to name.
Declaration = Requirement | ReportsItsOwnAbsence


def validate_declarations(
    rule_id: str, declarations: tuple[Declaration, ...]
) -> tuple[Declaration, ...]:
    """Reject a contradictory declaration set at ``@register`` time, not at census.

    Mixing ``ReportsItsOwnAbsence`` with a ``Requirement`` asserts both "no input
    can stop this rule running" and "this input can". One of the two is wrong, and
    since the self-reporting form wins in :func:`coverage_for`, accepting the mix
    would let a real requirement be silently discarded.
    """
    self_reporting = [d for d in declarations if isinstance(d, ReportsItsOwnAbsence)]
    if self_reporting and len(declarations) > 1:
        raise ValueError(
            f"rule {rule_id}: ReportsItsOwnAbsence says no absent input can stop "
            "this rule, so it must be the ONLY declaration -- drop it, or drop the "
            "requirements it contradicts"
        )
    return declarations


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


# A caller-supplied "is this input absent?" predicate. It receives a LEAF
# Requirement -- one path, one glob or one invocation field -- never a group: the
# alternation semantics are resolved here (see `_requirement_absent`) so every
# resolver agrees on them. Keeping presence out of this module is what makes every
# state reachable in a unit test with no tmpdir.
MissingPredicate = Callable[[Requirement], bool]


def _requirement_absent(requirement: Requirement, missing: MissingPredicate) -> bool:
    """Is the input this requirement names absent?

    An any-of group is absent only when EVERY alternative is: the rule selects its
    corpus by alternation, so one present arm means it ran. This is why the group
    form exists at all -- requirements are ANDed, so declaring the arms separately
    would report a rule that ran fine as unevaluable.
    """
    if requirement.any_of:
        return all(missing(alt) for alt in requirement.any_of)
    return missing(requirement)


def _first_absent(
    requires: tuple[Requirement, ...], missing: MissingPredicate
) -> Requirement | None:
    """The absent requirement that decides the state.

    An absent ``UNEVALUABLE`` requirement outranks an absent ``NOT_APPLICABLE``
    one: if any input the rule genuinely needed is gone, the rule did not run,
    and a ratified opt-in elsewhere must not launder that into coverage.
    """
    absent = [req for req in requires if _requirement_absent(req, missing)]
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

    for declaration in requires:
        if isinstance(declaration, ReportsItsOwnAbsence):
            # No input can silence this rule, so there is nothing to resolve --
            # it ran, and the note records what it says when input is missing.
            return CoverageRecord(
                rule_id=registered.id,
                state=CoverageState.EVALUATED,
                reason=declaration.note,
            )

    decisive = _first_absent(
        tuple(d for d in requires if isinstance(d, Requirement)), missing
    )
    if decisive is None:
        return CoverageRecord(rule_id=registered.id, state=CoverageState.EVALUATED)

    if decisive.absence is AbsenceSemantics.NOT_APPLICABLE:
        return CoverageRecord(
            rule_id=registered.id,
            state=CoverageState.NOT_APPLICABLE,
            requirement=decisive.target,
            reason="absent by a ratified opt-in",
            basis=decisive.basis,
        )

    default_reason = (
        f"required input {decisive.target!r} is absent, empty or unreadable, so "
        "this rule did not run and its silence is not a pass"
    )
    return CoverageRecord(
        rule_id=registered.id,
        state=CoverageState.UNEVALUABLE,
        requirement=decisive.target,
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
