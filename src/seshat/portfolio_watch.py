"""Portfolio Watch (spec 131): a recurring, read-only portfolio summary.

This module is a COMPOSITION, not a second source of truth (mirrors
``agent_next.py`` / ``readiness_projection.py``). It JOINS evidence that the
shipped per-scope surfaces already produce -- source drift, contract/metric
drift, dashboard-intent divergence, readiness, approvals, review -- into one
portfolio-wide summary, and persists a local baseline snapshot so the next
run can diff current categorical state into new/resolved/unchanged. It NEVER
re-runs or re-derives a shipped surface's own check; it reads that surface's
already-committed output and relays it, citing the source path.

Hard boundaries (spec 131, FR-018..FR-025):
  - READ-ONLY. The only writes this module makes are the summary it returns
    and the local snapshot under ``.seshat/watch/snapshot.json``. No project
    file is modified, no database is opened, no approval is recorded, no
    readiness stage is moved to ``pass``, nothing is published.
  - NO DATABASE in the MVP: this module imports no ``Dialect``/DSN-touching
    seam (``seshat.dialect``, ``seshat.portfolio_enumerate``,
    ``seshat.validate``); the governed-scope set comes from committed
    ``mappings/*/readiness-status.yaml`` paths, never a live metadata query.
  - NO NEW GATE / RULE / APPROVAL MECHANISM: this is an aggregation/summary
    layer, not another governance engine.
  - NO NUMERIC SCORE: every field is one of the four readiness spine statuses,
    a shipped categorical finding enum (relayed verbatim from the surface that
    emitted it), or a measured magnitude (a count/rate/delta) traceable to a
    committed source. No health/confidence/priority/quality number is ever
    emitted (hard rule #9).
  - NO ORIGINATED PRINCIPLE-V RULING: a relayed grain/PII/returns/approval
    condition always names a responsible owner; this module decides none of
    them.

Module scope stays stdlib-only at import time (``json``, ``pathlib``,
``dataclasses``, ``subprocess`` only for ``git rev-parse HEAD``, mirroring
``readiness_projection._source_revision``). It composes the following shipped
READERS (never re-implemented): ``readiness_projection`` (readiness +
next_action), ``readiness_classify`` (the fixed category rank),
``approval_inbox`` (open/invalid approval seams), and ``disclosure`` (the
shipped disclosure scan). None of these touch a database.

Dimension -> committed-evidence map (research.md D5; data-model.md):
  - ``readiness``                  -- read directly from the readiness
    projection (``readiness_projection.py`` / ``readiness_classify.py``);
    no separate artifact.
  - ``approvals``                  -- read directly from the approval inbox
    (``approval_inbox.py``); no separate artifact.
  - ``source_drift``               -- a committed
    ``mappings/<scope>/drift-findings.json`` artifact (the shape
    ``drift.to_findings_dict`` emits, schema_version "1.0"); absent when a
    baseline ``source-profile.md`` exists -> ``[PENDING LIVE]`` (the live
    re-profile leg is unavailable); absent with no baseline at all ->
    ``not_applicable_with_reason``.
  - ``contract_metric_drift``      -- a committed
    ``mappings/<scope>/metric-drift-findings.json`` artifact (a previously
    recorded run of ``retail semantic-check`` / ``metric_drift.py`` verdicts);
    absent -> ``not_applicable_with_reason``.
  - ``dashboard_intent_divergence``-- a committed
    ``mappings/<scope>/semantic-audit-findings.json`` artifact (a previously
    recorded ``semantic_audit.run_semantic_audit`` result); absent ->
    ``not_applicable_with_reason``.
  - ``review``                     -- a committed
    ``mappings/<scope>/review-result.json`` artifact (a previously recorded
    ``review_integration.build_review_result`` result); absent ->
    ``not_applicable_with_reason``.

This module never invokes ``drift.classify_drift``, ``metric_drift.
check_measure_drift``, ``semantic_audit.run_semantic_audit``, or
``review_integration.build_review_result`` itself -- doing so would be
re-running a surface's own check (FR-003). It only reads what those surfaces
already recorded, verbatim, citing the artifact path.
"""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .approval_inbox import build_approval_inbox
from .disclosure import scan_disclosure
from .portfolio_watch_baseline import (
    CHANGE_LABELS,
    LABEL_NEW,
    LABEL_NO_BASELINE,
    LABEL_RESOLVED,
    LABEL_UNCHANGED,
    SNAPSHOT_SCHEMA_VERSION,
    ConditionChange,
    classify_changes,
    condition_keys_from_summary,
    read_prior_snapshot,
    write_snapshot,
)
from .readiness_classify import CATEGORY_RANK, classify, rank_of
from .readiness_projection import build_readiness_projection

SCHEMA_VERSION = "1.0"
_ARTIFACT_SCHEMA_VERSION = "1.0"

# The closed, truthful degradation-state set (data-model.md). No state is ever
# invented ad hoc anywhere else in this module.
STATE_COVERED = "covered"
STATE_PENDING_LIVE = "[PENDING LIVE]"
STATE_STALE = "stale"
STATE_NOT_APPLICABLE = "not_applicable_with_reason"
STATE_UNREADABLE = "unreadable"

DEGRADATION_STATES: frozenset[str] = frozenset(
    {
        STATE_COVERED,
        STATE_PENDING_LIVE,
        STATE_STALE,
        STATE_NOT_APPLICABLE,
        STATE_UNREADABLE,
    }
)

# The six covered dimensions this feature joins (spec 131 FR-001).
DIMENSIONS: tuple[str, ...] = (
    "source_drift",
    "contract_metric_drift",
    "dashboard_intent_divergence",
    "readiness",
    "approvals",
    "review",
)

_SOURCE_SURFACE: dict[str, str] = {
    "source_drift": "seshat.drift / seshat.drift_semantics",
    "contract_metric_drift": "seshat.metric_drift",
    "dashboard_intent_divergence": "seshat.semantic_audit / seshat.report_intent",
    "readiness": "seshat.readiness_projection / seshat.readiness_classify",
    "approvals": "seshat.approval_inbox",
    "review": "seshat.review_integration / seshat.review_pack_export",
}

# The committed-artifact filename convention for the four surfaces this
# feature reads via a per-scope JSON artifact (readiness/approvals are read
# directly, no artifact). A tasks-level detail (data-model.md leaves concrete
# serialization to implementation); documented here so a producer knows where
# to record its output for Portfolio Watch to relay.
_ARTIFACT_FILENAMES: dict[str, str] = {
    "source_drift": "drift-findings.json",
    "contract_metric_drift": "metric-drift-findings.json",
    "dashboard_intent_divergence": "semantic-audit-findings.json",
    "review": "review-result.json",
}


# --------------------------------------------------------------------------- #
# Frozen data shapes (data-model.md)
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class DimensionItem:
    """One standing condition inside a covered dimension finding.

    ``class_`` + ``subject_locator`` (NOT ``measured``) form the magnitude-free
    part of the Condition Key -- a magnitude wiggle on ``measured`` never
    changes the key (research D3, duplicate suppression FR-010).
    """

    class_: str
    subject_locator: str
    measured: str | None = None
    owner: str | None = None
    principle_v: bool = False


@dataclass(frozen=True)
class CoveredDimensionFinding:
    """One (scope, dimension) finding (data-model.md entity 2)."""

    dimension: str
    state: str
    class_: str | None = None
    measured: str | None = None
    evidence: str | None = None
    owner: str | None = None
    source_surface: str = ""
    items: tuple[DimensionItem, ...] = ()

    def __post_init__(self) -> None:
        if self.state not in DEGRADATION_STATES:
            raise ValueError(f"invalid degradation state: {self.state!r}")


@dataclass(frozen=True)
class PrioritizedNextAction:
    """The one next action per scope (data-model.md entity; FR-005)."""

    category: str
    action: str


@dataclass(frozen=True)
class GovernedScope:
    """The existing per-table/per-report unit (data-model.md entity 1; FR-002).
    No new scope unit is introduced -- identified by its committed
    readiness-status source path, exactly as ``status_surface`` /
    ``readiness_projection`` already identify a table."""

    scope_id: str
    source_path: str
    current_stage: str | None


# --------------------------------------------------------------------------- #
# Git revision (mirrors readiness_projection._source_revision verbatim)
# --------------------------------------------------------------------------- #
def _source_revision(root: Path) -> str | None:
    result = subprocess.run(
        ["git", "-c", f"safe.directory={root.as_posix()}", "rev-parse", "HEAD"],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    return result.stdout.strip() if result.returncode == 0 else None


# --------------------------------------------------------------------------- #
# Governed-scope enumeration (T006; research D6: committed paths, no live DB)
# --------------------------------------------------------------------------- #
def enumerate_governed_scopes(repo_root: Path | str = ".") -> tuple[GovernedScope, ...]:
    """Enumerate governed scopes from committed ``mappings/*/readiness-status.
    yaml`` paths -- the SAME source ``status_surface``/``readiness_projection``
    already track (FR-002). Never opens a database connection; a malformed
    readiness-status.yaml still yields a scope entry (current_stage=None) so a
    read error degrades that scope's dimension, never silently drops it
    (FR-017/FR-022)."""
    root = Path(repo_root).resolve()
    mappings_dir = root / "mappings"
    if not mappings_dir.is_dir():
        return ()
    projection = build_readiness_projection(root)
    by_path = {t["source_path"]: t for t in projection["tables"]}
    scopes: list[GovernedScope] = []
    for status_path in sorted(mappings_dir.glob("*/readiness-status.yaml")):
        source_path = status_path.relative_to(root).as_posix()
        entry = by_path.get(source_path)
        scope_id = entry["table_id"] if entry is not None else status_path.parent.name
        current_stage = entry["current_stage"] if entry is not None else None
        scopes.append(
            GovernedScope(
                scope_id=scope_id, source_path=source_path, current_stage=current_stage
            )
        )
    return tuple(scopes)


# --------------------------------------------------------------------------- #
# Per-dimension joins (US1 T011; US3 T028 truthful degradation)
# --------------------------------------------------------------------------- #
def _read_json(path: Path) -> tuple[dict[str, Any] | None, str | None]:
    """Best-effort JSON read. Never raises; returns (data, error)."""
    try:
        text = path.read_text(encoding="utf-8-sig")
    except OSError as exc:
        return None, f"read error: {exc}"
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        return None, f"malformed JSON: {exc}"
    if not isinstance(data, dict):
        return None, "artifact is not a JSON object"
    return data, None


def _parse_items(raw: object) -> tuple[DimensionItem, ...]:
    if not isinstance(raw, list):
        return ()
    items: list[DimensionItem] = []
    for entry in raw:
        if not isinstance(entry, dict):
            continue
        cls = entry.get("class")
        locator = entry.get("subject_locator")
        if not isinstance(cls, str) or not isinstance(locator, str):
            continue
        measured = entry.get("measured")
        owner = entry.get("owner")
        items.append(
            DimensionItem(
                class_=cls,
                subject_locator=locator,
                measured=measured if isinstance(measured, str) else None,
                owner=owner if isinstance(owner, str) else None,
                principle_v=bool(entry.get("principle_v", False)),
            )
        )
    return tuple(items)


def _missing_artifact_finding(
    dimension: str, scope_dir: Path, surface: str
) -> CoveredDimensionFinding:
    if dimension != "source_drift":
        return CoveredDimensionFinding(
            dimension=dimension,
            state=STATE_NOT_APPLICABLE,
            measured="no evidence produced yet for this scope",
            source_surface=surface,
        )
    baseline = scope_dir / "source-profile.md"
    if baseline.is_file():
        return CoveredDimensionFinding(
            dimension=dimension,
            state=STATE_PENDING_LIVE,
            measured=(
                "a baseline source-profile.md is recorded but no "
                "live re-profile has been captured yet"
            ),
            source_surface=surface,
        )
    return CoveredDimensionFinding(
        dimension=dimension,
        state=STATE_NOT_APPLICABLE,
        measured="no baseline source-profile.md recorded for this scope",
        source_surface=surface,
    )


def _is_stale_captured_at(captured_at: object, source_revision: str | None) -> bool:
    return (
        source_revision is not None
        and isinstance(captured_at, str)
        and bool(captured_at)
        and captured_at != source_revision
    )


@dataclass(frozen=True)
class _ArtifactContext:
    """The trio every artifact-finding helper needs once a committed JSON
    artifact has been located -- bundled into one value so each helper stays
    under the 4-argument limit."""

    dimension: str
    rel_artifact: str
    surface: str


def _stale_artifact_finding(
    ctx: _ArtifactContext, data: dict[str, Any], source_revision: str | None
) -> CoveredDimensionFinding | None:
    captured_at = data.get("captured_at_revision")
    if not _is_stale_captured_at(captured_at, source_revision):
        return None
    return CoveredDimensionFinding(
        dimension=ctx.dimension,
        state=STATE_STALE,
        class_=data.get("class") if isinstance(data.get("class"), str) else None,
        measured=f"captured_at_revision={captured_at} vs current={source_revision}",
        evidence=ctx.rel_artifact,
        owner=data.get("owner") if isinstance(data.get("owner"), str) else None,
        source_surface=ctx.surface,
    )


def _pending_live_artifact_finding(
    ctx: _ArtifactContext, data: dict[str, Any]
) -> CoveredDimensionFinding | None:
    if ctx.dimension != "source_drift" or data.get("live_leg_available") is not False:
        return None
    return CoveredDimensionFinding(
        dimension=ctx.dimension,
        state=STATE_PENDING_LIVE,
        class_=data.get("class") if isinstance(data.get("class"), str) else None,
        measured=data.get("measured")
        if isinstance(data.get("measured"), str)
        else "live re-profile not available",
        evidence=ctx.rel_artifact,
        source_surface=ctx.surface,
    )


def _covered_artifact_finding(
    ctx: _ArtifactContext, data: dict[str, Any]
) -> CoveredDimensionFinding:
    cls = data.get("class")
    if not isinstance(cls, str) or not cls:
        return CoveredDimensionFinding(
            dimension=ctx.dimension,
            state=STATE_UNREADABLE,
            measured="artifact is missing a required 'class' field",
            evidence=ctx.rel_artifact,
            source_surface=ctx.surface,
        )
    return CoveredDimensionFinding(
        dimension=ctx.dimension,
        state=STATE_COVERED,
        class_=cls,
        measured=data.get("measured")
        if isinstance(data.get("measured"), str)
        else None,
        evidence=ctx.rel_artifact,
        owner=data.get("owner") if isinstance(data.get("owner"), str) else None,
        source_surface=ctx.surface,
        items=_parse_items(data.get("items")),
    )


def _parsed_artifact_finding(
    ctx: _ArtifactContext, data: dict[str, Any], source_revision: str | None
) -> CoveredDimensionFinding:
    schema_version = data.get("schema_version")
    if schema_version != _ARTIFACT_SCHEMA_VERSION:
        return CoveredDimensionFinding(
            dimension=ctx.dimension,
            state=STATE_UNREADABLE,
            measured=f"unknown schema_version {schema_version!r}",
            evidence=ctx.rel_artifact,
            source_surface=ctx.surface,
        )
    stale = _stale_artifact_finding(ctx, data, source_revision)
    if stale is not None:
        return stale
    pending = _pending_live_artifact_finding(ctx, data)
    if pending is not None:
        return pending
    return _covered_artifact_finding(ctx, data)


def _artifact_dimension_finding(
    dimension: str,
    root: Path,
    scope: GovernedScope,
    source_revision: str | None,
) -> CoveredDimensionFinding:
    """Read one dimension's committed JSON artifact (US3 truthful
    degradation): missing evidence -> not_applicable_with_reason (or
    [PENDING LIVE] for source_drift when a baseline exists); malformed/unknown
    schema -> unreadable; captured before HEAD -> stale; a live leg the
    artifact itself declares unavailable -> [PENDING LIVE]. Never upgrades a
    degraded state to covered; never raises (a per-scope read error degrades
    only this cell, FR-022)."""
    surface = _SOURCE_SURFACE[dimension]
    scope_dir_name = Path(scope.source_path).parent.name
    scope_dir = root / "mappings" / scope_dir_name
    filename = _ARTIFACT_FILENAMES[dimension]
    artifact_path = scope_dir / filename

    try:
        if not artifact_path.is_file():
            return _missing_artifact_finding(dimension, scope_dir, surface)

        rel_artifact = artifact_path.relative_to(root).as_posix()
        data, err = _read_json(artifact_path)
        if data is None:
            return CoveredDimensionFinding(
                dimension=dimension,
                state=STATE_UNREADABLE,
                measured=err,
                evidence=rel_artifact,
                source_surface=surface,
            )
        ctx = _ArtifactContext(
            dimension=dimension, rel_artifact=rel_artifact, surface=surface
        )
        return _parsed_artifact_finding(ctx, data, source_revision)
    except OSError as exc:  # pragma: no cover - defensive, mirrors FR-022
        return CoveredDimensionFinding(
            dimension=dimension,
            state=STATE_UNREADABLE,
            measured=f"read error: {exc}",
            source_surface=surface,
        )


def _readiness_dimension_finding(
    scope: GovernedScope, entry: dict[str, Any] | None
) -> CoveredDimensionFinding:
    surface = _SOURCE_SURFACE["readiness"]
    if entry is None:
        return CoveredDimensionFinding(
            dimension="readiness",
            state=STATE_UNREADABLE,
            measured="readiness-status.yaml could not be parsed",
            evidence=scope.source_path,
            source_surface=surface,
        )
    items: list[DimensionItem] = [
        DimensionItem(class_="blocking_reason", subject_locator="portfolio", measured=r)
        for r in entry.get("blocking_reasons", [])
    ]
    for stage_name, block in entry.get("stages", {}).items():
        for reason in block.get("blocking_reasons", []):
            items.append(
                DimensionItem(
                    class_=block["status"], subject_locator=stage_name, measured=reason
                )
            )
    measured = f"{len(items)} open condition(s)" if items else "0 open conditions"
    return CoveredDimensionFinding(
        dimension="readiness",
        state=STATE_COVERED,
        class_=entry.get("current_stage") or "unknown",
        measured=measured,
        evidence=scope.source_path,
        source_surface=surface,
        items=tuple(items),
    )


def _approvals_dimension_finding(
    scope: GovernedScope, inbox_items: list[dict[str, Any]]
) -> CoveredDimensionFinding:
    surface = _SOURCE_SURFACE["approvals"]
    mine = [i for i in inbox_items if i["source_path"] == scope.source_path]
    if not mine:
        return CoveredDimensionFinding(
            dimension="approvals",
            state=STATE_COVERED,
            class_="no_open_approval_issue",
            measured="0 open approval issues",
            evidence=scope.source_path,
            source_surface=surface,
        )
    items = tuple(
        DimensionItem(
            class_=i["issue"],
            subject_locator=i["stage"],
            measured=i["detail"],
            owner=i["required_authority"],
            principle_v=False,
        )
        for i in mine
    )
    worst = mine[0]
    return CoveredDimensionFinding(
        dimension="approvals",
        state=STATE_COVERED,
        class_=worst["issue"],
        measured=f"{len(mine)} open approval issue(s)",
        evidence=scope.source_path,
        owner=worst["required_authority"],
        source_surface=surface,
        items=items,
    )


# --------------------------------------------------------------------------- #
# Prioritized next action (US1 T012; FR-005; C1: ranks readiness-blocker
# categories only; relayed action, never synthesized)
# --------------------------------------------------------------------------- #
def _open_reasons(entry: dict[str, Any]) -> list[str]:
    reasons = list(entry.get("blocking_reasons", []))
    for block in entry.get("stages", {}).values():
        reasons.extend(block.get("blocking_reasons", []))
    return reasons


def select_next_action(entry: dict[str, Any] | None) -> PrioritizedNextAction:
    """Select the one next action for a scope by the SHIPPED fixed
    ``readiness_classify`` rank, relaying the scope's own recorded
    ``next_action`` -- never a synthesized string (FR-005).

    Open conditions come from two committed signals: each stage's recorded
    ``blocking_reasons`` text (classified via ``readiness_classify.classify``)
    AND the readiness projection's own ``required_authority`` (non-None
    exactly when ``run_next`` resolved an ``approval_required`` outcome, which
    carries no ``blocking_reasons`` text of its own to classify). Folding the
    latter in as an implicit ``approval``-category signal means a missing
    named approval is never missed just because it left no free-text blocker.
    """
    if entry is None:
        return PrioritizedNextAction(
            category="readiness",
            action=(
                "repair the malformed readiness-status.yaml before any pipeline work"
            ),
        )
    ranks = [rank_of(classify(reason)[0]) for reason in _open_reasons(entry)]
    if entry.get("required_authority"):
        ranks.append(rank_of("approval"))
    if not ranks:
        return PrioritizedNextAction(category="readiness", action=entry["next_action"])
    best_category = CATEGORY_RANK[min(ranks)]
    return PrioritizedNextAction(category=best_category, action=entry["next_action"])


def _requires_attention(
    dims: dict[str, CoveredDimensionFinding],
) -> tuple[bool, str | None]:
    """FR-006: set independently of category rank -- an unmet/invalid approval
    OR any relayed Principle-V drift blocker (regardless of which dimension or
    rank bucket it falls into) sets this flag and names the owner."""
    approvals = dims["approvals"]
    if approvals.items:
        return True, approvals.owner
    for dim in dims.values():
        for item in dim.items:
            if item.principle_v:
                return True, item.owner
    return False, None


# --------------------------------------------------------------------------- #
# Summary assembly (US1 T013)
# --------------------------------------------------------------------------- #
def _finding_to_dict(finding: CoveredDimensionFinding) -> dict[str, Any]:
    return {
        "dimension": finding.dimension,
        "state": finding.state,
        "class": finding.class_,
        "measured": finding.measured,
        "evidence": finding.evidence,
        "owner": finding.owner,
        "source_surface": finding.source_surface,
        "items": [
            {
                "class": item.class_,
                "subject_locator": item.subject_locator,
                "measured": item.measured,
                "owner": item.owner,
                "principle_v": item.principle_v,
            }
            for item in finding.items
        ],
    }


_ARTIFACT_DIMENSION_NAMES: tuple[str, ...] = (
    "source_drift",
    "contract_metric_drift",
    "dashboard_intent_divergence",
    "review",
)


@dataclass(frozen=True)
class _AssembleContext:
    """The values one ``_assemble`` call holds constant across every scope --
    bundled into one value so ``_scope_dimensions`` stays under the
    4-argument limit."""

    root: Path
    inbox_items: list[dict[str, Any]]
    revision: str | None


def _scope_dimensions(
    scope: GovernedScope, entry: dict[str, Any] | None, ctx: _AssembleContext
) -> dict[str, CoveredDimensionFinding]:
    dims: dict[str, CoveredDimensionFinding] = {
        "readiness": _readiness_dimension_finding(scope, entry),
        "approvals": _approvals_dimension_finding(scope, ctx.inbox_items),
    }
    for dimension in _ARTIFACT_DIMENSION_NAMES:
        dims[dimension] = _artifact_dimension_finding(
            dimension, ctx.root, scope, ctx.revision
        )
    return dims


def _dimension_keys(
    scope_id: str, dims: dict[str, CoveredDimensionFinding]
) -> set[tuple[str, str, str, str]]:
    return {
        (scope_id, dim_name, item.class_, item.subject_locator)
        for dim_name, finding in dims.items()
        for item in finding.items
    }


def _artifact_dims_evidenced(dims: dict[str, CoveredDimensionFinding]) -> bool:
    return any(
        dims[name].state != STATE_NOT_APPLICABLE for name in _ARTIFACT_DIMENSION_NAMES
    )


def _scope_document(
    scope: GovernedScope,
    entry: dict[str, Any] | None,
    dims: dict[str, CoveredDimensionFinding],
) -> dict[str, Any]:
    next_action = select_next_action(entry)
    attention, owner = _requires_attention(dims)
    open_blockers = list(entry.get("blocking_reasons", [])) if entry else []
    return {
        "scope_id": scope.scope_id,
        "source_path": scope.source_path,
        "current_stage": scope.current_stage,
        "dimensions": [_finding_to_dict(dims[d]) for d in DIMENSIONS],
        "open_blockers": open_blockers,
        "requires_human_attention": attention,
        "owner": owner,
        "prioritized_next_action": {
            "category": next_action.category,
            "action": next_action.action,
        },
    }


def _assemble(
    root: Path,
) -> tuple[dict[str, Any], frozenset[tuple[str, str, str, str]]]:
    """Build the summary body + the full set of magnitude-free condition keys
    it carries. Read-only; deterministic; never fails the whole run on one
    scope's read error (FR-017)."""
    scopes = enumerate_governed_scopes(root)
    projection = build_readiness_projection(root)
    by_path = {t["source_path"]: t for t in projection["tables"]}
    revision = _source_revision(root)
    ctx = _AssembleContext(
        root=root, inbox_items=build_approval_inbox(root)["items"], revision=revision
    )

    scope_docs: list[dict[str, Any]] = []
    scopes_with_no_evidence: list[str] = []
    all_keys: set[tuple[str, str, str, str]] = set()

    for scope in scopes:
        entry = by_path.get(scope.source_path)
        dims = _scope_dimensions(scope, entry, ctx)
        all_keys |= _dimension_keys(scope.scope_id, dims)
        if not _artifact_dims_evidenced(dims):
            scopes_with_no_evidence.append(scope.scope_id)
        scope_docs.append(_scope_document(scope, entry, dims))

    attention_count = sum(1 for doc in scope_docs if doc["requires_human_attention"])

    body: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "generated_at_revision": revision,
        "scopes": scope_docs,
        "portfolio": {
            "scope_count": len(scopes),
            "scopes_requiring_attention_count": attention_count,
            "scopes_with_no_evidence": sorted(scopes_with_no_evidence),
        },
    }
    body["disclosure"] = scan_disclosure(body)
    return body, frozenset(all_keys)


def build_portfolio_watch_summary(repo_root: Path | str = ".") -> dict[str, Any]:
    """Build the Portfolio Watch summary (US1). Read-only, deterministic; adds
    no ``change_labels`` (that is the baseline-diff layer, ``run_portfolio_
    watch``). Every ``covered`` finding cites committed evidence; every other
    dimension is truthfully degraded (never a fabricated pass)."""
    root = Path(repo_root).resolve()
    body, _keys = _assemble(root)
    return body


# --------------------------------------------------------------------------- #
# The run flow (US2 T021): read prior -> build summary -> classify -> write
# (condition keys, baseline snapshot, and the change classifier live in
# ``portfolio_watch_baseline``, imported above)
# --------------------------------------------------------------------------- #
def run_portfolio_watch(repo_root: Path | str = ".") -> dict[str, Any]:
    """Run one Portfolio Watch pass: read the prior snapshot, build the
    summary (US1), classify changes against the prior snapshot (US2), and
    write a fresh snapshot. The snapshot write is the only write beyond the
    returned summary (SC-008)."""
    root = Path(repo_root).resolve()
    prior = read_prior_snapshot(root)
    body, current_keys = _assemble(root)
    current_scopes = frozenset(scope["scope_id"] for scope in body["scopes"])

    conditions, scope_changes = classify_changes(current_keys, current_scopes, prior)
    by_scope: dict[str, list[dict[str, str]]] = {
        scope["scope_id"]: [] for scope in body["scopes"]
    }
    for change in conditions:
        scope_id, dimension, cls, locator = change.key
        by_scope.setdefault(scope_id, []).append(
            {
                "dimension": dimension,
                "class": cls,
                "subject_locator": locator,
                "label": change.label,
            }
        )
    for scope_doc in body["scopes"]:
        scope_doc["change_labels"] = by_scope.get(scope_doc["scope_id"], [])
    body["scope_changes"] = scope_changes
    body["baseline"] = {"used": prior is not None}
    if prior is None:
        body["baseline"]["note"] = (
            "no prior snapshot was available to diff against; every condition "
            "is a current condition, explicitly not 'new'"
        )

    write_snapshot(root, current_keys, current_scopes, body["generated_at_revision"])
    body["disclosure"] = scan_disclosure(body)
    return body


__all__ = [
    "SCHEMA_VERSION",
    "SNAPSHOT_SCHEMA_VERSION",
    "DEGRADATION_STATES",
    "CHANGE_LABELS",
    "DIMENSIONS",
    "STATE_COVERED",
    "STATE_PENDING_LIVE",
    "STATE_STALE",
    "STATE_NOT_APPLICABLE",
    "STATE_UNREADABLE",
    "LABEL_NEW",
    "LABEL_RESOLVED",
    "LABEL_UNCHANGED",
    "LABEL_NO_BASELINE",
    "DimensionItem",
    "CoveredDimensionFinding",
    "PrioritizedNextAction",
    "ConditionChange",
    "GovernedScope",
    "enumerate_governed_scopes",
    "select_next_action",
    "build_portfolio_watch_summary",
    "condition_keys_from_summary",
    "read_prior_snapshot",
    "write_snapshot",
    "classify_changes",
    "run_portfolio_watch",
]
