"""Shared fixtures for the `seshat next` guidance tests (issues #488 / #489).

`next`'s two informational guidance fields are covered by two focused test
modules -- one per issue -- because they are genuinely separate concerns:

  - ``test_issue_regression_489_adapter_checkpoint.py`` -- the dbt/Dagster
    adapter checkpoint;
  - ``test_issue_regression_488_source_map_shape.py`` -- the canonical
    source-map shape signpost, and the census that rules out a fail-closed
    shape rule.

Both need the same workspace builder, so it lives here rather than being
duplicated or forcing the two concerns back into one low-cohesion module.

Not a conftest: these are explicit imports, so a reader of either test module
can see exactly where the fixture comes from.
"""

from __future__ import annotations

import textwrap
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]

SPINE: tuple[str, ...] = (
    "source_ready",
    "mapping_ready",
    "silver_ready",
    "gold_ready",
    "semantic_model_ready",
    "dashboard_ready",
    "publish_ready",
)

# The two guidance keys under test. Always present in the document (null when they
# do not apply), never gates.
GUIDANCE_KEYS: tuple[str, ...] = (
    "orchestration_checkpoint",
    "source_map_shape_signpost",
)

# `run_next` only advances PAST mapping_ready when a named-human approval is
# recorded for it -- a `pass` status alone leaves the spine at the approval gate.
# Fixtures that need to reach silver/gold must therefore carry this record.
_MAPPING_APPROVAL = (
    '  - {stage: mapping_ready, owner: "Ada Lovelace (analyst)", at: "2026-07-01"}'
)


def write_status(root: Path, table: str, stage: str) -> None:
    """Commit a spine-consistent readiness-status.yaml that RESTS at ``stage``.

    Every earlier stage passes (with evidence, so the projection's
    pass-without-evidence invariant stays clean) and ``stage`` itself is
    ``not_started`` -- the honest shape of "this is the work in front of me".
    """
    index = SPINE.index(stage)
    stages = [
        f'  {name}: {{status: "pass", evidence: ["{name} evidence"]}}'
        for name in SPINE[:index]
    ]
    stages += [f'  {name}: {{status: "not_started"}}' for name in SPINE[index:]]
    approvals = _MAPPING_APPROVAL if index > SPINE.index("mapping_ready") else ""

    directory = root / "mappings" / table
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "readiness-status.yaml").write_text(
        textwrap.dedent(f"""\
            table: "{table}"
            current_stage: "{stage}"
            stages:
            """)
        + "\n".join(stages)
        + f"\napprovals:\n{approvals}\n",
        encoding="utf-8",
    )


def document(root: Path, table: str | None = None) -> dict[str, Any]:
    """The agent-facing next-action document for ``root``."""
    from seshat.agent_next import build_agent_next_document

    return build_agent_next_document(root, table)


def _descend(cursor: Any, part: str) -> Any:
    """One step of a dotted path. ``name[]`` takes the first list element."""
    if part.endswith("[]"):
        value = cursor.get(part[:-2]) if isinstance(cursor, dict) else None
        return value[0] if isinstance(value, list) and value else None
    return cursor.get(part) if isinstance(cursor, dict) else None


def has_dotted_field(document_body: Any, dotted: str) -> bool:
    """True when ``dotted`` (e.g. ``gold_star.dimensions[].name``) resolves.

    Lives here rather than inline in a test so the walk is written once and the
    tests that use it stay flat (CodeScene nesting guard).
    """
    cursor: Any = document_body
    for part in dotted.split("."):
        cursor = _descend(cursor, part)
        if cursor is None:
            return False
    return True
