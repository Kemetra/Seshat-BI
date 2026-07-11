"""Portable readiness passports (spec 120, US4): export + non-mutating verify.

A passport is a derived, disclosure-safe snapshot of one or more tables'
committed readiness state plus content identities for the evidence it cites.
It is evidence transport, never authority: it records approvals and statuses
but cannot grant approval or advance a readiness stage (FR-027), and
verification derives a separate result without rewriting the passport or any
source artifact (FR-025/FR-026).
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .artifact_identity import artifact_identity, resolve_within, sha256_file
from .ecosystem_contracts import ContractError, require_supported_schema
from .readiness_projection import build_readiness_projection

SCHEMA_VERSION = "1.0"
AUTHORITY_DISCLAIMER = (
    "This passport records readiness statuses, evidence identities, and "
    "existing approval receipts. It does not grant approval and does not "
    "independently advance readiness."
)
_STAGES = frozenset(
    {
        "source_ready",
        "mapping_ready",
        "silver_ready",
        "gold_ready",
        "semantic_model_ready",
        "dashboard_ready",
        "publish_ready",
    }
)
# Worst-first precedence for the single categorical verification outcome.
_VERDICT_ORDER = ("incompatible", "changed", "missing", "unavailable", "verified")


def _evidence_identity(root: Path, reference: str, *, kind: str) -> dict[str, Any]:
    """Identity for one evidence reference. References that are not workspace
    file paths (live sentinels like ``[PENDING LIVE PROFILE]``, prose) stay in
    the passport as ``unavailable`` -- never fabricated into a file identity."""
    try:
        identity = artifact_identity(root, reference, kind=kind)
    except (ValueError, OSError):
        return {
            "artifact_id": f"{kind}:{reference}",
            "kind": kind,
            "path": reference,
            "sha256": None,
            "verification": "unavailable",
            "note": "evidence reference is not a workspace-relative artifact path",
        }
    if identity["sha256"] is None:
        if reference.startswith("["):
            # A bracketed sentinel records deferred live evidence.
            identity["verification"] = "unavailable"
            identity["note"] = "evidence is recorded as deferred, not as a file"
        elif " " in reference:
            # Prose evidence (a recorded fact, not a file) cannot be hashed.
            identity["verification"] = "unavailable"
            identity["note"] = "evidence is recorded as prose, not as a file"
    return identity


def _valid_receipt_shape(stage: object, owner: object) -> bool:
    return (
        isinstance(stage, str)
        and stage in _STAGES
        and isinstance(owner, str)
        and bool(owner.strip())
    )


def _receipt(item: dict[str, Any], source_path: str) -> dict[str, Any]:
    stage = item.get("stage")
    owner = item.get("owner")
    at = item.get("at")
    return {
        "stage": stage if isinstance(stage, str) else None,
        "owner": owner if isinstance(owner, str) else None,
        "at": str(at) if at is not None else None,
        "source_artifact": source_path,
        "valid_shape": _valid_receipt_shape(stage, owner),
    }


def _approval_receipts(root: Path, source_path: str) -> list[dict[str, Any]]:
    import yaml  # lazy: keep module import stdlib-light (B1/B3)

    try:
        data = yaml.safe_load((root / source_path).read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeDecodeError, yaml.YAMLError):
        return []
    if not isinstance(data, dict) or not isinstance(data.get("approvals"), list):
        return []
    return [
        _receipt(item, source_path)
        for item in data["approvals"]
        if isinstance(item, dict)
    ]


def _readiness_subset(table: dict[str, Any]) -> dict[str, Any]:
    return {
        "table_id": table["table_id"],
        "source_path": table["source_path"],
        "current_stage": table["current_stage"],
        "stages": table["stages"],
        "blocking_reasons": table["blocking_reasons"],
        "next_action": table["next_action"],
    }


def _scope_aliases(
    projected_tables: list[dict[str, Any]],
    available: dict[str, dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    """Recorded table ids plus mappings/<dir>/ names, mirroring how run-next
    resolves a table identity."""
    aliases = dict(available)
    for table in projected_tables:
        directory = table["source_path"].rsplit("/", 2)[-2]
        aliases.setdefault(directory, table)
    return aliases


def _full_scope(available: dict[str, dict[str, Any]]) -> list[str]:
    scope = sorted(available)
    if not scope:
        raise ContractError(
            "passport scope is empty: no readiness-status.yaml is committed"
        )
    return scope


def _resolve_scope(
    projected_tables: list[dict[str, Any]],
    available: dict[str, dict[str, Any]],
    requested: list[str] | None,
) -> list[str]:
    """Canonical table-id scope for the passport (FR-023)."""
    if not requested:
        return _full_scope(available)
    aliases = _scope_aliases(projected_tables, available)
    unknown = [name for name in requested if name not in aliases]
    if unknown:
        raise ContractError(
            "unknown table in passport scope: " + ", ".join(sorted(unknown))
        )
    return sorted({aliases[name]["table_id"] for name in requested})


def _table_artifacts(
    root: Path, table: dict[str, Any]
) -> list[tuple[tuple[str, str], dict[str, Any]]]:
    status_identity = artifact_identity(
        root, table["source_path"], kind="readiness_status"
    )
    entries = [(("readiness_status", status_identity["path"]), status_identity)]
    for stage_block in table["stages"].values():
        for reference in stage_block["evidence"]:
            identity = _evidence_identity(root, str(reference), kind="evidence")
            entries.append((("evidence", identity["path"]), identity))
    return entries


def _collect_scope(
    root: Path, scope: list[str], available: dict[str, dict[str, Any]]
) -> tuple[list[dict[str, Any]], dict[tuple[str, str], dict[str, Any]], list[dict]]:
    readiness: list[dict[str, Any]] = []
    artifacts: dict[tuple[str, str], dict[str, Any]] = {}
    approvals: list[dict[str, Any]] = []
    for table_id in scope:
        table = available[table_id]
        readiness.append(_readiness_subset(table))
        for key, identity in _table_artifacts(root, table):
            artifacts.setdefault(key, identity)
        approvals.extend(_approval_receipts(root, table["source_path"]))
    return readiness, artifacts, approvals


def build_passport(
    repo_root: Path | str = ".",
    *,
    tables: list[str] | None = None,
    generated_at: str | None = None,
) -> dict[str, Any]:
    """Assemble one passport for an explicit table scope (FR-023/FR-024).

    Deterministic for identical committed inputs except ``generated_at``;
    ``passport_id`` is derived from the content digest and therefore excludes
    the generation time. Read-only: no file is written here.
    """
    root = Path(repo_root).resolve()
    projection = build_readiness_projection(root)
    available = {table["table_id"]: table for table in projection["tables"]}
    scope = _resolve_scope(projection["tables"], available, tables)
    readiness, artifacts, approvals = _collect_scope(root, scope, available)
    body = {
        "schema_version": SCHEMA_VERSION,
        "source_revision": projection["workspace"]["source_revision"],
        "scope": scope,
        "readiness": readiness,
        "artifacts": [
            artifacts[key] for key in sorted(artifacts, key=lambda item: item[1])
        ],
        "approvals": approvals,
        "validation_boundary": {
            "static": (
                "readiness statuses, evidence identities, and approval receipts "
                "were read from committed workspace files"
            ),
            "live": "unavailable",
            "unavailable_checks": [
                "live_database_validation",
                "powerbi_semantic_validation",
            ],
        },
        "authority_disclaimer": AUTHORITY_DISCLAIMER,
    }
    digest = hashlib.sha256(
        json.dumps(body, sort_keys=True, ensure_ascii=True).encode("utf-8")
    ).hexdigest()
    return {
        **body,
        "passport_id": f"passport-{digest[:16]}",
        "generated_at": generated_at
        or datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }


def _verify_artifact(root: Path, entry: object) -> dict[str, Any]:
    if not isinstance(entry, dict) or not isinstance(entry.get("path"), str):
        return {
            "artifact_id": None,
            "path": None,
            "verification": "incompatible",
            "note": "artifact entry is not interpretable",
        }
    result = {
        "artifact_id": entry.get("artifact_id"),
        "path": entry["path"],
        "verification": "verified",
        "note": None,
    }
    recorded = entry.get("sha256")
    if recorded is None:
        result["verification"] = "unavailable"
        result["note"] = "the passport recorded no content hash for this artifact"
        return result
    try:
        target = resolve_within(root, entry["path"])
    except (ValueError, OSError):
        result["verification"] = "incompatible"
        result["note"] = "artifact path does not stay within the workspace"
        return result
    if not target.is_file():
        result["verification"] = "missing"
        result["note"] = "artifact is not available in the workspace"
        return result
    if sha256_file(target) != recorded:
        result["verification"] = "changed"
        result["note"] = "artifact content no longer matches the recorded hash"
    return result


def _incompatible_result(passport_id: object, note: str) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "passport_id": passport_id,
        "outcome": "incompatible",
        "artifacts": [],
        "note": note,
    }


def _revision_comparison(recorded: object, current: object) -> dict[str, Any]:
    match = None if recorded is None or current is None else recorded == current
    return {
        "source_revision_recorded": recorded,
        "source_revision_current": current,
        "source_revision_match": match,
    }


def _checked_artifacts(root: Path, passport: dict[str, Any]) -> list[dict[str, Any]]:
    artifacts = passport.get("artifacts")
    if not isinstance(artifacts, list):
        return []
    return [_verify_artifact(root, entry) for entry in artifacts]


def verify_passport(repo_root: Path | str, passport: object) -> dict[str, Any]:
    """Non-mutating verification (FR-025/FR-026, SC-005): re-derive each
    artifact identity and report verified / changed / missing / incompatible /
    unavailable distinctly, plus one worst-first categorical outcome. The
    passport document and the workspace are never modified."""
    root = Path(repo_root).resolve()
    if not isinstance(passport, dict):
        return _incompatible_result(None, "passport document is not interpretable")
    try:
        require_supported_schema(passport)
    except ContractError as exc:
        return _incompatible_result(passport.get("passport_id"), str(exc))
    checked = _checked_artifacts(root, passport)
    seen = {item["verification"] for item in checked}
    outcome = next(
        (verdict for verdict in _VERDICT_ORDER if verdict in seen), "verified"
    )
    projection = build_readiness_projection(root)
    return {
        "schema_version": SCHEMA_VERSION,
        "passport_id": passport.get("passport_id"),
        "outcome": outcome,
        "artifacts": checked,
        **_revision_comparison(
            passport.get("source_revision"),
            projection["workspace"]["source_revision"],
        ),
        "note": None,
    }
