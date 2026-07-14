"""Assemble and finalize a read-only PBIP adoption assessment.

``assess_pbip`` never writes: it composes discovery, governance, readiness, and
fingerprint-baseline reassessment into one normalized, digest-stamped document
whose disclosure surface has been validated before it is returned.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from ..disclosure import scan_disclosure
from ._boundaries import _add_missing_governance_facts, _scan_literal_boundaries
from ._discovery import _discover_pbip
from ._facts import _component_fact, _Fact
from ._safety import (
    MANIFEST_PATH,
    SCHEMA_VERSION,
    PbipAdoptionError,
    _FileRecord,
    _git_state,
    _safe_files,
    _safe_name,
    _target_path,
    canonical_assessment_digest,
)
from ._seams import (
    _governance_findings,
    _next_step,
    _NextStepInputs,
    _readiness,
)

_SHA256 = re.compile(r"[a-f0-9]{64}")


def _read_manifest(path: Path) -> Any:
    try:
        import yaml

        return yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, yaml.YAMLError):
        return None


def _add_baseline_entry(result: dict[str, str], entry: dict[str, Any]) -> None:
    artifact = entry.get("artifact")
    digest = entry.get("sha256")
    if not isinstance(artifact, str) or not isinstance(digest, str):
        return
    if _SHA256.fullmatch(digest):
        result[artifact] = digest


def _baseline_entries(raw: list[Any]) -> dict[str, str]:
    result: dict[str, str] = {}
    for entry in raw:
        if isinstance(entry, dict):
            _add_baseline_entry(result, entry)
    return result


def _load_baseline(root: Path) -> tuple[dict[str, str] | None, str]:
    """Return ``(baseline, status)`` where status is absent/usable/unusable.

    An adoption manifest that exists but cannot be parsed into a fingerprint
    baseline is reported as ``unusable`` -- never silently treated as absent --
    so reassessment fails closed with a recorded blocker.
    """
    path = root / Path(MANIFEST_PATH)
    if not path.is_file():
        return None, "absent"
    parsed = _read_manifest(path)
    raw = parsed.get("authoritative_inputs") if isinstance(parsed, dict) else None
    if not isinstance(raw, list):
        return None, "unusable"
    return _baseline_entries(raw), "usable"


def _unusable_baseline_fact() -> _Fact:
    return _Fact(
        id="blocked:adoption-baseline-unusable",
        classification="blocked",
        category="readiness",
        subject="adoption baseline",
        detail="An adoption manifest exists but could not be read as a valid "
        "fingerprint baseline; committed inputs cannot be compared.",
        artifact=MANIFEST_PATH,
        reason="The committed adoption manifest is unreadable or malformed.",
        required_authority="data_owner",
    )


def _changes_from_baseline(
    baseline: dict[str, str] | None, records: list[_FileRecord]
) -> list[dict[str, Any]]:
    if baseline is None:
        return []
    current = {
        record.artifact: record.sha256
        for record in records
        if record.sha256 is not None
    }
    changes: list[dict[str, Any]] = []
    for artifact in sorted(set(baseline) | set(current)):
        before, after = baseline.get(artifact), current.get(artifact)
        if before is None:
            kind = "added"
        elif after is None:
            kind = "removed"
        elif before == after:
            kind = "unchanged"
        else:
            kind = "changed"
        changes.append(
            {
                "kind": kind,
                "artifact": artifact,
                "previous_sha256": before,
                "current_sha256": after,
                "classification": "observed" if kind == "unchanged" else "blocked",
            }
        )
    return changes


def _coverage(components: list[dict[str, Any]]) -> dict[str, Any]:
    counts = {
        name: 0
        for name in ("supported", "unsupported", "unreadable", "missing", "ambiguous")
    }
    for component in components:
        support = component.get("support")
        if support in counts:
            counts[support] += 1
    status = (
        "complete"
        if counts["supported"]
        and not any(
            counts[name]
            for name in ("unsupported", "unreadable", "missing", "ambiguous")
        )
        else "partial"
    )
    if not counts["supported"]:
        status = "blocked"
    return {"status": status, **counts}


def _finalize(assessment: dict[str, Any]) -> dict[str, Any]:
    assessment["facts"].sort(key=lambda item: item["id"])
    assessment["governance_findings"].sort(
        key=lambda item: (item["rule_id"], item["locator"], item["message"])
    )
    assessment["target"]["components"].sort(
        key=lambda item: (item["kind"], item["artifact"], item["identity"])
    )
    assessment["changes"].sort(key=lambda item: item["artifact"])
    disclosure = scan_disclosure(
        {
            key: value
            for key, value in assessment.items()
            if key not in {"disclosure", "assessment_digest"}
        }
    )
    assessment["disclosure"] = {
        "status": disclosure["status"],
        "findings": disclosure["findings"],
    }
    if disclosure["status"] != "pass":
        raise PbipAdoptionError(
            "assessment disclosure validation blocked unsafe output"
        )
    assessment["assessment_digest"] = canonical_assessment_digest(assessment)
    return assessment


def _pbix_assessment(root: Path) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "target": {
            "kind": "pbix_unsupported",
            "label": _safe_name(root.name, fallback="PBIX file"),
            "version_control": _git_state(root.parent),
            "components": [],
        },
        "coverage": {
            "status": "blocked",
            "supported": 0,
            "unsupported": 1,
            "unreadable": 0,
            "missing": 0,
            "ambiguous": 0,
        },
        "facts": [
            _Fact(
                id="unavailable:pbix",
                classification="unavailable_with_reason",
                category="coverage",
                subject="PBIX binary",
                detail="PBIX input is a supported boundary: save it as a PBIP "
                "before assessment.",
                artifact=root.name,
                reason="PBIX binaries are not parsed or modified in v1.",
            ).as_dict()
        ],
        "governance_findings": [],
        "readiness": [],
        "changes": [],
        "scaffold_plan": {
            "writes": [],
            "preconditions": ["PBIX must first be saved as a PBIP project."],
            "approvals": [],
        },
        "next_step": _next_step(
            _NextStepInputs("pbix_unsupported", "clean", [], [], [])
        ),
        "disclosure": {"status": "pass", "findings": []},
        "assessment_digest": "",
    }


def _project_assessment(root: Path) -> dict[str, Any]:
    files = _safe_files(root)
    components, discovered_facts, records = _discover_pbip(root, files)
    fact_objs: list[_Fact] = [
        *discovered_facts,
        *(_component_fact(component) for component in components),
    ]
    _add_missing_governance_facts(root, fact_objs)
    _scan_literal_boundaries(root, records, fact_objs)
    governance_findings, governance_facts = _governance_findings(root)
    fact_objs.extend(governance_facts)
    baseline, baseline_status = _load_baseline(root)
    if baseline_status == "unusable":
        fact_objs.append(_unusable_baseline_fact())
    facts = [fact.as_dict() for fact in fact_objs]
    readiness, blockers = _readiness(root)
    state = _git_state(root)
    return {
        "schema_version": SCHEMA_VERSION,
        "target": {
            "kind": "pbip_project",
            "label": _safe_name(root.name, fallback="PBIP project"),
            "version_control": state,
            "components": components,
        },
        "coverage": _coverage(components),
        "facts": facts,
        "governance_findings": governance_findings,
        "readiness": readiness,
        "changes": _changes_from_baseline(baseline, records),
        "scaffold_plan": {
            "writes": [MANIFEST_PATH],
            "preconditions": [
                "existing clean Git worktree",
                "exact current assessment digest",
                "contained absent manifest target",
            ],
            "approvals": [],
        },
        "next_step": _next_step(
            _NextStepInputs("pbip_project", state, facts, readiness, blockers)
        ),
        "disclosure": {"status": "pass", "findings": []},
        "assessment_digest": "",
    }


def assess_pbip(project: Path | str) -> dict[str, Any]:
    """Assess one PBIP directory without changing it.

    ``PbipAdoptionError`` represents an unsafe or invalid input shape.  The CLI
    turns it into a concise exit-2 response; library callers can make the same
    distinction without parsing printed output.
    """
    root, is_pbix = _target_path(project)
    if is_pbix:
        return _finalize(_pbix_assessment(root))
    return _finalize(_project_assessment(root))
