"""Workspace fixtures for the Studio projection tests (T009).

The five states T009 names: ready, blocked, empty, pending-live, and malformed. Each
builder writes a real committed workspace on disk, because the projection's whole job
is reading committed YAML -- a mocked loader would test the mock.

Kept out of the test module so the same fixtures serve T010's parity assertions and
T011's endpoint tests without being rebuilt.
"""

from __future__ import annotations

from pathlib import Path

_STAGES = (
    "source_ready",
    "mapping_ready",
    "silver_ready",
    "gold_ready",
    "semantic_model_ready",
    "dashboard_ready",
    "publish_ready",
)


def _workspace(root: Path) -> Path:
    """A directory the shipped `looks_like_workspace` recognizer accepts."""
    (root / ".seshat").mkdir(parents=True, exist_ok=True)
    (root / "mappings").mkdir(parents=True, exist_ok=True)
    return root


def _stage_block(status: str, *, evidence: list[str], blockers: list[str]) -> str:
    lines = [f'    status: "{status}"']
    if evidence:
        lines.append("    evidence:")
        lines.extend(f'      - "{item}"' for item in evidence)
    else:
        lines.append("    evidence: []")
    if blockers:
        lines.append("    blocking_reasons:")
        lines.extend(f'      - "{item}"' for item in blockers)
    else:
        lines.append("    blocking_reasons: []")
    return "\n".join(lines)


def _readiness_document(
    table: str,
    *,
    current_stage: str | None,
    statuses: dict[str, str],
    evidence: dict[str, list[str]] | None = None,
    blockers: dict[str, list[str]] | None = None,
) -> str:
    evidence = evidence or {}
    blockers = blockers or {}
    head = [f'table: "{table}"']
    if current_stage is not None:
        head.append(f'current_stage: "{current_stage}"')
    head.append("stages:")
    body = []
    for stage in _STAGES:
        body.append(f"  {stage}:")
        body.append(
            _stage_block(
                statuses.get(stage, "not_started"),
                evidence=evidence.get(stage, []),
                blockers=blockers.get(stage, []),
            )
        )
    return "\n".join(head + body) + "\n"


def write_ready_table(root: Path, table: str = "ready_sales") -> Path:
    """Every stage `pass` with evidence -- the fully-advanced case."""
    _workspace(root)
    document = _readiness_document(
        table,
        current_stage="publish_ready",
        statuses=dict.fromkeys(_STAGES, "pass"),
        evidence={stage: [f"evidence/{stage}.md"] for stage in _STAGES},
    )
    target = root / "mappings" / table / "readiness-status.yaml"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(document, encoding="utf-8")
    return target


def write_blocked_table(root: Path, table: str = "blocked_sales") -> Path:
    """Blocked at mapping, so silver and later stay not_started."""
    _workspace(root)
    document = _readiness_document(
        table,
        current_stage="mapping_ready",
        statuses={"source_ready": "pass", "mapping_ready": "blocked"},
        evidence={"source_ready": ["evidence/source-profile.md"]},
        blockers={
            "mapping_ready": [
                "source-map.yaml is missing a grain declaration",
                "no named-human approval recorded",
            ]
        },
    )
    target = root / "mappings" / table / "readiness-status.yaml"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(document, encoding="utf-8")
    return target


def write_warning_table(root: Path, table: str = "warning_sales") -> Path:
    """A `warning` stage -- advanced-with-a-recorded-issue.

    The status the contract originally had no slot for. Kept as a fixture so the
    projection is proven to carry it verbatim rather than renaming or dropping it.
    """
    _workspace(root)
    document = _readiness_document(
        table,
        current_stage="source_ready",
        statuses={"source_ready": "warning"},
        evidence={"source_ready": ["evidence/source-profile.md"]},
        blockers={},
    )
    target = root / "mappings" / table / "readiness-status.yaml"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(document, encoding="utf-8")
    return target


def write_empty_workspace(root: Path) -> Path:
    """A recognized workspace with no onboarded tables (first-arrival state)."""
    return _workspace(root)


def write_pending_live_table(root: Path, table: str = "pending_live_sales") -> Path:
    """Source stage awaiting a live profile: blocked with a PENDING LIVE reason."""
    _workspace(root)
    document = _readiness_document(
        table,
        current_stage="source_ready",
        statuses={"source_ready": "blocked"},
        blockers={"source_ready": ["[PENDING LIVE PROFILE] no DSN configured"]},
    )
    target = root / "mappings" / table / "readiness-status.yaml"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(document, encoding="utf-8")
    return target


def write_malformed_table(root: Path, table: str = "malformed_sales") -> Path:
    """Unparseable YAML.

    `build_status_projection` SKIPS this silently and documents that as intentional
    ("failing loud is RS1's job"). FR-010 requires Studio to do the opposite and name
    it as an input defect, so this fixture drives a divergence test, not a parity one.
    """
    _workspace(root)
    target = root / "mappings" / table / "readiness-status.yaml"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("table: [unclosed\n  bad: : :\n", encoding="utf-8")
    return target


def write_missing_stage_table(root: Path, table: str = "partial_sales") -> Path:
    """A document whose stage map omits four of the seven blocks.

    `_project_stages` returns only the blocks it could read, so this is the case the
    contract's `minItems: 7` forces Studio to fill rather than pass through short.
    """
    _workspace(root)
    document = (
        f'table: "{table}"\n'
        'current_stage: "source_ready"\n'
        "stages:\n"
        "  source_ready:\n"
        '    status: "pass"\n'
        "    evidence: []\n"
        "    blocking_reasons: []\n"
        "  mapping_ready:\n"
        '    status: "not_started"\n'
        "    evidence: []\n"
        "    blocking_reasons: []\n"
        "  silver_ready:\n"
        '    status: "not_started"\n'
        "    evidence: []\n"
        "    blocking_reasons: []\n"
    )
    target = root / "mappings" / table / "readiness-status.yaml"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(document, encoding="utf-8")
    return target
