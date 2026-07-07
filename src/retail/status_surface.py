"""Agent-control status surface (spec 109, roadmap M4, under ratified Option B).

Under Option B this is the ONE sanctioned CLI addition -- a THIN, READ-ONLY JSON
projection of already-committed readiness state. It is NOT a broad verb surface
and it introduces NO new readiness *logic*: every field here already exists in a
committed ``mappings/<table>/readiness-status.yaml`` (see
``templates/readiness-status.yaml``, ``docs/readiness/readiness-model.md``).

Contract:
  - Read-only: globs and reads committed YAML files; writes nothing, opens no DB
    connection, makes no network call (B1/B3, FR-004).
  - No new computation: ``current_stage`` / ``stages[*].status`` / ``evidence[]`` /
    ``blocking_reasons[]`` / ``next_action`` are projected verbatim from the
    source file -- this module never derives, grants, or upgrades a stage.
  - Never a numeric score: only the four categorical statuses
    (``not_started``/``blocked``/``warning``/``pass``) plus named evidence/blocker
    strings are emitted (hard rule #9, Principle V).
  - Deterministic: table entries are sorted by their source path so two runs over
    the same committed state produce byte-identical output.
  - Graceful on an empty repo: no committed ``mappings/*/readiness-status.yaml``
    projects as ``{"tables": []}``, never an error.
  - Best-effort on a malformed source file: a file that fails to parse as a YAML
    mapping is SKIPPED, not fatal. Failing loud on malformed readiness-status.yaml
    is RS1's job (the static gate); this projection's job is to report what it CAN
    read without crashing a downstream host that polls it.
  - Module scope stays stdlib-only (B1/B3): ``yaml`` is imported lazily, inside the
    function, mirroring every other lazy-YAML rule/handler in this repo (e.g.
    ``rules/readiness_status.py``).
"""

from __future__ import annotations

from pathlib import Path

_STAGE_ORDER: tuple[str, ...] = (
    "source_ready",
    "mapping_ready",
    "silver_ready",
    "gold_ready",
    "semantic_model_ready",
    "dashboard_ready",
    "publish_ready",
)


def _as_str_list(value: object) -> list[str]:
    """Coerce a committed list field to ``list[str]``, dropping non-string
    entries rather than raising -- a projection stays best-effort on an
    imperfectly-typed source file."""
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str)]


def _project_stage(block: object) -> dict | None:
    """Project one stage block verbatim. Returns ``None`` for a missing or
    malformed block (skipped, not fabricated)."""
    if not isinstance(block, dict):
        return None
    status = block.get("status")
    if not isinstance(status, str):
        return None
    return {
        "status": status,
        "evidence": _as_str_list(block.get("evidence")),
        "blocking_reasons": _as_str_list(block.get("blocking_reasons")),
    }


def _project_stages(stages: object) -> dict:
    if not isinstance(stages, dict):
        return {}
    projected: dict[str, dict] = {}
    for name in _STAGE_ORDER:
        stage = _project_stage(stages.get(name))
        if stage is not None:
            projected[name] = stage
    return projected


def _project_table(data: dict, source_path: str) -> dict:
    """Project one parsed readiness-status.yaml document into its stable
    JSON-schema shape (``$defs/tableStatus`` in ``schemas/agent-status.schema.json``).
    ``current_stage`` / ``next_action`` project as ``null`` when the source file
    omits them -- never fabricated."""
    table = data.get("table")
    current_stage = data.get("current_stage")
    next_action = data.get("next_action")
    return {
        "table": table if isinstance(table, str) else source_path,
        "source_path": source_path,
        "current_stage": current_stage if isinstance(current_stage, str) else None,
        "stages": _project_stages(data.get("stages")),
        "blocking_reasons": _as_str_list(data.get("blocking_reasons")),
        "next_action": next_action if isinstance(next_action, str) else None,
    }


def _load_yaml_mapping(path: Path) -> dict | None:
    """Read + parse one readiness-status.yaml. Returns ``None`` (skip, not fatal)
    on any read/parse/shape failure -- RS1 is the fail-loud gate for a malformed
    committed file; this projection stays best-effort for a live/polling host."""
    import yaml  # lazy: keep this module's import path stdlib-light (B1/B3)

    try:
        raw = path.read_text(encoding="utf-8-sig")
    except (OSError, UnicodeDecodeError):
        return None
    try:
        data = yaml.safe_load(raw)
    except yaml.YAMLError:
        return None
    if not isinstance(data, dict):
        return None
    return data


def build_status_projection(repo_root: Path | str = ".") -> dict:
    """Build the agent-control status projection for ``repo_root``.

    Globs ``mappings/*/readiness-status.yaml`` under ``repo_root``, projects each
    into the stable shape validated by ``schemas/agent-status.schema.json``, and
    returns ``{"tables": [...]}`` sorted by source path. Read-only: no writes, no
    DB, no network. An empty/absent ``mappings/`` projects as ``{"tables": []}``,
    not an error.
    """
    root = Path(repo_root)
    mappings_dir = root / "mappings"
    tables: list[dict] = []
    if mappings_dir.is_dir():
        for status_path in sorted(mappings_dir.glob("*/readiness-status.yaml")):
            data = _load_yaml_mapping(status_path)
            if data is None:
                continue
            source_path = status_path.relative_to(root).as_posix()
            tables.append(_project_table(data, source_path))
    tables.sort(key=lambda t: t["source_path"])
    return {"tables": tables}
