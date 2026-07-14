"""Create only the human-accepted adoption baseline, never overwriting a target.

Scaffolding is the single small write in this feature.  It re-derives the
assessment immediately before writing, refuses on any drift from the accepted
digest, and publishes the manifest atomically so an interrupted write leaves no
partial file.
"""

from __future__ import annotations

import os
import re
import tempfile
from pathlib import Path
from typing import Any

from ._assess import assess_pbip
from ._safety import (
    MANIFEST_PATH,
    SCHEMA_VERSION,
    PbipAdoptionError,
    _FileRecord,
    _fingerprint,
    _is_within,
    _relative,
    _safe_files,
    _target_path,
)
from ._seams import _default_next_step

_SHA256 = re.compile(r"[a-f0-9]{64}")
_STALE_MESSAGE = (
    "The accepted assessment digest is stale or does not match the current assessment."
)
_EXISTS_MESSAGE = "The adoption manifest already exists and will not be overwritten."
_CLEAN_MESSAGE = (
    "Scaffolding requires a clean existing Git worktree; it never initializes Git."
)
_WRITE_PLAN_MESSAGE = (
    "The assessment does not declare the fixed adoption manifest write plan."
)
_ACCEPT_MESSAGE = "--accept-assessment must be a 64-character lowercase SHA-256 digest."


def _manifest_document(
    assessment: dict[str, Any], records: list[_FileRecord]
) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "assessment_digest": assessment["assessment_digest"],
        "target": assessment["target"],
        "authoritative_inputs": [
            {"artifact": record.artifact, "sha256": record.sha256}
            for record in sorted(records, key=lambda item: item.artifact)
            if record.sha256 is not None
        ],
        "facts": assessment["facts"],
        "next_step": assessment["next_step"],
        "proposals": [
            fact for fact in assessment["facts"] if fact["classification"] == "proposed"
        ],
        "approvals": [],
    }


def _scaffold_refusal(
    outcome: str,
    digest: str | None,
    blockers: list[str],
    next_step: dict[str, Any],
) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "outcome": outcome,
        "assessment_digest": digest,
        "written": [],
        "blocking_reasons": blockers,
        "next_step": next_step,
        "approvals": [],
    }


def _scaffold_written(digest: str, next_step: dict[str, Any]) -> dict[str, Any]:
    # Reuse the single result builder so the emitted shape has one definition;
    # a written result differs only by outcome and the recorded manifest path.
    result = _scaffold_refusal("written", digest, [], next_step)
    result["written"] = [MANIFEST_PATH]
    return result


def _is_safe_existing_dir(root: Path, current: Path) -> bool:
    if current.is_symlink():
        return False
    if not current.is_dir():
        return False
    return _is_within(root, current)


def _ensure_safe_dir(root: Path, current: Path, created: list[Path]) -> None:
    if not current.exists():
        current.mkdir()
        created.append(current)
        return
    if not _is_safe_existing_dir(root, current):
        raise PbipAdoptionError("manifest parent is not a safe contained directory")


def _safe_manifest_parent(root: Path) -> tuple[Path, list[Path]]:
    target = root / Path(MANIFEST_PATH)
    if not _is_within(root, target):
        raise PbipAdoptionError("manifest target resolves outside the selected project")
    created: list[Path] = []
    current = root
    for part in Path(MANIFEST_PATH).parts[:-1]:
        current = current / part
        _ensure_safe_dir(root, current, created)
    return target, created


def _cleanup_empty_directories(directories: list[Path]) -> None:
    for directory in reversed(directories):
        try:
            directory.rmdir()
        except OSError:
            pass


def _load_scaffold_assessment(
    project: Path | str,
) -> tuple[Path, dict[str, Any]] | dict[str, Any]:
    try:
        root, is_pbix = _target_path(project)
    except PbipAdoptionError as exc:
        return _scaffold_refusal("input_defect", None, [str(exc)], _default_next_step())
    if is_pbix:
        assessment = assess_pbip(project)
        return _scaffold_refusal(
            "refused",
            assessment["assessment_digest"],
            ["PBIX must be saved as PBIP before scaffolding."],
            assessment["next_step"],
        )
    try:
        assessment = assess_pbip(root)
    except PbipAdoptionError as exc:
        return _scaffold_refusal("input_defect", None, [str(exc)], _default_next_step())
    return root, assessment


def _acceptance_refusal(
    root: Path, assessment: dict[str, Any], digest: str, accept: str
) -> dict[str, Any] | None:
    next_step = assessment["next_step"]
    if not _SHA256.fullmatch(accept or ""):
        return _scaffold_refusal("input_defect", digest, [_ACCEPT_MESSAGE], next_step)
    if accept != digest:
        return _scaffold_refusal("refused", digest, [_STALE_MESSAGE], next_step)
    target = root / Path(MANIFEST_PATH)
    if target.exists() or target.is_symlink():
        return _scaffold_refusal("refused", digest, [_EXISTS_MESSAGE], next_step)
    if assessment["target"]["version_control"] != "clean":
        return _scaffold_refusal("refused", digest, [_CLEAN_MESSAGE], next_step)
    if assessment["scaffold_plan"]["writes"] != [MANIFEST_PATH]:
        return _scaffold_refusal("refused", digest, [_WRITE_PLAN_MESSAGE], next_step)
    return None


def _reconfirm_assessment(
    root: Path, digest: str, previous_next_step: dict[str, Any]
) -> dict[str, Any]:
    """Re-derive the assessment just before writing; any drift refuses the write."""
    try:
        current = assess_pbip(root)
    except PbipAdoptionError as exc:
        return _scaffold_refusal("input_defect", digest, [str(exc)], previous_next_step)
    if current["assessment_digest"] != digest:
        return _scaffold_refusal(
            "refused",
            current["assessment_digest"],
            [_STALE_MESSAGE],
            current["next_step"],
        )
    return current


def _publish_manifest(rendered: str, target: Path, created: list[Path]) -> str | None:
    """Atomically publish the rendered manifest; return an error name on failure."""
    fd, staging_name = tempfile.mkstemp(
        prefix=".pbip-adoption-", suffix=".tmp", dir=target.parent
    )
    staging = Path(staging_name)
    published = False
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(rendered)
            handle.flush()
            os.fsync(handle.fileno())
        os.link(staging, target)
        published = True
        staging.unlink()
    except OSError as exc:
        try:
            staging.unlink(missing_ok=True)
        finally:
            if published:
                target.unlink(missing_ok=True)
            _cleanup_empty_directories(created)
        return type(exc).__name__
    return None


def _write_manifest(
    root: Path, assessment: dict[str, Any], digest: str
) -> dict[str, Any]:
    next_step = assessment["next_step"]
    records = [
        _fingerprint(root, path)
        for path in _safe_files(root)
        if _relative(root, path) != MANIFEST_PATH
    ]
    try:
        import yaml

        rendered = yaml.safe_dump(
            _manifest_document(assessment, records),
            sort_keys=True,
            allow_unicode=False,
            default_flow_style=False,
        ).replace("\r\n", "\n")
        target, created = _safe_manifest_parent(root)
        if target.exists() or target.is_symlink():
            _cleanup_empty_directories(created)
            return _scaffold_refusal("refused", digest, [_EXISTS_MESSAGE], next_step)
        error = _publish_manifest(rendered, target, created)
    except (OSError, PbipAdoptionError, yaml.YAMLError) as exc:
        name = type(exc).__name__
        reason = f"The adoption manifest could not be prepared safely ({name})."
        return _scaffold_refusal("refused", digest, [reason], next_step)
    if error is not None:
        return _scaffold_refusal(
            "refused",
            digest,
            [f"The adoption manifest could not be published safely ({error})."],
            next_step,
        )
    return _scaffold_written(digest, next_step)


def scaffold_pbip(project: Path | str, accept_assessment: str) -> dict[str, Any]:
    """Create only the accepted adoption baseline, never overwriting a target."""
    loaded = _load_scaffold_assessment(project)
    if not isinstance(loaded, tuple):
        return loaded
    root, assessment = loaded
    digest = assessment["assessment_digest"]
    refusal = _acceptance_refusal(root, assessment, digest, accept_assessment)
    if refusal is not None:
        return refusal
    # Close the assessment-to-write gap: re-evaluate the complete normalized
    # document immediately before preparing the staged file.  Any concurrent
    # input change invalidates the human-accepted digest and creates no target.
    reconfirmed = _reconfirm_assessment(root, digest, assessment["next_step"])
    if "outcome" in reconfirmed:
        return reconfirmed
    return _write_manifest(root, reconfirmed, digest)
