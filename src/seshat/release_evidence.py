"""Fail-closed validators for public-distribution evidence records.

These helpers validate evidence shape only. They never grant approval, publish
an artifact, or convert a factual check into a readiness score.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Mapping

_SEMVER = re.compile(
    r"^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)"
    r"(?:-[0-9A-Za-z.-]+)?(?:\+[0-9A-Za-z.-]+)?$"
)
_FULL_SHA = re.compile(r"^[0-9a-f]{40}$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_PROHIBITED_SCORE_KEYS = {
    "confidence",
    "confidence_score",
    "readiness_score",
    "score",
}

PUBLICATION_ACTIONS = {
    "configure_pypi_trusted_publisher",
    "publish_pypi",
    "publish_github_release",
    "publish_claude_marketplace",
    "submit_claude_catalog",
    "create_release_tag",
    "rollback_pypi",
    "rollback_github_release",
    "rollback_claude_marketplace",
    "rollback_claude_catalog",
    "rollback_codex_marketplace",
    "submit_openai_plugin",
    "publish_openai_plugin",
    "rollback_openai_plugin",
}

PUBLIC_SURFACES = {
    "python_pypi",
    "claude_repository",
    "codex_repository",
    "claude_public_catalog",
    "openai_public_plugin",
}
COORDINATED_REQUIRED_SURFACES = {
    "python_pypi",
    "claude_repository",
    "codex_repository",
}
ROLLBACK_ACTIONS_BY_SURFACE = {
    "python_pypi": {"rollback_pypi"},
    "claude_repository": {"rollback_claude_marketplace"},
    "codex_repository": {"rollback_codex_marketplace"},
    "claude_public_catalog": {"rollback_claude_catalog"},
    "openai_public_plugin": {"rollback_openai_plugin"},
}


class EvidenceValidationError(ValueError):
    """Evidence is incomplete, ambiguous, or outside the safe contract."""


@dataclass(frozen=True)
class ApprovalScope:
    candidate_id: str | None = None
    version: str | None = None
    source_revision: str | None = None
    artifact_digests: Mapping[str, str] | None = None
    action: str | None = None


@dataclass(frozen=True)
class AuthorizationRequest:
    scope: ApprovalScope
    used_approval_ids: set[str] | frozenset[str] = frozenset()
    at: datetime | None = None


@dataclass(frozen=True)
class RollbackAuthorizationRequest:
    version: str
    source_revision: str
    artifact_digests: Mapping[str, str]
    used_approval_ids: set[str] | frozenset[str] = frozenset()
    at: datetime | None = None


def _require_mapping(record: object, label: str) -> Mapping[str, Any]:
    if not isinstance(record, Mapping):
        raise EvidenceValidationError(f"{label} must be an object")
    return record


def _require_fields(record: Mapping[str, Any], fields: set[str]) -> None:
    missing = sorted(field for field in fields if field not in record)
    if missing:
        raise EvidenceValidationError(f"missing required fields: {', '.join(missing)}")


def _non_empty_text(value: object, error: str) -> str:
    if not isinstance(value, str):
        raise EvidenceValidationError(error)
    if not value.strip():
        raise EvidenceValidationError(error)
    return value


def _require_text(record: Mapping[str, Any], field: str) -> str:
    return _non_empty_text(record.get(field), f"{field} must be non-empty text")


def _require_timestamp(record: Mapping[str, Any], field: str) -> datetime:
    value = _require_text(record, field)
    if not value.endswith("Z"):
        raise EvidenceValidationError(f"{field} must be an ISO-8601 UTC timestamp")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise EvidenceValidationError(
            f"{field} must be an ISO-8601 UTC timestamp"
        ) from exc
    if parsed.tzinfo != timezone.utc:
        raise EvidenceValidationError(f"{field} must be UTC")
    return parsed


def _require_artifact_digests(
    record: Mapping[str, Any], field: str = "artifact_digests"
) -> Mapping[str, str]:
    value = record.get(field)
    if not isinstance(value, Mapping):
        raise EvidenceValidationError(f"{field} must be a non-empty object")
    if not value:
        raise EvidenceValidationError(f"{field} must be a non-empty object")
    for name, digest in value.items():
        _validate_artifact_digest(name, digest, field)
    return value


def _validate_artifact_digest(name: object, digest: object, field: str) -> None:
    error = f"{field} contains an invalid entry"
    validated_name = _non_empty_text(name, error)
    validated_digest = _non_empty_text(digest, error)
    if _SHA256.fullmatch(validated_digest) is None:
        raise EvidenceValidationError(
            f"artifact digest for {validated_name} must be SHA-256"
        )


def _concrete_text(value: object, field: str) -> str:
    return _non_empty_text(value, f"{field} must be a list of concrete strings")


def _require_text_list(
    record: Mapping[str, Any], field: str, *, allow_empty: bool = False
) -> list[str]:
    value = record.get(field)
    if not isinstance(value, list):
        raise EvidenceValidationError(f"{field} must be a list of concrete strings")
    result = [_concrete_text(item, field) for item in value]
    if result:
        return result
    if allow_empty:
        return result
    raise EvidenceValidationError(f"{field} must not be empty")


def _reject_mapping_scores(value: Mapping[object, object], path: str) -> None:
    for key, child in value.items():
        if str(key).lower() in _PROHIBITED_SCORE_KEYS:
            raise EvidenceValidationError(
                f"{path}.{key} is prohibited; evidence uses status and blockers"
            )
        _reject_scores(child, f"{path}.{key}")


def _reject_list_scores(value: list[object], path: str) -> None:
    for index, child in enumerate(value):
        _reject_scores(child, f"{path}[{index}]")


def _reject_scores(value: object, path: str = "$") -> None:
    if isinstance(value, Mapping):
        _reject_mapping_scores(value, path)
        return
    if isinstance(value, list):
        _reject_list_scores(value, path)


def _validate_status_and_blockers(
    record: Mapping[str, Any], *, allowed: set[str]
) -> None:
    status = record.get("status")
    if status not in allowed:
        raise EvidenceValidationError(
            f"status must be one of: {', '.join(sorted(allowed))}"
        )
    blockers = _require_text_list(record, "blockers", allow_empty=True)
    _require_failure_blockers(status, blockers)
    _reject_success_blockers(status, blockers)


def _require_failure_blockers(status: object, blockers: list[str]) -> None:
    if status not in {"blocked", "fail"}:
        return
    if not blockers:
        raise EvidenceValidationError(f"{status} evidence requires concrete blockers")


def _reject_success_blockers(status: object, blockers: list[str]) -> None:
    if status not in {"validated", "pass", "approved", "completed"}:
        return
    if blockers:
        raise EvidenceValidationError(f"{status} evidence cannot retain blockers")


def validate_release_candidate(record: object) -> Mapping[str, Any]:
    """Validate a release-candidate evidence record and return it unchanged."""

    item = _require_mapping(record, "release candidate")
    _reject_scores(item)
    _require_fields(
        item,
        {
            "schema_version",
            "candidate_id",
            "version",
            "source_revision",
            "artifact_digests",
            "status",
            "blockers",
            "created_at",
            "authority_disclaimer",
        },
    )
    if item.get("schema_version") != "1.0":
        raise EvidenceValidationError("schema_version must be 1.0")
    _require_text(item, "candidate_id")
    version = _require_text(item, "version")
    if _SEMVER.fullmatch(version) is None:
        raise EvidenceValidationError("version must be SemVer")
    revision = _require_text(item, "source_revision")
    if _FULL_SHA.fullmatch(revision) is None:
        raise EvidenceValidationError(
            "source_revision must be a full lowercase Git SHA"
        )
    _require_artifact_digests(item)
    _validate_status_and_blockers(item, allowed={"blocked", "validated"})
    _require_timestamp(item, "created_at")
    _require_text(item, "authority_disclaimer")
    return item


def _require_acceptance_booleans(item: Mapping[str, Any]) -> None:
    for field in (
        "fresh_workspace",
        "development_repo_available",
        "human_gate_observed",
        "secrets_or_pii_exposed",
        "fabricated_score",
    ):
        if not isinstance(item.get(field), bool):
            raise EvidenceValidationError(f"{field} must be boolean")


def _require_acceptance_state(
    item: Mapping[str, Any], field: str, expected: bool, error: str
) -> None:
    if item.get(field) is not expected:
        raise EvidenceValidationError(error)


def _validate_acceptance_safety(item: Mapping[str, Any]) -> None:
    _require_acceptance_state(
        item,
        "fresh_workspace",
        True,
        "acceptance must use a fresh workspace",
    )
    _require_acceptance_state(
        item,
        "development_repo_available",
        False,
        "acceptance must hide the development repository",
    )
    _require_acceptance_state(
        item,
        "secrets_or_pii_exposed",
        False,
        "acceptance exposed secrets or PII",
    )
    _require_acceptance_state(
        item,
        "fabricated_score",
        False,
        "acceptance fabricated a readiness score",
    )


def _require_acceptance_text(item: Mapping[str, Any]) -> None:
    for field in (
        "run_id",
        "candidate_id",
        "client",
        "fixture_id",
        "observed_stage",
        "next_action",
    ):
        _require_text(item, field)


def validate_external_acceptance(record: object) -> Mapping[str, Any]:
    """Validate one external Claude/Codex acceptance observation."""

    item = _require_mapping(record, "external acceptance")
    _reject_scores(item)
    _require_fields(
        item,
        {
            "schema_version",
            "run_id",
            "candidate_id",
            "platform",
            "client",
            "fresh_workspace",
            "development_repo_available",
            "fixture_id",
            "observed_stage",
            "next_action",
            "human_gate_observed",
            "secrets_or_pii_exposed",
            "fabricated_score",
            "status",
            "blockers",
            "recorded_at",
        },
    )
    if item.get("schema_version") != "1.0":
        raise EvidenceValidationError("schema_version must be 1.0")
    if item.get("platform") not in {"claude-code", "codex"}:
        raise EvidenceValidationError("platform must be claude-code or codex")
    _require_acceptance_booleans(item)
    _validate_acceptance_safety(item)
    _require_acceptance_text(item)
    _validate_status_and_blockers(item, allowed={"fail", "pass"})
    _require_timestamp(item, "recorded_at")
    return item


def _validate_approval_scope(item: Mapping[str, Any], scope: ApprovalScope) -> None:
    expected = {
        "candidate_id": scope.candidate_id,
        "version": scope.version,
        "source_revision": scope.source_revision,
        "action": scope.action,
    }
    for field, value in expected.items():
        _validate_scope_field(item, field, value)


def _validate_scope_field(
    item: Mapping[str, Any], field: str, expected: str | None
) -> None:
    if expected is None:
        return
    if item.get(field) != expected:
        raise EvidenceValidationError(
            f"approval {field} does not match the requested action scope"
        )


def _validate_approval_digests(
    recorded: Mapping[str, str], expected: Mapping[str, str] | None
) -> None:
    if expected is None:
        return
    if dict(recorded) != dict(expected):
        raise EvidenceValidationError(
            "approval artifact_digests do not match the requested action scope"
        )


def _require_semver(item: Mapping[str, Any], field: str = "version") -> str:
    version = _require_text(item, field)
    if _SEMVER.fullmatch(version) is None:
        raise EvidenceValidationError(f"{field} must be SemVer")
    return version


def _require_revision(item: Mapping[str, Any]) -> str:
    revision = _require_text(item, "source_revision")
    if _FULL_SHA.fullmatch(revision) is None:
        raise EvidenceValidationError(
            "source_revision must be a full lowercase Git SHA"
        )
    return revision


def _require_approval_text(item: Mapping[str, Any]) -> None:
    for field in (
        "approval_id",
        "candidate_id",
        "approver",
        "scope",
        "authority_disclaimer",
    ):
        _require_text(item, field)


def _validate_approval_action(item: Mapping[str, Any]) -> None:
    action = _require_text(item, "action")
    if action not in PUBLICATION_ACTIONS:
        raise EvidenceValidationError("action is not an allowed owner-only action")


def _validate_approval_window(item: Mapping[str, Any]) -> None:
    approved_at = _require_timestamp(item, "approved_at")
    expires_at = _require_timestamp(item, "expires_at")
    if expires_at <= approved_at:
        raise EvidenceValidationError("expires_at must be later than approved_at")


def validate_publication_approval(
    record: object, scope: ApprovalScope | None = None
) -> Mapping[str, Any]:
    """Validate exact, named, action-scoped publication authority."""

    item = _require_mapping(record, "publication approval")
    _reject_scores(item)
    _require_fields(
        item,
        {
            "schema_version",
            "approval_id",
            "candidate_id",
            "version",
            "source_revision",
            "artifact_digests",
            "action",
            "approver",
            "scope",
            "evidence_reviewed",
            "constraints",
            "approved_at",
            "expires_at",
            "status",
            "authority_disclaimer",
        },
    )
    if item.get("schema_version") != "1.0":
        raise EvidenceValidationError("schema_version must be 1.0")
    _require_approval_text(item)
    _require_semver(item)
    _require_revision(item)
    recorded_digests = _require_artifact_digests(item)
    _validate_approval_action(item)
    if item.get("status") != "approved":
        raise EvidenceValidationError("status must be approved")
    _validate_approval_window(item)
    _require_text_list(item, "evidence_reviewed")
    _require_text_list(item, "constraints", allow_empty=True)
    resolved_scope = scope or ApprovalScope()
    _validate_approval_scope(item, resolved_scope)
    _validate_approval_digests(recorded_digests, resolved_scope.artifact_digests)
    return item


def _require_complete_authorization_scope(scope: ApprovalScope) -> None:
    required = {
        "candidate_id": scope.candidate_id,
        "version": scope.version,
        "source_revision": scope.source_revision,
        "artifact_digests": scope.artifact_digests,
        "action": scope.action,
    }
    missing = sorted(field for field, value in required.items() if value is None)
    if missing:
        raise EvidenceValidationError(
            "authorization request must bind the exact action scope; missing: "
            + ", ".join(missing)
        )


def validate_action_authorization(
    record: object, request: AuthorizationRequest
) -> Mapping[str, Any]:
    """Validate a still-current, unused approval for one exact action."""

    _require_complete_authorization_scope(request.scope)
    item = validate_publication_approval(record, request.scope)
    approval_id = str(item["approval_id"])
    if approval_id in request.used_approval_ids:
        raise EvidenceValidationError(
            "approval was already consumed and cannot authorize another action"
        )
    checked_at = request.at or datetime.now(timezone.utc)
    expires_at = _require_timestamp(item, "expires_at")
    if expires_at <= checked_at:
        raise EvidenceValidationError("approval has expired")
    return item


_SURFACE_STATUSES = {"available", "unavailable", "unverified", "blocked"}


def _validate_surface(name: str, raw: object) -> Mapping[str, Any]:
    surface = _require_mapping(raw, f"surface {name}")
    status = surface.get("status")
    if status not in _SURFACE_STATUSES:
        raise EvidenceValidationError(
            f"surface {name} status must be available, unavailable, "
            "unverified, or blocked"
        )
    _require_surface_reason(name, status, surface.get("reason"))
    return surface


def _require_surface_reason(name: str, status: object, reason: object) -> None:
    if status == "available":
        return
    if not isinstance(reason, str):
        raise EvidenceValidationError(
            f"surface {name} {status} status requires a concrete reason"
        )
    if not reason.strip():
        raise EvidenceValidationError(
            f"surface {name} {status} status requires a concrete reason"
        )


def _validate_surfaces(item: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    raw_surfaces = _require_mapping(item.get("surfaces"), "surfaces")
    if set(raw_surfaces) != PUBLIC_SURFACES:
        raise EvidenceValidationError("availability must name every public surface")
    return {name: _validate_surface(name, raw) for name, raw in raw_surfaces.items()}


def _required_surfaces_available(
    surfaces: Mapping[str, Mapping[str, Any]],
) -> bool:
    return all(
        surfaces[name].get("status") == "available"
        for name in COORDINATED_REQUIRED_SURFACES
    )


def _validate_coordinated_claim(
    item: Mapping[str, Any], surfaces: Mapping[str, Mapping[str, Any]]
) -> None:
    coordinated = item.get("coordinated_release_status")
    if coordinated not in _SURFACE_STATUSES:
        raise EvidenceValidationError("coordinated_release_status is invalid")
    required_available = _required_surfaces_available(surfaces)
    _require_coordinated_surfaces(coordinated, required_available)
    _reject_full_launch_claim(_require_text(item, "summary"), required_available)


def _require_coordinated_surfaces(
    coordinated: object, required_available: bool
) -> None:
    if coordinated != "available":
        return
    if not required_available:
        raise EvidenceValidationError(
            "coordinated release cannot be available while a required surface is not"
        )


def _reject_full_launch_claim(summary: str, required_available: bool) -> None:
    if required_available:
        return
    if "full launch" in summary.casefold():
        raise EvidenceValidationError(
            "partial availability must not be described as a full launch"
        )


def validate_surface_availability(record: object) -> Mapping[str, Any]:
    """Validate truthful per-surface availability and coordinated wording."""

    item = _require_mapping(record, "surface availability")
    _reject_scores(item)
    _require_fields(
        item,
        {
            "schema_version",
            "surfaces",
            "coordinated_release_status",
            "summary",
        },
    )
    if item.get("schema_version") != "1.0":
        raise EvidenceValidationError("schema_version must be 1.0")
    _validate_coordinated_claim(item, _validate_surfaces(item))
    return item


def _require_rollback_text(item: Mapping[str, Any]) -> None:
    for field in (
        "rollback_id",
        "candidate_id",
        "surface",
        "trigger",
        "actor",
        "action",
        "approval_id",
    ):
        _require_text(item, field)


def _validate_rollback_action(item: Mapping[str, Any]) -> None:
    surface = _require_text(item, "surface")
    if surface not in ROLLBACK_ACTIONS_BY_SURFACE:
        raise EvidenceValidationError("rollback surface is not a public surface")
    action = str(item.get("action"))
    if action not in PUBLICATION_ACTIONS:
        raise EvidenceValidationError(
            "rollback action must match the affected public surface"
        )
    if action not in ROLLBACK_ACTIONS_BY_SURFACE[surface]:
        raise EvidenceValidationError(
            "rollback action must match the affected public surface"
        )


def validate_rollback_record(record: object) -> Mapping[str, Any]:
    """Validate rollback evidence without treating rollback as self-authorizing."""

    item = _require_mapping(record, "rollback record")
    _reject_scores(item)
    _require_fields(
        item,
        {
            "schema_version",
            "rollback_id",
            "candidate_id",
            "surface",
            "trigger",
            "actor",
            "action",
            "status",
            "blockers",
            "recorded_at",
            "approval_id",
        },
    )
    if item.get("schema_version") != "1.0":
        raise EvidenceValidationError("schema_version must be 1.0")
    _require_rollback_text(item)
    _validate_rollback_action(item)
    _validate_status_and_blockers(item, allowed={"blocked", "completed"})
    _require_timestamp(item, "recorded_at")
    return item


def validate_rollback_authorization(
    rollback_record: object,
    approval_record: object,
    request: RollbackAuthorizationRequest,
) -> tuple[Mapping[str, Any], Mapping[str, Any]]:
    """Bind rollback evidence to a fresh approval for that affected surface."""

    rollback = validate_rollback_record(rollback_record)
    approval = validate_action_authorization(
        approval_record,
        AuthorizationRequest(
            scope=ApprovalScope(
                candidate_id=str(rollback["candidate_id"]),
                version=request.version,
                source_revision=request.source_revision,
                artifact_digests=request.artifact_digests,
                action=str(rollback["action"]),
            ),
            used_approval_ids=request.used_approval_ids,
            at=request.at,
        ),
    )
    if rollback.get("approval_id") != approval.get("approval_id"):
        raise EvidenceValidationError(
            "rollback record approval_id does not match its action-scoped approval"
        )
    return rollback, approval
