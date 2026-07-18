"""Guarantee the mapping stage's unresolved-questions mirror exists (#326).

``mappings/<table>/unresolved-questions.md`` is the Principle-V human-decision
ledger. The dbt gate hard-requires it (``DBT_MAPPING_MIRROR_MISSING``) and the
dagster gate reads its ``Gate status`` -- yet the mapping stage is agent-driven
prose, so a table could clear the whole readiness spine without the file and
only fail much later. This emitter closes that gap deterministically:

- It NEVER overwrites an existing ledger (the humans' audit trail wins).
- The stub's status is DERIVED from the committed ``readiness-status.yaml``,
  never invented (never_self_grant_approval): a CLEARED stub is written only
  when a ``mapping_ready: pass`` with a named-human approval is already
  recorded; anything less yields an OPEN stub that keeps every gate blocked.
- The stub carries exactly one ``Gate status:`` line and no question-table
  rows, the one shape every downstream parser (dbt gate, dagster gate,
  approver-view, gap-detector) reads identically.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

import yaml

_TABLE_ID = re.compile(r"^[a-z][a-z0-9_]*$")

_CLEARED_STUB = """\
# Unresolved questions -- `{table_id}`

> Generated mirror (`seshat mapping-mirror`). The mapping stage recorded no
> open blocking questions for this table; this file is the committed
> Principle-V decision ledger the downstream dbt and Dagster gates require.
> Its status is DERIVED from `readiness-status.yaml` (mapping_ready: pass with
> a named-human approval already recorded) -- this file grants nothing itself.

- **Table id:** `{table_id}`
- **Date raised:** {today}
- **Raised by:** `seshat mapping-mirror` (generated stub)
- **Gate status:** CLEARED

## Questions

No open blocking questions were raised during mapping. The decisions and their
named-human approvals are recorded in `readiness-status.yaml` `approvals[]`
and `source-map.yaml`. If a new blocking question surfaces, add it here as a
template-shaped row and flip the gate status back to OPEN.
"""

_OPEN_STUB = """\
# Unresolved questions -- `{table_id}`

> Generated stub (`seshat mapping-mirror`). The committed readiness status does
> not (yet) record a named-human `mapping_ready` pass for this table, so the
> gate starts OPEN and every downstream build stays blocked. Raise each
> build-blocking question as a row (see `templates/unresolved-questions.md`
> for the full authoring guidance), record resolutions, and only a named human
> flips the status to CLEARED.

- **Table id:** `{table_id}`
- **Date raised:** {today}
- **Raised by:** `seshat mapping-mirror` (generated stub)
- **Gate status:** OPEN

## Open questions (the build is blocked until these are `answered`)

| ID | Question | Why it blocks | Who must answer | Proposed default (if unanswered) | Status | Resolution |
|----|----------|---------------|-----------------|----------------------------------|--------|------------|
"""


@dataclass(frozen=True)
class MirrorResult:
    """What the emitter did for one table's unresolved-questions mirror."""

    path: Path
    created: bool
    status: str  # "already-present" | "cleared-stub" | "open-stub"


def _require_mapping_dir(repo_root: Path, table_id: str) -> Path:
    if not _TABLE_ID.fullmatch(table_id):
        raise ValueError("table id must match ^[a-z][a-z0-9_]*$")
    mapping_dir = Path(repo_root) / "mappings" / table_id
    if not mapping_dir.is_dir():
        raise ValueError(
            f"no mapping working set exists at mappings/{table_id}/; "
            "run the mapping stage first"
        )
    return mapping_dir


def _read_readiness(mapping_dir: Path) -> dict[str, Any]:
    try:
        document = yaml.safe_load(
            (mapping_dir / "readiness-status.yaml").read_text(encoding="utf-8")
        )
    except (OSError, UnicodeError, yaml.YAMLError):
        return {}
    return document if isinstance(document, dict) else {}


def _mapping_ready_passed(document: dict[str, Any]) -> bool:
    stages = document.get("stages")
    mapping = stages.get("mapping_ready") if isinstance(stages, dict) else None
    status = mapping.get("status") if isinstance(mapping, dict) else None
    return status == "pass"


def _named_owner(row: Any) -> bool:
    owner = row.get("owner") if isinstance(row, dict) else None
    return isinstance(owner, str) and bool(owner.strip())


def _valid_date(row: Any) -> bool:
    value = row.get("at") if isinstance(row, dict) else None
    if not isinstance(value, str):
        return False
    try:
        date.fromisoformat(value)
    except ValueError:
        return False
    return True


def _has_named_mapping_approval(document: dict[str, Any]) -> bool:
    approvals = document.get("approvals")
    if not isinstance(approvals, list):
        return False
    return any(
        isinstance(row, dict)
        and row.get("stage") == "mapping_ready"
        and _named_owner(row)
        and _valid_date(row)
        for row in approvals
    )


def _stub_for(mapping_dir: Path, table_id: str) -> tuple[str, str]:
    document = _read_readiness(mapping_dir)
    cleared = _mapping_ready_passed(document) and _has_named_mapping_approval(document)
    template = _CLEARED_STUB if cleared else _OPEN_STUB
    status = "cleared-stub" if cleared else "open-stub"
    return template.format(table_id=table_id, today=date.today().isoformat()), status


def ensure_unresolved_questions(repo_root: Path, table_id: str) -> MirrorResult:
    """Materialize the mirror if absent; never touch an existing ledger."""

    mapping_dir = _require_mapping_dir(repo_root, table_id)
    path = mapping_dir / "unresolved-questions.md"
    if path.is_file():
        return MirrorResult(path=path, created=False, status="already-present")
    text, status = _stub_for(mapping_dir, table_id)
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(text)
    return MirrorResult(path=path, created=True, status=status)
