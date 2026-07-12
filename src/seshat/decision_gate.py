"""Decision gate: pass / warn / blocked verdicts over the Decision Store (spec 121).

A pure projection. Given the store, the repo root (to resolve cited evidence and
the flow contract), and a requested flow stage, it classifies readiness:

* ``blocked`` -- a required decision for the stage is unresolved, invalid, in
  conflict, or its approval evidence is missing/unresolvable; each concrete
  blocking decision is named;
* ``warn``    -- progress allowed, non-fatal issues listed (accepted deviations,
  stale evidence on non-critical decisions, open low-risk questions);
* ``pass``    -- every required decision is approved with valid metadata and
  resolvable evidence, and no blocking condition applies.

Never stores state: the readiness spine remains the sole stage-state authority.
Fails closed: a malformed store, an unknown status, or a missing flow contract
yields ``blocked``, never ``pass``. Determinism (FR-034): computed only from
committed artifacts (store + cited evidence + the flow contract).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from seshat.artifact_identity import artifact_identity
from seshat.decision_store import (
    Store,
    active_scope_conflicts,
    approval_is_valid,
    is_critical,
    is_open_status,
    load_authority_map,
    load_store,
)

_FLOW_CONTRACT_REL = "contracts/knowledge/database-to-pbip-flow.yaml"

VERDICTS = ("pass", "warn", "blocked")


@dataclass(frozen=True)
class Blocker:
    decision_id: str
    reason: str


@dataclass(frozen=True)
class Verdict:
    stage: str
    verdict: str  # pass | warn | blocked
    blocking: tuple[Blocker, ...] = ()
    warnings: tuple[str, ...] = ()
    evidence: tuple[str, ...] = ()


def _load_blocking_categories(repo_root: Path | str, stage: str) -> set[str] | None:
    """The blocking decision categories declared for ``stage`` in the flow
    contract. None => fail closed (contract missing/malformed/unknown stage)."""
    path = Path(repo_root) / _FLOW_CONTRACT_REL
    try:
        raw = path.read_text(encoding="utf-8-sig")
    except (OSError, UnicodeDecodeError):
        return None
    import yaml

    try:
        data = yaml.safe_load(raw)
    except yaml.YAMLError:
        return None
    if not isinstance(data, dict) or not isinstance(data.get("stages"), list):
        return None
    for entry in data["stages"]:
        if isinstance(entry, dict) and entry.get("stage") == stage:
            cats = entry.get("blocking_decision_categories")
            return set(cats) if isinstance(cats, list) else set()
    return None  # unknown stage -> fail closed


def _evidence_stale(repo_root: Path | str, approval: dict[str, Any]) -> list[str]:
    """Cited evidence whose current content identity differs from the recorded
    ``evidence_identity`` at approval time (research R-10). A missing file or an
    unresolvable reference counts as stale/mismatched."""
    recorded = approval.get("evidence_identity")
    evidence = approval.get("evidence")
    if not isinstance(recorded, dict) or not isinstance(evidence, list):
        return list(evidence) if isinstance(evidence, list) else []
    stale: list[str] = []
    for ref in evidence:
        if not isinstance(ref, str):
            continue
        want = recorded.get(ref)
        try:
            current = artifact_identity(repo_root, ref, kind="evidence")
        except (ValueError, OSError):
            stale.append(ref)
            continue
        if current.get("verification") != "verified" or current.get("sha256") != want:
            stale.append(ref)
    return stale


def _decision_applies(decision: dict[str, Any], categories: set[str]) -> bool:
    dtype = decision.get("decision_type")
    return isinstance(dtype, str) and dtype in categories


def _classify_decision(
    repo_root: Path | str,
    decision: dict[str, Any],
    authority: dict[str, frozenset[str]] | None,
) -> tuple[str, str | None]:
    """Return (state, note) for one in-scope decision.

    state in {"ok", "blocked", "warn"}:
      - open status                        -> blocked (unresolved)
      - unrecognized status                -> blocked (fail closed)
      - rejected / superseded (terminal)   -> ok (settled; does not block)
      - approved but INVALID approval       -> blocked (shared approval_is_valid)
      - approved but stale-critical         -> blocked
      - approved but stale-non-critical     -> warn
      - approved, valid, fresh              -> ok (contributes evidence)
    """
    status = decision.get("status")
    did = decision.get("id", "<no-id>")
    if is_open_status(status):
        return "blocked", f"{did}: decision is {status!r} (unresolved)"
    if status == "approved":
        return _classify_approved(repo_root, decision, authority)
    # rejected and superseded are settled terminal states (they do not block).
    if status in ("rejected", "superseded"):
        return "ok", None
    # Any unrecognized status fails CLOSED at the gate (DS1 also ERRORs it).
    return "blocked", f"{did}: unrecognized status {status!r}"


def _classify_approved(
    repo_root: Path | str,
    decision: dict[str, Any],
    authority: dict[str, frozenset[str]] | None,
) -> tuple[str, str | None]:
    """Classify an approved decision. Reuses the shared approval_is_valid predicate
    so the gate and DS2 can never disagree on what a valid approval is."""
    did = decision.get("id", "<no-id>")
    valid, reason = approval_is_valid(decision, authority)
    if not valid:
        return "blocked", reason
    approval = decision["approval"]
    stale = _evidence_stale(repo_root, approval)
    if not stale:
        return "ok", None
    if is_critical(decision.get("decision_type")):
        return "blocked", f"{did}: approval evidence is stale/missing {stale}"
    return "warn", f"{did}: stale evidence on non-critical decision {stale}"


def _failclosed_verdict(
    repo_root: Path | str, store: Store, stage: str
) -> Verdict | None:
    """Return a blocked verdict for a fail-closed precondition (malformed store or
    missing/unknown flow stage), else None to proceed."""
    if store.problems:
        return Verdict(
            stage,
            "blocked",
            tuple(Blocker(p.locator, p.message) for p in store.problems),
        )
    if _load_blocking_categories(repo_root, stage) is None:
        return Verdict(
            stage,
            "blocked",
            (
                Blocker(
                    _FLOW_CONTRACT_REL,
                    f"flow contract missing/malformed or unknown stage {stage!r}",
                ),
            ),
        )
    return None


def _approval_evidence(decision: dict[str, Any]) -> list[str]:
    approval = decision.get("approval")
    evidence = approval.get("evidence") if isinstance(approval, dict) else None
    return (
        [e for e in evidence if isinstance(e, str)]
        if isinstance(evidence, list)
        else []
    )


@dataclass
class _Accumulator:
    blocking: list[Blocker] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    evidence: list[str] = field(default_factory=list)

    def add(
        self,
        repo_root: Path | str,
        decision: dict[str, Any],
        authority: dict[str, frozenset[str]] | None,
    ) -> None:
        state, note = _classify_decision(repo_root, decision, authority)
        if state == "blocked" and note:
            self.blocking.append(Blocker(str(decision.get("id", "<no-id>")), note))
        elif state == "warn" and note:
            self.warnings.append(note)
        elif state == "ok":
            self.evidence += _approval_evidence(decision)


def _conflict_blockers(
    decisions: list[dict[str, Any]], categories: set[str]
) -> list[Blocker]:
    """Blockers for 2+ active in-scope records conflicting on one scope (shared
    with DS4 via active_scope_conflicts) -- the FR-033 'in conflict' trigger."""
    return [
        Blocker(ids[0], f"conflicting active {dtype} decisions on {key}: {ids}")
        for dtype, key, ids in active_scope_conflicts(decisions)
        if dtype in categories
    ]


def _not_started_blocker(stage: str) -> Blocker:
    return Blocker(
        stage,
        "no approved in-scope decision provides evidence; the stage's required "
        "decisions are not started/approved",
    )


def _final_verdict(stage: str, categories: set[str], acc: _Accumulator) -> Verdict:
    """Resolve the pass/warn/blocked outcome from an accumulated result set."""
    warnings, evidence = tuple(acc.warnings), tuple(acc.evidence)
    if acc.blocking:
        return Verdict(stage, "blocked", tuple(acc.blocking), warnings, evidence)
    # Evidence-presence rule (FR-034 / gate-verdicts.md line 9): on a stage that
    # declares blocking categories, a pass MUST rest on at least one citable
    # evidence string. Empty evidence => not-started => blocked, never a false
    # pass from an absent/empty store.
    if categories and not acc.evidence:
        return Verdict(stage, "blocked", (_not_started_blocker(stage),), warnings)
    if acc.warnings:
        return Verdict(stage, "warn", (), warnings, evidence)
    return Verdict(stage, "pass", (), (), evidence)


def compute_verdict(repo_root: Path | str, store: Store, stage: str) -> Verdict:
    """Classify readiness for ``stage`` from the store + evidence + flow contract."""
    failclosed = _failclosed_verdict(repo_root, store, stage)
    if failclosed is not None:
        return failclosed

    categories = _load_blocking_categories(repo_root, stage) or set()
    authority = load_authority_map(repo_root)
    decisions = store.decisions()

    acc = _Accumulator()
    for decision in decisions:
        if _decision_applies(decision, categories):
            acc.add(repo_root, decision, authority)
    acc.blocking += _conflict_blockers(decisions, categories)

    return _final_verdict(stage, categories, acc)


def verdict_for(
    repo_root: Path | str, tracked_files: tuple[str, ...], stage: str
) -> Verdict:
    """Convenience: load the store from tracked files and compute the verdict."""
    store = load_store(repo_root, tracked_files)
    return compute_verdict(repo_root, store, stage)


# Which readiness-spine stage each flow stage's verdict contributes to (R-6). The
# spine remains the sole stage-state authority; the gate only *contributes*
# blocking_reasons[]/warning entries -- it never writes readiness-status.yaml.
_FLOW_TO_SPINE: dict[str, str] = {
    "business_knowledge_interview": "source_ready",
    "kpi_contracts": "semantic_model_ready",
    "silver_gold_model_planning": "silver_ready",
    "semantic_model_dax": "semantic_model_ready",
    "report_intent": "dashboard_ready",
    "dashboard_blueprint": "dashboard_ready",
    "pbip_prototype_readiness": "publish_ready",
    "evidence_pack": "publish_ready",
}


def project_to_spine(verdict: Verdict) -> dict[str, Any]:
    """Project a verdict into the readiness-spine contribution shape (R-6).

    Returns a dict keyed by the spine stage the flow stage feeds, carrying the
    ``status`` word the spine uses (``pass``->``pass``, ``warn``->``warning``,
    ``blocked``->``blocked``) plus ``blocking_reasons``/``evidence``. This is a
    *contribution* the spine may fold in; it is NOT a readiness-status file and
    does not advance any stage on its own (FR-001)."""
    spine_stage = _FLOW_TO_SPINE.get(verdict.stage, verdict.stage)
    status = {"pass": "pass", "warn": "warning", "blocked": "blocked"}[verdict.verdict]
    return {
        "spine_stage": spine_stage,
        "flow_stage": verdict.stage,
        "status": status,
        "blocking_reasons": [f"{b.decision_id}: {b.reason}" for b in verdict.blocking],
        "warnings": list(verdict.warnings),
        "evidence": list(verdict.evidence),
    }
