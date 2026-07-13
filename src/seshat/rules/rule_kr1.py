"""KR1 -- Generic KPI registry structure and client-free boundary.

This rule checks the product-level registry only. It validates identity,
traceability, lifecycle, and client-free structure; it does not decide whether a
KPI is meaningful, answerable, or ready.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from typing import Any

from ..core import Finding, RuleContext, RuleTier, Severity
from ..decision_store import CRITICAL_DECISION_TYPES
from ..registry import register

REGISTRY_REL = "skills/retail-kpi-knowledge/registry.yaml"
_ID_RE = re.compile(r"^KPI-MC-\d{2,}$")
_SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_METRIC_KINDS = frozenset(
    {
        "base_metric",
        "derived_metric",
        "ratio",
        "time_transform",
        "snapshot",
        "quality_metric",
        "analytical_slice",
    }
)
_LIFECYCLES = frozenset({"seeded", "planned"})
_REQUIRED_FIELDS = frozenset(
    {
        "id",
        "slug",
        "canonical_name",
        "aliases",
        "domain",
        "metric_kind",
        "lifecycle",
        "knowledge_contract_ref",
        "derives_from",
        "required_concepts",
        "required_decision_types",
        "source_roles",
    }
)
_BINDING_KEYS = frozenset({"binds_to", "gold_table", "columns"})
_FORBIDDEN_TOKENS = (
    "c086",
    "retail_store_sales",
    "kaggle",
    "gold.fct_sales_rss",
    "total_spent",
    "quantity",
    "transaction_id",
    "discount_applied",
    "customer_id",
    "12575",
    "50.37",
    "q1",
    "q2",
    "q3",
    "q4",
    "ahmed shaaban",
    "billing code",
    "billing codes",
    "billing_code",
    "insurance pii",
)
_PHYSICAL_BINDING_RE = re.compile(r"\b(?:bronze|silver|gold)\.[a-z_][a-z0-9_]*")


def _finding(locator: str, message: str) -> Finding:
    return Finding("KR1", Severity.ERROR, message, locator)


def _is_non_empty_string_list(value: object) -> bool:
    return isinstance(value, list) and all(
        isinstance(item, str) and item for item in value
    )


def _strings(value: object) -> list[str] | None:
    return value if _is_non_empty_string_list(value) else None


def _walk_mapping(mapping: dict, *, include_values: bool) -> Iterable[str]:
    for key, nested in mapping.items():
        if isinstance(key, str):
            yield key
        yield from _walk(nested, include_values=include_values)


def _walk(value: object, *, include_values: bool) -> Iterable[str]:
    """Yield every mapping key, and every string value when ``include_values``."""

    if isinstance(value, str) and include_values:
        yield value
    elif isinstance(value, dict):
        yield from _walk_mapping(value, include_values=include_values)
    elif isinstance(value, list):
        for nested in value:
            yield from _walk(nested, include_values=include_values)


def _walk_strings(value: object) -> Iterable[str]:
    return _walk(value, include_values=True)


def _walk_mapping_keys(value: object) -> Iterable[str]:
    return _walk(value, include_values=False)


def _contains_exact_physical_token(text: str, token: str) -> bool:
    """Match a physical identifier without rejecting a logical lookalike.

    ``transaction_identifier`` is a valid generic logical concept;
    ``transaction_id`` is a worked-example physical column that must not be
    represented in the registry.
    """

    return bool(
        re.search(
            rf"(?<![a-z0-9_-]){re.escape(token)}(?![a-z0-9_-])",
            text.casefold(),
        )
    )


def _registry_entries(ctx: RuleContext) -> tuple[dict[str, Any] | None, list[Finding]]:
    if REGISTRY_REL not in ctx.tracked_files:
        return None, [_finding(REGISTRY_REL, "generic KPI registry is missing")]
    import yaml

    try:
        raw = (ctx.repo_root / REGISTRY_REL).read_text(encoding="utf-8-sig")
        loaded = yaml.safe_load(raw)
    except (OSError, UnicodeDecodeError, yaml.YAMLError) as exc:
        return None, [_finding(REGISTRY_REL, f"could not read/parse registry: {exc}")]
    if not isinstance(loaded, dict):
        return None, [_finding(REGISTRY_REL, "registry must be a YAML mapping")]
    return loaded, []


def _binding_key_findings(data: dict[str, Any]) -> list[Finding]:
    return [
        _finding(REGISTRY_REL, f"registry contains project binding key {key!r}")
        for key in _walk_mapping_keys(data)
        if key in _BINDING_KEYS
    ]


def _string_leakage_findings(text: str) -> list[Finding]:
    lowered = text.casefold()
    findings: list[Finding] = []
    if _PHYSICAL_BINDING_RE.search(lowered):
        findings.append(
            _finding(REGISTRY_REL, "registry contains a physical layer binding")
        )
    findings.extend(
        _finding(
            REGISTRY_REL,
            f"registry contains worked-example or client token {token!r}",
        )
        for token in _FORBIDDEN_TOKENS
        if _contains_exact_physical_token(lowered, token)
    )
    return findings


def _registry_leakage(data: dict[str, Any]) -> list[Finding]:
    findings = _binding_key_findings(data)
    for text in _walk_strings(data):
        findings.extend(_string_leakage_findings(text))
    return findings


def _register_id(
    entry: dict[str, Any], locator: str, ids: set[str]
) -> tuple[str | None, list[Finding]]:
    entry_id = entry.get("id")
    if not isinstance(entry_id, str) or not _ID_RE.fullmatch(entry_id):
        return None, [_finding(locator, "id must match KPI-MC-NN")]
    if entry_id in ids:
        return None, [_finding(locator, f"duplicate registry id {entry_id!r}")]
    ids.add(entry_id)
    return entry_id, []


def _identity_findings(entry: dict[str, Any], locator: str) -> list[Finding]:
    findings: list[Finding] = []
    slug = entry.get("slug")
    if not isinstance(slug, str) or not _SLUG_RE.fullmatch(slug):
        findings.append(_finding(locator, "slug must be lowercase kebab-case"))
    canonical = entry.get("canonical_name")
    if not isinstance(canonical, str) or not canonical.strip():
        findings.append(_finding(locator, "canonical_name must be a non-empty string"))
    return findings


def _list_field_findings(entry: dict[str, Any], locator: str) -> list[Finding]:
    return [
        _finding(locator, f"{name} must be a list of non-empty strings")
        for name in ("aliases", "derives_from", "required_concepts", "source_roles")
        if _strings(entry.get(name)) is None
    ]


def _decision_type_findings(entry: dict[str, Any], locator: str) -> list[Finding]:
    decisions = _strings(entry.get("required_decision_types"))
    if decisions is None:
        return [_finding(locator, "required_decision_types must be a string list")]
    unknown = sorted(set(decisions) - CRITICAL_DECISION_TYPES)
    if unknown:
        return [_finding(locator, f"unknown decision types {unknown}")]
    return []


def _taxonomy_findings(entry: dict[str, Any], locator: str) -> list[Finding]:
    findings: list[Finding] = []
    if entry.get("metric_kind") not in _METRIC_KINDS:
        findings.append(_finding(locator, "metric_kind is outside the closed taxonomy"))
    lifecycle = entry.get("lifecycle")
    if lifecycle not in _LIFECYCLES:
        findings.append(_finding(locator, "lifecycle must be seeded or planned"))
    elif lifecycle == "planned" and not _strings(entry.get("blockers")):
        findings.append(_finding(locator, "planned entry must name concrete blockers"))
    return findings


def _contract_ref_findings(
    entry: dict[str, Any], locator: str, tracked: set[str]
) -> list[Finding]:
    reference = entry.get("knowledge_contract_ref")
    if not isinstance(reference, str) or reference not in tracked:
        return [
            _finding(
                locator, "knowledge_contract_ref does not resolve to a tracked file"
            )
        ]
    return []


def _validate_entry(
    entry: object, index: int, ids: set[str], tracked: set[str]
) -> tuple[str | None, list[Finding]]:
    locator = f"{REGISTRY_REL}:entries[{index}]"
    if not isinstance(entry, dict):
        return None, [_finding(locator, "registry entry must be a mapping")]
    missing = sorted(_REQUIRED_FIELDS - set(entry))
    if missing:
        return None, [
            _finding(locator, f"registry entry missing required fields {missing}")
        ]

    entry_id, findings = _register_id(entry, locator, ids)
    findings.extend(_identity_findings(entry, locator))
    findings.extend(_list_field_findings(entry, locator))
    findings.extend(_decision_type_findings(entry, locator))
    findings.extend(_taxonomy_findings(entry, locator))
    findings.extend(_contract_ref_findings(entry, locator, tracked))
    return entry_id, findings


def _canonical_names(entries: list[dict[str, Any]]) -> set[str]:
    return {
        entry.get("canonical_name").casefold()
        for entry in entries
        if isinstance(entry.get("canonical_name"), str)
    }


def _duplicate_finding(
    value: object, seen: set[str], locator: str, message: str
) -> list[Finding]:
    if not isinstance(value, str):
        return []
    key = value.casefold()
    findings = [_finding(locator, message)] if key in seen else []
    seen.add(key)
    return findings


def _alias_collision_findings(
    entry: dict[str, Any], locator: str, canonical_names: set[str]
) -> list[Finding]:
    return [
        _finding(locator, f"alias {alias!r} collides with a canonical_name")
        for alias in _strings(entry.get("aliases")) or []
        if alias.casefold() in canonical_names
    ]


def _derives_from_findings(
    entry: dict[str, Any], locator: str, ids: set[str]
) -> list[Finding]:
    missing = sorted(set(_strings(entry.get("derives_from")) or []) - ids)
    if missing:
        return [_finding(locator, f"derives_from has unresolved ids {missing}")]
    return []


def _validate_cross_entry(
    entries: list[dict[str, Any]], ids: set[str]
) -> list[Finding]:
    findings: list[Finding] = []
    seen_slugs: set[str] = set()
    seen_names: set[str] = set()
    canonical_names = _canonical_names(entries)
    for index, entry in enumerate(entries):
        locator = f"{REGISTRY_REL}:entries[{index}]"
        findings.extend(
            _duplicate_finding(
                entry.get("slug"),
                seen_slugs,
                locator,
                f"duplicate registry slug {entry.get('slug')!r}",
            )
        )
        findings.extend(
            _duplicate_finding(
                entry.get("canonical_name"),
                seen_names,
                locator,
                f"duplicate canonical_name {entry.get('canonical_name')!r}",
            )
        )
        findings.extend(_alias_collision_findings(entry, locator, canonical_names))
        findings.extend(_derives_from_findings(entry, locator, ids))
    return findings


@register(
    "KR1",
    "Generic KPI registry structure and client-free boundary",
    tier=RuleTier.KIT_SELF,
)
def check_kr1(ctx: RuleContext) -> Iterable[Finding]:
    """Return structure/traceability errors for the one generic KPI registry."""

    registry, findings = _registry_entries(ctx)
    if registry is None:
        return findings
    if registry.get("version") != 1:
        findings.append(_finding(REGISTRY_REL, "registry version must be 1"))
    raw_entries = registry.get("entries")
    if not isinstance(raw_entries, list) or not raw_entries:
        findings.append(
            _finding(REGISTRY_REL, "registry entries must be a non-empty list")
        )
        return findings + _registry_leakage(registry)

    tracked = set(ctx.tracked_files)
    ids: set[str] = set()
    entries: list[dict[str, Any]] = []
    for index, entry in enumerate(raw_entries):
        entry_id, entry_findings = _validate_entry(entry, index, ids, tracked)
        findings.extend(entry_findings)
        if isinstance(entry, dict):
            entries.append(entry)
        if entry_id is None:
            continue
    findings.extend(_validate_cross_entry(entries, ids))
    findings.extend(_registry_leakage(registry))
    return findings
