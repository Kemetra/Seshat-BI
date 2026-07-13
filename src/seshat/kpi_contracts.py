"""Governed project metric-contract authoring for the ``kpi_contracts`` stage.

The helpers deliberately produce committed-artifact shapes and refusal reasons;
they do not add a CLI, a second Decision Store, or a second readiness engine.
Decision validity reuses the existing Decision Store approval predicate. The
source-to-KPI answerability scorecard is a separate concern in
``kpi_answerability``.
"""

from __future__ import annotations

import re
from copy import deepcopy
from dataclasses import dataclass, field
from pathlib import PurePosixPath
from typing import Any, Iterable, Mapping

from .decision_store import approval_is_valid, owner_shape_ok

# Shared by draft (adds it as a required decision type when a binding is PII
# sensitive) and finalize (blocks pass until it is an approved, referenced
# decision). Keeping one constant prevents the two ends from drifting apart.
PII_HANDLING_DECISION_TYPE = "pii_handling"
_DRAFT_BOUNDARY_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "a connection string",
        re.compile(
            r"\b(?:postgres(?:ql)?|mysql|mssql|sqlserver)://|"
            r"\b(?:server|host|password|pwd|uid|user id)\s*=",
            re.IGNORECASE,
        ),
    ),
    (
        "SQL implementation",
        re.compile(
            r"\b(?:select\s+|insert\s+into|update\s+\w+\s+set|"
            r"delete\s+from|create\s+table|merge\s+into)",
            re.IGNORECASE,
        ),
    ),
    (
        "DAX implementation",
        re.compile(
            r"\b(?:calculate|divide|sumx|sum|distinctcount)\s*\(",
            re.IGNORECASE,
        ),
    ),
    (
        "visual or dashboard implementation",
        re.compile(r"\b(?:dashboard|visual|chart|report page)\b", re.IGNORECASE),
    ),
    (
        "a raw PII value",
        re.compile(
            r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b|"
            r"\b\d{3}[- .]\d{2,3}[- .]\d{4}\b|\b\d{3}-\d{2}-\d{4}\b|"
            r"\b(?:email|phone|ssn)\s*=",
        ),
    ),
    (
        "a physical layer binding",
        re.compile(r"\b(?:bronze|silver|gold)\.[a-z_][a-z0-9_]*", re.IGNORECASE),
    ),
)
_MATERIALIZATION_BLOCKER = (
    "physical gold binding is not materialized; next action: materialize and "
    "validate the gold binding"
)


class ContractDraftRefused(ValueError):
    """Raised when the approved-decision precondition is not met."""


def _string_set(values: Iterable[object]) -> set[str]:
    return {value for value in values if isinstance(value, str) and value}


def _repo_relative_reference(reference: object) -> bool:
    if not isinstance(reference, str) or not reference:
        return False
    path = reference.split("#", 1)[0]
    candidate = PurePosixPath(path)
    return bool(path) and not candidate.is_absolute() and ".." not in candidate.parts


def _is_approved(
    decision: Mapping[str, Any], authority: Mapping[str, frozenset[str]] | None
) -> bool:
    if decision.get("status") != "approved":
        return False
    return approval_is_valid(dict(decision), dict(authority) if authority else None)[0]


def _approved_ref(
    records: tuple[Mapping[str, Any], ...],
    decision_type: str,
    authority: Mapping[str, frozenset[str]] | None,
) -> str:
    """Return the id of one approved, valid decision of ``decision_type``."""

    valid = [
        decision
        for decision in records
        if decision.get("decision_type") == decision_type
        and _is_approved(decision, authority)
    ]
    if not valid:
        raise ContractDraftRefused(
            f"missing approved {decision_type} decision required to draft this KPI"
        )
    decision_id = valid[0].get("id")
    if not isinstance(decision_id, str) or not decision_id:
        raise ContractDraftRefused(
            f"approved {decision_type} decision has no usable decision id"
        )
    return decision_id


def _approved_refs(
    decisions: Iterable[Mapping[str, Any]],
    required_types: Iterable[str],
    authority: Mapping[str, frozenset[str]] | None,
) -> list[str]:
    records = tuple(decisions)
    return [
        _approved_ref(records, decision_type, authority)
        for decision_type in sorted(_string_set(required_types))
    ]


def _classification_error(generic_kpi_ref: object, custom: object) -> str | None:
    has_generic = isinstance(generic_kpi_ref, str) and bool(generic_kpi_ref)
    is_custom = custom is True
    if has_generic == is_custom:
        return "exactly one of generic_kpi_ref or custom: true is required"
    return None


def _assert_draft_boundary(*, name: str, formula_intent: str, grain: str) -> None:
    """Keep Checkpoint A declarative and free of downstream implementation."""

    for field_name, value in (
        ("name", name),
        ("formula_intent", formula_intent),
        ("grain", grain),
    ):
        for description, pattern in _DRAFT_BOUNDARY_PATTERNS:
            if pattern.search(value):
                raise ContractDraftRefused(
                    f"{field_name} contains {description}; draft contracts contain "
                    "business intent only"
                )


@dataclass(frozen=True)
class ContractDraftRequest:
    """Every input needed to author one Checkpoint-A project metric contract."""

    name: str
    formula_intent: str
    grain: str
    owner: str
    generic_kpi_ref: str | None
    custom: bool
    registry_ids: tuple[str, ...]
    decisions: tuple[Mapping[str, Any], ...]
    authority: Mapping[str, frozenset[str]] | None
    required_decision_types: tuple[str, ...]
    source_evidence: tuple[str, ...]
    time_additivity: str | None = None
    unit: str | None = None
    pii_sensitive: bool = False
    required_fields: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        for name in (
            "registry_ids",
            "decisions",
            "required_decision_types",
            "source_evidence",
            "required_fields",
        ):
            object.__setattr__(self, name, tuple(getattr(self, name)))


def _registry_resolves(request: ContractDraftRequest) -> bool:
    if not request.generic_kpi_ref:
        return True
    return request.generic_kpi_ref in _string_set(request.registry_ids)


def _validate_classification(request: ContractDraftRequest) -> None:
    classification = _classification_error(request.generic_kpi_ref, request.custom)
    if classification:
        raise ContractDraftRefused(classification)
    if not _registry_resolves(request):
        raise ContractDraftRefused(
            f"generic_kpi_ref {request.generic_kpi_ref!r} does not resolve in the "
            "registry"
        )
    if request.custom and not owner_shape_ok(request.owner):
        raise ContractDraftRefused(
            "custom KPI needs a named eligible owner in 'Name (authority_class)' form"
        )


def _draft_decision_refs(request: ContractDraftRequest) -> list[str]:
    required = request.required_decision_types
    if request.pii_sensitive:
        required = (*required, PII_HANDLING_DECISION_TYPE)
    return _approved_refs(request.decisions, required, request.authority)


def _validate_draft_evidence(request: ContractDraftRequest) -> tuple[str, ...]:
    evidence_refs = request.source_evidence
    if not evidence_refs or not all(
        _repo_relative_reference(ref) for ref in evidence_refs
    ):
        raise ContractDraftRefused(
            "source_evidence must contain repo-relative committed artifact references"
        )
    return evidence_refs


def _validate_draft_intent(request: ContractDraftRequest) -> None:
    fields = (request.name, request.formula_intent, request.grain, request.owner)
    if not all(isinstance(value, str) and value.strip() for value in fields):
        raise ContractDraftRefused(
            "name, formula_intent, grain, and owner are required"
        )
    _assert_draft_boundary(
        name=request.name,
        formula_intent=request.formula_intent,
        grain=request.grain,
    )


def _custom_fields(request: ContractDraftRequest) -> list[str]:
    fields = sorted(_string_set(request.required_fields))
    has_shape = bool(fields) and bool(request.time_additivity) and bool(request.unit)
    if not has_shape:
        raise ContractDraftRefused(
            "custom KPI needs required fields, grain, additivity, and unit"
        )
    return fields


def _draft_optional_fields(request: ContractDraftRequest) -> dict[str, Any]:
    optional: dict[str, Any] = {}
    if request.generic_kpi_ref:
        optional["generic_kpi_ref"] = request.generic_kpi_ref
    if request.time_additivity:
        optional["time_additivity"] = request.time_additivity
    if request.unit:
        optional["unit"] = request.unit
    if request.custom:
        optional["required_fields"] = _custom_fields(request)
    return optional


def draft_project_metric_contract(request: ContractDraftRequest) -> dict[str, Any]:
    """Draft Checkpoint-A provenance without inventing a physical Gold binding."""

    _validate_classification(request)
    decision_refs = _draft_decision_refs(request)
    evidence_refs = _validate_draft_evidence(request)
    _validate_draft_intent(request)

    contract: dict[str, Any] = {
        "name": request.name,
        "formula_intent": request.formula_intent,
        "grain": request.grain,
        "owner": request.owner,
        "binds_to": {
            "gold_table": "<physical gold binding not materialized>",
            "columns": [],
            "pii_sensitive": request.pii_sensitive,
        },
        "readiness": {
            "status": "blocked",
            "evidence": [],
            "blocking_reasons": [_MATERIALIZATION_BLOCKER],
        },
        "ambiguities": [],
        "custom": request.custom,
        "decision_refs": decision_refs,
        "source_evidence": list(evidence_refs),
    }
    contract.update(_draft_optional_fields(request))
    return contract


def build_handoff_intent() -> dict[str, str]:
    """Return downstream ownership intent only; it never contains implementation."""

    return {
        "sql": (
            "Use the approved contract to plan required Gold fields; do not author "
            "SQL here."
        ),
        "dax": (
            "Implement the approved business intent after the semantic-model gate; "
            "do not author DAX here."
        ),
        "python": (
            "Use this contract as reconciliation intent only; do not author Python "
            "here."
        ),
        "big_data": (
            "Use this contract as distributed-processing intent only when scale "
            "evidence requires that route."
        ),
    }


@dataclass(frozen=True)
class FinalizationContext:
    """Resolved evidence and approvals used to complete Checkpoint B."""

    decisions: tuple[Mapping[str, Any], ...]
    authority: Mapping[str, frozenset[str]] | None
    evidence_freshness: Mapping[str, bool]
    named_human_approval: str | None
    by_id: Mapping[str, Mapping[str, Any]] = field(default_factory=dict)

    def __post_init__(self) -> None:
        records = tuple(self.decisions)
        object.__setattr__(self, "decisions", records)
        object.__setattr__(
            self,
            "by_id",
            {
                decision.get("id"): decision
                for decision in records
                if isinstance(decision.get("id"), str)
            },
        )


def _binding_blockers(binds_to: object) -> list[str]:
    if not isinstance(binds_to, dict):
        return ["physical gold binding is not materialized"]
    table = binds_to.get("gold_table")
    if not isinstance(table, str) or not table.startswith("gold."):
        return ["physical gold binding is not materialized"]
    columns = binds_to.get("columns")
    if not isinstance(columns, list) or not _string_set(columns):
        return ["physical gold binding has no bound columns"]
    return []


def _declared_blockers(declared_readiness: object) -> list[str]:
    if not isinstance(declared_readiness, dict):
        return []
    declared = declared_readiness.get("blocking_reasons", [])
    if not isinstance(declared, list) or not all(
        isinstance(blocker, str) for blocker in declared
    ):
        return ["existing blocking_reasons are malformed"]
    return [blocker for blocker in declared if blocker != _MATERIALIZATION_BLOCKER]


def _resolved_decision_blocker(
    reference: object, ctx: FinalizationContext
) -> str | None:
    decision = ctx.by_id.get(reference)
    if decision is None:
        return f"decision {reference!r} is missing"
    if decision.get("status") == "superseded":
        return f"decision {reference!r} is superseded"
    valid, reason = approval_is_valid(
        dict(decision), dict(ctx.authority) if ctx.authority else None
    )
    if decision.get("status") != "approved" or not valid:
        return reason or f"decision {reference!r} is not approved"
    return None


def _decision_blockers(refs: object, ctx: FinalizationContext) -> list[str]:
    if not isinstance(refs, list) or not refs:
        return ["decision_refs are missing or malformed"]
    blockers = [_resolved_decision_blocker(ref, ctx) for ref in refs]
    return [blocker for blocker in blockers if blocker is not None]


def _is_approved_pii_handling(reference: object, ctx: FinalizationContext) -> bool:
    decision = ctx.by_id.get(reference)
    if decision is None:
        return False
    is_pii_handling = decision.get("decision_type") == PII_HANDLING_DECISION_TYPE
    return is_pii_handling and _resolved_decision_blocker(reference, ctx) is None


def _pii_handling_blockers(
    binds_to: object, refs: object, ctx: FinalizationContext
) -> list[str]:
    """Block a PII-sensitive binding until pii_handling is approved and referenced."""

    if not isinstance(binds_to, dict) or binds_to.get("pii_sensitive") is not True:
        return []
    references = refs if isinstance(refs, list) else []
    if any(_is_approved_pii_handling(reference, ctx) for reference in references):
        return []
    return [
        "pii_sensitive binding requires an approved, referenced pii_handling decision"
    ]


def _is_stale_evidence(reference: object, ctx: FinalizationContext) -> bool:
    return (
        not isinstance(reference, str)
        or ctx.evidence_freshness.get(reference) is not True
    )


def _evidence_blockers(evidence: object, ctx: FinalizationContext) -> list[str]:
    if not isinstance(evidence, list) or not evidence:
        return ["source_evidence are missing or malformed"]
    return [
        f"evidence {reference!r} is stale or missing"
        for reference in evidence
        if _is_stale_evidence(reference, ctx)
    ]


def _approval_blockers(ctx: FinalizationContext) -> list[str]:
    if not ctx.named_human_approval or not owner_shape_ok(ctx.named_human_approval):
        return ["named-human approval is missing or malformed"]
    return []


def _finalization_blockers(
    result: Mapping[str, Any], ctx: FinalizationContext
) -> list[str]:
    binds_to = result.get("binds_to")
    refs = result.get("decision_refs")
    blockers: list[str] = []
    classification = _classification_error(
        result.get("generic_kpi_ref"), result.get("custom")
    )
    if classification:
        blockers.append(classification)
    blockers.extend(_binding_blockers(binds_to))
    blockers.extend(_declared_blockers(result.get("readiness")))
    blockers.extend(_decision_blockers(refs, ctx))
    blockers.extend(_pii_handling_blockers(binds_to, refs, ctx))
    blockers.extend(_evidence_blockers(result.get("source_evidence"), ctx))
    blockers.extend(_approval_blockers(ctx))
    return blockers


def finalize_project_metric_contract(
    contract: Mapping[str, Any], ctx: FinalizationContext
) -> dict[str, Any]:
    """Complete Checkpoint B only when every declared precondition is valid."""

    result = deepcopy(dict(contract))
    readiness = result.get("readiness")
    if not isinstance(readiness, dict):
        readiness = {}
        result["readiness"] = readiness

    blockers = _finalization_blockers(result, ctx)
    if blockers:
        readiness.update(
            {
                "status": "blocked",
                "evidence": [],
                "blocking_reasons": sorted(set(blockers)),
            }
        )
        return result

    readiness.update(
        {
            "status": "pass",
            "evidence": [f"approved by {ctx.named_human_approval}"],
            "blocking_reasons": [],
        }
    )
    result["handoff_intent"] = build_handoff_intent()
    return result
