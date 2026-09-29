"""Report Intent metric-reference resolution (spec 123, US1/FR-003/FR-004).

A committed Report Intent's ``outcome_metrics`` / ``driver_metrics`` /
``guardrail_metrics`` entries REFERENCE approved metric contracts by name --
never define them (FR-003). This module is the small, honest reader that
resolves each reference against the real metric-contract store and reports the
result: every metric that resolves to a contract the shared contract inventory
approves (``metric_contract_inventory`` -- never the file's own status field),
and every metric that does NOT (a gap that routes upstream to
metric-contract definition, per FR-004) -- it never invents a metric contract
to make a reference resolve.

This is the SAME committed-evidence shape ``gap_detector.py`` already reads
(``mappings/<table>/metrics/*.yaml`` + ``readiness.status``), scoped down to
just the resolve-by-name question a Report Intent needs. The US2 coordinator
(spec 123) reuses this same resolution at design time (FR-007); DL9 (the static
shape rule) deliberately does NOT do this resolution -- it is a runtime state
check, not a presence-only shape check (data-model.md D5).

Read-only: no execution, no DB, no Power BI, no approval grant, no writes.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, NamedTuple


class MetricReference(NamedTuple):
    """One ``*_metrics[]`` entry as declared in a committed report-intent.yaml."""

    name: str
    store_ref: str


class MetricGap(NamedTuple):
    """A metric reference that does NOT resolve to an approved contract."""

    name: str
    store_ref: str
    reason: str


class ResolutionResult(NamedTuple):
    """The outcome of resolving one intent's metric references."""

    resolved: tuple[str, ...]  # names that resolve to an approved (pass) contract
    gaps: tuple[MetricGap, ...]  # names that do not; never invented


def _norm_refs(entries: object) -> list[MetricReference]:
    if not isinstance(entries, list):
        return []
    out: list[MetricReference] = []
    for e in entries:
        if not isinstance(e, dict):
            continue
        name = str(e.get("name", "")).strip()
        store_ref = str(e.get("store_ref", "")).strip()
        if name:
            out.append(MetricReference(name=name, store_ref=store_ref))
    return out


def metric_references(intent: dict[str, Any]) -> list[MetricReference]:
    """The de-duplicated (by name) metric references across all three roles."""
    refs: dict[str, MetricReference] = {}
    for role in ("outcome_metrics", "driver_metrics", "guardrail_metrics"):
        for ref in _norm_refs(intent.get(role)):
            refs.setdefault(ref.name, ref)
    return list(refs.values())


_STORE_REF_RE = re.compile(r"^mappings/(?P<scope>[^/]+)/metrics/(?P<stem>[^/]+)\.yaml$")


def _store_ref_scope(store_ref: str) -> tuple[str, str] | None:
    """(scope, file stem) for a CONTAINED ``mappings/<scope>/metrics/<x>.yaml``.

    An absolute path, a ``..`` segment or anything outside a mapping scope's
    metrics/ directory is refused -- a reference may only name a governed
    contract inside this repository (audit F145)."""
    ref = store_ref.replace("\\", "/").strip()
    if not ref or ref.startswith("/") or ":" in ref or ".." in ref.split("/"):
        return None
    match = _STORE_REF_RE.match(ref)
    if match is None or match["scope"] in (".", ".."):
        return None
    return match["scope"], match["stem"]


def _resolve_one(
    ref: MetricReference, repo_root: Path, committed: bool, cache: dict
) -> str | None:
    """None when ``ref`` resolves to an APPROVED contract of the SAME name, else
    the gap reason. Approval comes only from the shared contract inventory."""
    from seshat.metric_contract_inventory import approved_contracts_for_scope

    located = _store_ref_scope(ref.store_ref)
    if located is None:
        return (
            f"store_ref {ref.store_ref!r} is not a contained "
            "mappings/<scope>/metrics/<name>.yaml path"
        )
    scope, stem = located
    if scope not in cache:
        cache[scope] = approved_contracts_for_scope(
            repo_root, scope, committed=committed
        )
    approved, errors = cache[scope]
    if stem != ref.name:
        return f"store_ref {ref.store_ref!r} names contract {stem!r}, not {ref.name!r}"
    if ref.name in approved:
        return None
    detail = next((e for e in errors if e.startswith(ref.store_ref)), None)
    if detail is None:
        return f"no approved metric contract found at {ref.store_ref!r}"
    return f"metric contract at {ref.store_ref!r} is not approved: {detail}"


def resolve_metric_references(
    intent: dict[str, Any], repo_root: Path, *, committed: bool = False
) -> ResolutionResult:
    """Resolve every metric reference in ``intent`` against the real contract
    store rooted at ``repo_root``.

    A reference resolves only when its ``store_ref`` is a contained contract path,
    the contract there carries the SAME name, and the shared contract inventory
    approves it (FR-003). Everything else is a GAP: it is reported, never
    invented (FR-004). ``committed=True`` reads at HEAD (approval-bearing
    callers such as the dashboard coordinator). No write, no approval grant.
    """
    resolved: list[str] = []
    gaps: list[MetricGap] = []
    cache: dict = {}
    for ref in metric_references(intent):
        reason = _resolve_one(ref, Path(repo_root), committed, cache)
        if reason is None:
            resolved.append(ref.name)
        else:
            gaps.append(
                MetricGap(name=ref.name, store_ref=ref.store_ref, reason=reason)
            )
    return ResolutionResult(resolved=tuple(resolved), gaps=tuple(gaps))
