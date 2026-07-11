"""Read-only evidence pack preview.

This module composes a 10-section evidence view from already-committed table
artifacts. It writes no markdown pack files, creates no truth, and grants no
approval.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

_SECTIONS: tuple[dict[str, Any], ...] = (
    {
        "id": "01",
        "name": "source-profile",
        "sources": ("source-profile.md",),
    },
    {
        "id": "02",
        "name": "source-map-summary",
        "sources": ("source-map.yaml",),
    },
    {
        "id": "03",
        "name": "assumptions-and-decisions",
        "sources": ("assumptions.md", "unresolved-questions.md"),
    },
    {
        "id": "04",
        "name": "metric-contracts",
        "sources": ("metrics/*.yaml",),
    },
    {
        "id": "05",
        "name": "validation-summary",
        "sources": ("readiness-status.yaml", "reconciliation-report.md"),
    },
    {
        "id": "06",
        "name": "semantic-model-summary",
        "sources": ("readiness-status.yaml",),
        "stage": "semantic_model_ready",
    },
    {
        "id": "07",
        "name": "dashboard-summary",
        "sources": ("design/*.md",),
    },
    {
        "id": "08",
        "name": "handoff-pack",
        "sources": ("handoff/bi-handoff-pack.md",),
    },
    {
        "id": "09",
        "name": "known-limitations",
        "sources": ("data-issues.md",),
    },
    {
        "id": "10",
        "name": "release-notes",
        "sources": ("release-notes.md", "readiness-status.yaml"),
    },
)


def _load_yaml_mapping(path: Path) -> dict[str, Any] | None:
    import yaml

    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeDecodeError, yaml.YAMLError):
        return None
    if not isinstance(data, dict):
        return None
    return data


def _table_candidate_names(table: str) -> list[str]:
    normalized = table.strip().replace("\\", "/").strip("/")
    names = [normalized, normalized.rsplit(".", 1)[-1]]
    unique: list[str] = []
    for name in names:
        if _candidate_needs_append(name, unique):
            unique.append(name)
    return unique


def _candidate_needs_append(name: str, existing: list[str]) -> bool:
    if not name:
        return False
    if "/" in name:
        return False
    return name not in existing


def _status_path_candidates(root: Path, table: str) -> list[Path]:
    return [
        root / "mappings" / name / "readiness-status.yaml"
        for name in _table_candidate_names(table)
    ]


def _direct_status(root: Path, table: str) -> tuple[Path | None, dict[str, Any] | None]:
    for candidate in _status_path_candidates(root, table):
        if candidate.is_file():
            return candidate, _load_yaml_mapping(candidate)
    return None, None


def _status_names(status_path: Path, data: dict[str, Any]) -> set[str]:
    return {
        status_path.parent.name,
        str(data.get("table") or ""),
        str(data.get("source_id") or ""),
    }


def _matches_status_identity(
    status_path: Path, data: dict[str, Any] | None, table: str
) -> bool:
    if data is None:
        return False
    return table in _status_names(status_path, data)


def _matching_status_by_identity(
    mappings_dir: Path, table: str
) -> tuple[Path | None, dict[str, Any] | None]:
    for status_path in sorted(mappings_dir.glob("*/readiness-status.yaml")):
        data = _load_yaml_mapping(status_path)
        if _matches_status_identity(status_path, data, table):
            return status_path, data
    return None, None


def _find_status(root: Path, table: str) -> tuple[Path | None, dict[str, Any] | None]:
    status_path, data = _direct_status(root, table)
    if status_path is not None:
        return status_path, data

    mappings_dir = root / "mappings"
    if not mappings_dir.is_dir():
        return None, None
    return _matching_status_by_identity(mappings_dir, table)


def _has_unfilled_template_marker(path: Path) -> bool:
    try:
        text = path.read_text(encoding="utf-8-sig")
    except (OSError, UnicodeDecodeError):
        return True
    stripped = text.strip()
    return not stripped or "<placeholder>" in stripped or "`<" in stripped


def _resolve_source(base: Path, pattern: str) -> list[Path]:
    if "*" in pattern:
        return sorted(base.glob(pattern))
    path = base / pattern
    return [path] if path.exists() else []


def _rel(root: Path, path: Path) -> str:
    return path.relative_to(root).as_posix()


def _source_status(root: Path, base: Path, pattern: str) -> tuple[list[str], list[str]]:
    paths = _resolve_source(base, pattern)
    if not paths:
        return [], [f"missing or unfilled source: {_rel(root, base / pattern)}"]

    evidence: list[str] = []
    blockers: list[str] = []
    for path in paths:
        if path.is_file() and not _has_unfilled_template_marker(path):
            evidence.append(_rel(root, path))
        else:
            blockers.append(f"missing or unfilled source: {_rel(root, path)}")
    return evidence, blockers


def _build_section(root: Path, base: Path, spec: dict[str, Any]) -> dict[str, Any]:
    evidence: list[str] = []
    blockers: list[str] = []
    for pattern in spec["sources"]:
        found, missing = _source_status(root, base, pattern)
        evidence.extend(found)
        blockers.extend(missing)
    return {
        "id": spec["id"],
        "name": spec["name"],
        "status": "blocked" if blockers else "pass",
        "sources": evidence,
        "evidence": evidence,
        "blocking_reasons": blockers,
    }


def _valid_owner(owner: object) -> bool:
    from seshat.rules.readiness_status import _owner_is_valid

    return _owner_is_valid(owner)


def _approval_for(data: dict[str, Any], stage: str) -> dict[str, str] | None:
    approvals = data.get("approvals")
    if not isinstance(approvals, list):
        return None
    for item in approvals:
        if not isinstance(item, dict) or item.get("stage") != stage:
            continue
        owner = item.get("owner")
        at = item.get("at")
        if _valid_owner(owner) and isinstance(at, str):
            return {"owner": owner, "at": at}
    return None


def _stage_block(data: dict[str, Any], stage: str) -> dict[str, Any]:
    stages = data.get("stages")
    block = stages.get(stage) if isinstance(stages, dict) else None
    if not isinstance(block, dict):
        return {"status": "not_started", "evidence": [], "blocking_reasons": []}
    return {
        "status": block.get("status") if isinstance(block.get("status"), str) else None,
        "evidence": (
            block.get("evidence") if isinstance(block.get("evidence"), list) else []
        ),
        "blocking_reasons": (
            block.get("blocking_reasons")
            if isinstance(block.get("blocking_reasons"), list)
            else []
        ),
    }


def _input_defect(table: str, detail: str) -> dict[str, Any]:
    return {
        "table": table,
        "source_path": None,
        "current_stage": None,
        "outcome": "input_defect",
        "publish_ready": {
            "status": None,
            "evidence": [],
            "blocking_reasons": [detail],
            "approval": None,
        },
        "sections": [],
        "blockers": [{"section": None, "detail": detail, "source": None}],
        "read_only_proof": True,
    }


def _response_table(data: dict[str, Any], fallback: str) -> str:
    table = data.get("table")
    return table if isinstance(table, str) and table else fallback


def _section_blockers(sections: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "section": section["id"],
            "name": section["name"],
            "detail": reason,
            "source": section["sources"][0] if section["sources"] else None,
        }
        for section in sections
        for reason in section["blocking_reasons"]
    ]


def _pack_response(
    root: Path,
    status_path: Path,
    data: dict[str, Any],
    table: str,
) -> dict[str, Any]:
    sections = [_build_section(root, status_path.parent, spec) for spec in _SECTIONS]
    publish_ready = _stage_block(data, "publish_ready")
    publish_ready["approval"] = _approval_for(data, "publish_ready")

    return {
        "table": _response_table(data, table),
        "source_path": _rel(root, status_path),
        "current_stage": data.get("current_stage"),
        "outcome": "ok",
        "publish_ready": publish_ready,
        "sections": sections,
        "blockers": _section_blockers(sections),
        "read_only_proof": True,
    }


def build_evidence_pack(repo_root: Path | str, table: str) -> dict[str, Any]:
    """Build a read-only evidence pack preview for one table."""
    root = Path(repo_root)
    status_path, data = _find_status(root, table)
    if status_path is None:
        return _input_defect(table, "readiness-status.yaml not found")
    if data is None:
        return _input_defect(table, "readiness-status.yaml is unreadable or malformed")

    return _pack_response(root, status_path, data, table)
