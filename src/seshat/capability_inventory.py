"""Read-only capability inventory builder (spec 118).

Renders the committed capability manifest (``docs/capabilities/capabilities.yaml``)
into two DETERMINISTIC forms: a grouped human read (default) and a stable JSON
machine form (``--format json``). The manifest is SELF-CONTAINED for display --
each entry carries its own name/summary/axes; the builder does not resolve feeder
facts at render time. The feeders (``capability_feeders.py``) exist for the
INDEPENDENT truthfulness oracle (``tests/unit/test_capability_inventory.py``),
which reconciles the manifest against them via its OWN readers -- that separation
is the anti-circularity guarantee (the builder never learns ground truth from the
same path the oracle checks). This is NOT a ``retail``/``seshat`` CLI verb (the
ratified Option-B decision) -- it is exposed ONLY as a ``python -m`` module
entry point, wrapped by the ``capabilities`` skill.

Hard constraints (grep-verifiable):
  - No file write of any kind (no ``open(..., "w")``, no ``write_text``, no
    ``Path.write*``) anywhere in this module.
  - No DB driver import, no network call, at module scope or anywhere else.
  - No ``readiness-status.yaml`` read (FR-011): this module reads capability
    METADATA only, never per-table run-state.
  - No numeric maturity/confidence/completeness/health value is ever emitted
    (FR-009); grouping is by fixed categorical precedence, never a computed
    ranking.

``__main__`` writes only to stdout via ``print``.
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path

_LIFECYCLE_STATES: frozenset[str] = frozenset({"shipped", "spec-only", "deferred"})
_AUTHORITIES: frozenset[str] = frozenset({"agent-runnable", "advisory", "human-gated"})
_SURFACES: frozenset[str] = frozenset(
    {"cli", "skill", "execution-adapter", "plugin", "docs", "human-artifact"}
)
_REQUIREMENTS: frozenset[str] = frozenset({"database", "optional-dependency"})
_PROVENANCES: frozenset[str] = frozenset(
    {"locally-verified", "publicly-released", "unrecorded"}
)

_GROUP_AVAILABLE_NOW = "available-now"
_GROUP_REQUIRES_DB = "requires-db-or-extra"
_GROUP_COMPANION = "agent-companion"
_GROUP_HUMAN_GATED = "human-gated"
_GROUP_DEFERRED = "deferred"

_GROUP_HEADINGS: dict[str, str] = {
    _GROUP_AVAILABLE_NOW: "Available now",
    _GROUP_REQUIRES_DB: "Requires database or optional dependency",
    _GROUP_COMPANION: "Agent / companion",
    _GROUP_HUMAN_GATED: "Human-gated",
    _GROUP_DEFERRED: "Deferred / not shipped",
}

# Fixed group order (data-model.md): top wins, each capability lands in
# EXACTLY ONE group.
_GROUP_ORDER: tuple[str, ...] = (
    _GROUP_AVAILABLE_NOW,
    _GROUP_REQUIRES_DB,
    _GROUP_COMPANION,
    _GROUP_HUMAN_GATED,
    _GROUP_DEFERRED,
)

_GAP = "[unrecorded]"

# The closed, declared field set of an InventoryRecord (contracts/inventory-output.md
# Form 2). Kept as a tuple (not derived from the dataclass) so the schema is an
# explicit, reviewable contract independent of any future dataclass field reorder.
_RECORD_FIELDS: tuple[str, ...] = (
    "id",
    "name",
    "summary",
    "state",
    "authority",
    "surface",
    "requirements",
    "provenance",
    "readiness_stage",
    "command",
    "documentation",
    "group",
)


@dataclass(frozen=True)
class InventoryRecord:
    """One rendered capability record (data-model.md derived entity)."""

    id: str
    name: str
    summary: str
    state: str
    authority: str
    surface: str
    requirements: tuple[str, ...]
    provenance: str
    readiness_stage: str
    command: str | None
    documentation: str
    group: str

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "summary": self.summary,
            "state": self.state,
            "authority": self.authority,
            "surface": self.surface,
            "requirements": list(self.requirements),
            "provenance": self.provenance,
            "readiness_stage": self.readiness_stage,
            "command": self.command,
            "documentation": self.documentation,
            "group": self.group,
        }


def load_manifest(repo_root: Path) -> list[dict]:
    """Read the raw capability list from ``docs/capabilities/capabilities.yaml``.
    Missing/malformed manifest resolves to an empty list (drop-in edge case)."""
    import yaml  # lazy: keep this module's import path stdlib-light

    path = repo_root / "docs" / "capabilities" / "capabilities.yaml"
    try:
        raw = path.read_text(encoding="utf-8-sig")
        data = yaml.safe_load(raw)
    except (OSError, UnicodeDecodeError, yaml.YAMLError):
        return []
    if not isinstance(data, dict):
        return []
    caps = data.get("capabilities")
    return caps if isinstance(caps, list) else []


def _as_str_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str)]


def _primary_group(entry: dict) -> str:
    """Fixed precedence (data-model.md): Deferred > Human-gated >
    Requires-DB/extra > Agent-companion > Available-now."""
    state = entry.get("state")
    authority = entry.get("authority")
    surface = entry.get("surface")
    requirements = _as_str_list(entry.get("requirements"))

    if state in ("spec-only", "deferred"):
        return _GROUP_DEFERRED
    if authority == "human-gated":
        return _GROUP_HUMAN_GATED
    if requirements:
        return _GROUP_REQUIRES_DB
    if authority == "advisory" or surface == "skill":
        return _GROUP_COMPANION
    return _GROUP_AVAILABLE_NOW


def _project_record(entry: dict) -> InventoryRecord:
    """Project one manifest entry into its InventoryRecord, applying the
    fixed-precedence group assignment. Assumes the entry already carries the
    closed field set (the oracle enforces that against the real manifest;
    the builder itself stays permissive/best-effort like the other read-only
    surfaces so a malformed entry degrades rather than crashes)."""
    requirements = tuple(_as_str_list(entry.get("requirements")))
    return InventoryRecord(
        id=str(entry.get("id", "")),
        name=str(entry.get("name", "")),
        summary=str(entry.get("summary", "")),
        state=str(entry.get("state", "")),
        authority=str(entry.get("authority", "")),
        surface=str(entry.get("surface", "")),
        requirements=requirements,
        provenance=str(entry.get("provenance", "unrecorded")),
        readiness_stage=str(entry.get("readiness_stage", "not-stage-scoped")),
        command=entry.get("command") if isinstance(entry.get("command"), str) else None,
        documentation=str(entry.get("documentation", "")),
        group=_primary_group(entry),
    )


def build_inventory(repo_root: Path | str = ".") -> list[dict]:
    """Build the sorted, deterministic list of capability records.

    Reads the committed manifest + feeders under ``repo_root``; resolves each
    record carries the manifest's own categorical fields plus the derived
    ``group``. The manifest is self-contained for display; feeder facts are not
    resolved here -- the truthfulness oracle reconciles the manifest against the
    feeders independently (``capability_feeders.py``). Sorted by ``id`` for
    determinism (FR-007).
    """
    root = Path(repo_root)
    manifest = load_manifest(root)
    records = [_project_record(entry).to_dict() for entry in manifest]
    records.sort(key=lambda r: r["id"])
    return records


def _format_axes(record: dict) -> str:
    parts = [f"surface: {record['surface']}", f"authority: {record['authority']}"]
    requirements = record["requirements"]
    parts.append(f"requires: {', '.join(requirements) if requirements else 'none'}")
    provenance = record["provenance"]
    provenance_text = _GAP if provenance == "unrecorded" else provenance
    parts.append(f"provenance: {provenance_text}")
    return " | ".join(parts)


def _format_entry_point(record: dict) -> str:
    if record["authority"] == "human-gated":
        return "(human action)"
    if record["command"]:
        return record["command"]
    return "(none)"


def _render_group_body(records: list[dict]) -> list[str]:
    if not records:
        return ["  (none)"]
    lines: list[str] = []
    for record in records:
        state_suffix = f" [{record['state']}]" if record["state"] != "shipped" else ""
        lines.append(f"  {record['name']} -- {record['summary']}{state_suffix}")
        lines.append(f"    {_format_axes(record)}")
        entry = _format_entry_point(record)
        doc = record["documentation"] or _GAP
        lines.append(f"    entry: {entry} | doc: {doc}")
    return lines


def render_human(records: list[dict]) -> str:
    """Render Form 1 (contracts/inventory-output.md): fixed group order,
    items sorted by id, GAP marker for unset fields, ASCII-only, no score."""
    lines = [
        "Seshat BI -- capability inventory "
        "(read-only; grants nothing, computes no readiness)",
        "",
    ]
    grouped: dict[str, list[dict]] = {key: [] for key in _GROUP_ORDER}
    for record in records:
        grouped[record["group"]].append(record)

    for index, group_key in enumerate(_GROUP_ORDER):
        if index > 0:
            lines.append("")
        lines.append(_GROUP_HEADINGS[group_key])
        lines.extend(_render_group_body(grouped[group_key]))

    return "\n".join(lines) + "\n"


def render_json(records: list[dict]) -> str:
    """Render Form 2 (contracts/inventory-output.md): stdlib json, sorted
    keys, indent=2, records already sorted by id, trailing newline."""
    ordered = [{field: record[field] for field in _RECORD_FIELDS} for record in records]
    return json.dumps(ordered, indent=2, sort_keys=True) + "\n"


def _parse_args(argv: list[str]) -> str:
    """Thin arg parse for the ``--format`` flag only. Not an argparse
    subcommand/``_DISPATCH`` entry -- this is a bare module ``__main__``."""
    output_format = "text"
    if "--format" in argv:
        idx = argv.index("--format")
        if idx + 1 < len(argv):
            output_format = argv[idx + 1]
    return output_format


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    output_format = _parse_args(args)
    records = build_inventory(".")
    if output_format == "json":
        print(render_json(records), end="")
    else:
        print(render_human(records), end="")
    return 0


if __name__ == "__main__":
    sys.exit(main())
