"""Source-to-KPI answerability: the fail-closed coverage scorecard.

These helpers decide, for one generic KPI in one scope, whether committed source
evidence and approved decisions make it answerable -- and never fabricate a
mapping, a confidence score, or a coverage claim. Contract authoring lives in
``kpi_contracts``; this module shares no state with it.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Iterable, Mapping

COVERAGE_STATUSES: tuple[str, ...] = (
    "Covered",
    "Blocked -- missing field",
    "Blocked -- needs business definition",
    "Planned",
    "Out of scope",
)

# One check produces at most one row; ``None`` means "this rule did not fire".
RowBuilder = Callable[[str, Iterable[str], str], "KpiAnswerabilityRow"]
AnswerabilityCheck = Callable[
    [Mapping[str, Any], "AnswerabilityInputs", RowBuilder],
    "KpiAnswerabilityRow | None",
]


def _string_set(values: Iterable[object]) -> set[str]:
    return {value for value in values if isinstance(value, str) and value}


def _entry_strings(entry: Mapping[str, Any], key: str) -> set[str]:
    value = entry.get(key, [])
    return _string_set(value) if isinstance(value, list) else set()


@dataclass(frozen=True)
class KpiAnswerabilityRow:
    """One evidence-bound, non-scored source-to-KPI answerability result."""

    scope: str
    kpi: str
    status: str
    blockers: tuple[str, ...]
    evidence: tuple[str, ...]
    next_action: str
    knowledge_contract_ref: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "scope": self.scope,
            "kpi": self.kpi,
            "status": self.status,
            "blockers": list(self.blockers),
            "evidence": list(self.evidence),
            "next_action": self.next_action,
        }


@dataclass(frozen=True)
class AnswerabilityInputs:
    """Resolved, committed context for one generic KPI's answerability check.

    ``mapped_concepts`` means a committed source-map has explicitly established
    the logical concept. A similarly named physical column belongs in
    ``lookalike_concepts`` and is never treated as a mapping. Iterable inputs are
    normalized to frozensets so the fail-closed checks can use set arithmetic.
    """

    scope: str
    available_source_roles: frozenset[str] = field(default_factory=frozenset)
    mapped_concepts: frozenset[str] = field(default_factory=frozenset)
    approved_decision_types: frozenset[str] = field(default_factory=frozenset)
    evidence: tuple[str, ...] = ()
    evidence_is_fresh: bool = False
    domain_served: bool = False
    lookalike_concepts: frozenset[str] = field(default_factory=frozenset)

    def __post_init__(self) -> None:
        for name in (
            "available_source_roles",
            "mapped_concepts",
            "approved_decision_types",
            "lookalike_concepts",
        ):
            object.__setattr__(self, name, frozenset(_string_set(getattr(self, name))))
        object.__setattr__(self, "evidence", tuple(_string_set(self.evidence)))


def _make_row(entry: Mapping[str, Any], inputs: AnswerabilityInputs) -> RowBuilder:
    """Return a row builder bound to the entry, scope, and evidence for a check."""

    kpi = entry.get("id")
    contract_ref = entry.get("knowledge_contract_ref")
    if not isinstance(kpi, str) or not isinstance(contract_ref, str):
        raise ValueError("registry entry needs string id and knowledge_contract_ref")

    def row(
        status: str, blockers: Iterable[str], next_action: str
    ) -> KpiAnswerabilityRow:
        if status not in COVERAGE_STATUSES:
            raise ValueError(f"unknown answerability status {status!r}")
        return KpiAnswerabilityRow(
            scope=inputs.scope,
            kpi=kpi,
            status=status,
            blockers=tuple(blockers),
            evidence=inputs.evidence,
            next_action=next_action,
            knowledge_contract_ref=contract_ref,
        )

    return row


def _out_of_scope_row(
    entry: Mapping[str, Any], inputs: AnswerabilityInputs, row: RowBuilder
) -> KpiAnswerabilityRow | None:
    if inputs.domain_served:
        return None
    return row(
        "Out of scope",
        ("the source roles cannot serve this KPI domain",),
        "select a source scope that contains the required business domain",
    )


def _missing_field_row(
    missing: set[str], blocker_label: str, next_action: str, row: RowBuilder
) -> KpiAnswerabilityRow | None:
    if not missing:
        return None
    return row(
        "Blocked -- missing field",
        (f"{blocker_label}: {', '.join(sorted(missing))}",),
        next_action,
    )


def _missing_role_row(
    entry: Mapping[str, Any], inputs: AnswerabilityInputs, row: RowBuilder
) -> KpiAnswerabilityRow | None:
    return _missing_field_row(
        _entry_strings(entry, "source_roles") - inputs.available_source_roles,
        "missing source roles",
        "obtain committed mapping evidence for every named source role",
        row,
    )


def _lookalike_row(
    entry: Mapping[str, Any], inputs: AnswerabilityInputs, row: RowBuilder
) -> KpiAnswerabilityRow | None:
    lookalikes = _entry_strings(entry, "required_concepts") & inputs.lookalike_concepts
    if not lookalikes:
        return None
    return row(
        "Blocked -- needs business definition",
        (
            "lookalike fields are not approved mappings for: "
            + ", ".join(sorted(lookalikes)),
        ),
        "request an approved kpi_definition for the ambiguous concepts",
    )


def _missing_concept_row(
    entry: Mapping[str, Any], inputs: AnswerabilityInputs, row: RowBuilder
) -> KpiAnswerabilityRow | None:
    return _missing_field_row(
        _entry_strings(entry, "required_concepts") - inputs.mapped_concepts,
        "missing mapped concepts",
        "map the missing logical concepts in committed source evidence",
        row,
    )


def _missing_decision_row(
    entry: Mapping[str, Any], inputs: AnswerabilityInputs, row: RowBuilder
) -> KpiAnswerabilityRow | None:
    missing = (
        _entry_strings(entry, "required_decision_types")
        - inputs.approved_decision_types
    )
    if not missing:
        return None
    return row(
        "Blocked -- needs business definition",
        ("missing approved decisions: " + ", ".join(sorted(missing)),),
        "request the missing approved business decision",
    )


def _evidence_row(
    entry: Mapping[str, Any], inputs: AnswerabilityInputs, row: RowBuilder
) -> KpiAnswerabilityRow | None:
    if inputs.evidence and inputs.evidence_is_fresh:
        return None
    reason = (
        "source or mapping evidence is missing"
        if not inputs.evidence
        else "source or mapping evidence is stale"
    )
    return row(
        "Blocked -- missing field",
        (reason,),
        "refresh and commit source-profile and source-map evidence",
    )


# The six fail-closed rules, in their declared precedence order.
_SEEDED_CHECKS: tuple[AnswerabilityCheck, ...] = (
    _out_of_scope_row,
    _missing_role_row,
    _lookalike_row,
    _missing_concept_row,
    _missing_decision_row,
    _evidence_row,
)


def _planned_row(
    entry: Mapping[str, Any], row: RowBuilder
) -> KpiAnswerabilityRow | None:
    if entry.get("lifecycle") != "planned":
        return None
    blockers = _entry_strings(entry, "blockers") or {"generic KPI is planned"}
    return row(
        "Planned",
        sorted(blockers),
        "follow the registry blockers; do not fabricate a project contract",
    )


def derive_answerability(
    entry: Mapping[str, Any], inputs: AnswerabilityInputs
) -> KpiAnswerabilityRow:
    """Apply the fail-closed answerability rules in their declared order."""

    row = _make_row(entry, inputs)
    planned = _planned_row(entry, row)
    if planned is not None:
        return planned
    if entry.get("lifecycle") != "seeded":
        raise ValueError(
            f"registry entry has unsupported lifecycle {entry.get('lifecycle')!r}"
        )

    for check in _SEEDED_CHECKS:
        found = check(entry, inputs, row)
        if found is not None:
            return found

    return row(
        "Covered",
        (),
        "draft the project metric contract from approved decisions",
    )


def _cell(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ")


def render_answerability_artifact(
    scope: str, rows: Iterable[KpiAnswerabilityRow]
) -> str:
    """Render the SL1-compatible scorecard shape plus evidence/next-action rows."""

    ordered = tuple(rows)
    lines = [
        "# KPI Answerability",
        "",
        f"> Table: {_cell(scope)}",
        "",
        "| KPI | Contract | Coverage status | Blocker |",
        "|-----|----------|-----------------|---------|",
    ]
    for row in ordered:
        contract = row.knowledge_contract_ref if row.status == "Covered" else "--"
        blockers = "; ".join(row.blockers) or "--"
        lines.append(
            "| "
            f"{_cell(row.kpi)} | {_cell(contract)} | {_cell(row.status)} | "
            f"{_cell(blockers)} |"
        )
    lines += [
        "",
        "## Evidence and next actions",
        "",
        "| KPI | Evidence | Next action |",
        "|-----|----------|-------------|",
    ]
    for row in ordered:
        evidence = "; ".join(row.evidence) or "--"
        lines.append(
            f"| {_cell(row.kpi)} | {_cell(evidence)} | {_cell(row.next_action)} |"
        )
    return "\n".join(lines) + "\n"
