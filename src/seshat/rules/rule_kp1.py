"""KP1 -- Project KPI provenance is structurally traceable.

KP1 validates optional provenance fields when a project metric contract adopts
them. Legacy contracts with no provenance fields remain valid by design.
Decision approval, evidence freshness, and readiness remain owned by the existing
Decision Store gate rather than this static rule.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any

from ..core import Finding, RuleContext, Severity, is_test_path
from ..registry import register

REGISTRY_REL = "skills/retail-kpi-knowledge/registry.yaml"
_METRIC_RE = re.compile(r"^mappings/[^/]+/metrics/[^/]+\.ya?ml$")
_EVIDENCE_RE = re.compile(r"^mappings/[^/]+/(?:source-map\.ya?ml|source-profile\.md)$")
_PROVENANCE_FIELDS = frozenset(
    {"generic_kpi_ref", "custom", "decision_refs", "source_evidence"}
)


@dataclass(frozen=True)
class RegistryLookup:
    """Resolved registry ids, or the reason the registry could not be read."""

    ids: frozenset[str] | None
    error: str | None


def _finding(rel: str, message: str) -> Finding:
    return Finding("KP1", Severity.ERROR, message, rel)


def _contracts(ctx: RuleContext) -> list[str]:
    return [
        path
        for path in ctx.tracked_files
        if _METRIC_RE.match(path) and not is_test_path(path)
    ]


def _load_yaml(ctx: RuleContext, rel: str) -> tuple[dict[str, Any] | None, str | None]:
    import yaml

    try:
        raw = (ctx.repo_root / rel).read_text(encoding="utf-8-sig")
        loaded = yaml.safe_load(raw)
    except (OSError, UnicodeDecodeError, yaml.YAMLError) as exc:
        return None, str(exc)
    return (
        (loaded, None) if isinstance(loaded, dict) else (None, "YAML must be a mapping")
    )


def _registry_lookup(ctx: RuleContext) -> RegistryLookup:
    if REGISTRY_REL not in ctx.tracked_files:
        return RegistryLookup(None, "generic KPI registry is not tracked")
    registry, error = _load_yaml(ctx, REGISTRY_REL)
    if registry is None:
        return RegistryLookup(None, f"generic KPI registry cannot be read: {error}")
    entries = registry.get("entries")
    if not isinstance(entries, list):
        return RegistryLookup(None, "generic KPI registry entries are malformed")
    ids = {entry.get("id") for entry in entries if isinstance(entry, dict)}
    return RegistryLookup(
        frozenset(entry_id for entry_id in ids if isinstance(entry_id, str)), None
    )


def _refs(value: object) -> list[str] | None:
    if not isinstance(value, list) or not value:
        return None
    if not all(isinstance(item, str) and item for item in value):
        return None
    return value


def _source_ref_resolves(reference: str, tracked: set[str]) -> bool:
    """Accept only committed source-map / source-profile evidence artifacts.

    A metric contract or any other ``mappings/`` file is not source evidence; the
    provenance chain must point at the source-map or source-profile it derives from.
    """

    path = reference.split("#", 1)[0]
    return bool(_EVIDENCE_RE.match(path)) and path in tracked


def _classification_findings(
    rel: str, contract: dict[str, Any], registry: RegistryLookup
) -> list[Finding]:
    generic_ref = contract.get("generic_kpi_ref")
    custom = contract.get("custom")
    has_generic = isinstance(generic_ref, str) and bool(generic_ref)
    findings: list[Finding] = []
    if "generic_kpi_ref" in contract and not has_generic:
        findings.append(_finding(rel, "generic_kpi_ref must be a non-empty string"))
    if "custom" in contract and not isinstance(custom, bool):
        findings.append(_finding(rel, "custom must be a boolean when present"))
    if has_generic == (custom is True):
        findings.append(
            _finding(rel, "exactly one of generic_kpi_ref or custom: true is required")
        )
    if has_generic:
        findings.extend(_registry_findings(rel, generic_ref, registry))
    return findings


def _registry_findings(
    rel: str, generic_ref: object, registry: RegistryLookup
) -> list[Finding]:
    if registry.error:
        return [_finding(rel, registry.error)]
    if registry.ids is not None and generic_ref not in registry.ids:
        return [_finding(rel, f"generic_kpi_ref {generic_ref!r} does not resolve")]
    return []


def _reference_findings(
    rel: str, contract: dict[str, Any], tracked: set[str]
) -> list[Finding]:
    findings: list[Finding] = []
    if _refs(contract.get("decision_refs")) is None:
        findings.append(
            _finding(rel, "decision_refs must be a non-empty list of decision ids")
        )
    evidence = _refs(contract.get("source_evidence"))
    if evidence is None:
        findings.append(
            _finding(
                rel, "source_evidence must be a non-empty list of repo-relative refs"
            )
        )
        return findings
    findings.extend(
        _finding(rel, f"source_evidence ref {reference!r} does not resolve")
        for reference in evidence
        if not _source_ref_resolves(reference, tracked)
    )
    return findings


def _contract_findings(
    rel: str, contract: dict[str, Any], registry: RegistryLookup, tracked: set[str]
) -> list[Finding]:
    if not (_PROVENANCE_FIELDS & set(contract)):
        return []
    return [
        *_classification_findings(rel, contract, registry),
        *_reference_findings(rel, contract, tracked),
    ]


@register("KP1", "Project KPI provenance is structurally traceable")
def check_kp1(ctx: RuleContext) -> Iterable[Finding]:
    """Check provenance structure only for contracts that opt into the fields."""

    registry = _registry_lookup(ctx)
    tracked = set(ctx.tracked_files)
    findings: list[Finding] = []
    for rel in sorted(_contracts(ctx)):
        contract, error = _load_yaml(ctx, rel)
        if contract is None:
            findings.append(
                _finding(rel, f"could not read/parse metric contract: {error}")
            )
            continue
        findings.extend(_contract_findings(rel, contract, registry, tracked))
    return findings
