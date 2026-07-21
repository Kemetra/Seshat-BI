"""Materialize a scaffold plan to disk: per-file models + idempotent merges.

Per-table model files (``<layer>/<table>/*.sql`` + ``_models.yml``) are written
with the shared hardened non-destructive writer (``safe_write.write_if_absent``):
an existing file is always kept. ``selectors.yml`` and the shared
``models/sources/_sources.yml`` are instead MERGED idempotently -- ``dbt init``
already created ``selectors.yml`` with a bootstrap row, and ``_sources.yml`` is
shared across tables, so a blind write-if-absent would either skip the new table
or clobber another's rows. Both merges add only what is missing.
"""

from __future__ import annotations

from pathlib import Path

import yaml

from seshat.safe_write import (
    SafeWriteError,
    _refuse_symlinked_components,
    write_if_absent,
)

from .model_plan import ModelSpec, ScaffoldError, ScaffoldPlan

_SELECTORS = "dbt/selectors.yml"
_SOURCES = "dbt/models/sources/_sources.yml"


def _yaml_bytes(document: dict) -> bytes:
    text = yaml.safe_dump(document, sort_keys=False, default_flow_style=False)
    return text.encode("utf-8")


def _refuse_symlinked_target(path: Path) -> None:
    """Refuse a symlink AT the output path (even DANGLING, which ``is_file`` misses).

    ``write_text`` on a symlinked path follows the link and rewrites its TARGET --
    possibly outside the repo. Refused with the repo's dedicated ``SafeWriteError``,
    the same posture ``safe_write`` enforces and which the dbt CLI already routes to
    a clean exit 3.
    """
    if path.is_symlink():
        raise SafeWriteError(
            f"refusing to rewrite a symlinked merge target: {path} "
            "(a symlink here could write outside the workspace); remove it and retry"
        )


def _write_merge_target(root: Path, path: Path, document: dict) -> None:
    """Rewrite a MERGE target (selectors.yml / _sources.yml) in place, refusing any
    symlink on the path first.

    Unlike the per-model files (write-if-absent), these shared files must be
    read-then-rewritten to union in the new table, so ``write_if_absent`` cannot
    guard them. This mirrors its containment posture instead: refuse a symlinked
    PARENT component (a symlinked ``dbt/`` would redirect the write even when the
    final file is not itself a link -- ``mkdir(exist_ok=True)`` happily traverses
    it) AND a symlink at the output path. Closes the whole #351/#352 class, not
    just the final component.
    """
    _refuse_symlinked_components(root, path)
    _refuse_symlinked_target(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        _yaml_bytes(document).decode("utf-8"), encoding="utf-8", newline="\n"
    )


def _load_document(path: Path) -> dict:
    """Load an existing merge target, or ``{}`` when it does not exist yet.

    Fails CLOSED on a present-but-malformed document (mirrors every sibling
    writer in this codebase): returning ``{}`` would let the caller rewrite the
    file with ONLY the new rows, silently destroying OTHER tables' selectors or
    sources. An absent file is the only valid empty case.
    """
    if not path.is_file():
        return {}
    try:
        document = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, yaml.YAMLError) as exc:
        raise ScaffoldError(
            f"{path.name} is present but not valid YAML ({exc.__class__.__name__}); "
            "fix or remove it before scaffolding (refusing to overwrite it and lose "
            "other tables' entries)"
        ) from exc
    if not isinstance(document, dict):
        raise ScaffoldError(
            f"{path.name} is present but is not a YAML mapping; fix or remove it "
            "before scaffolding (refusing to overwrite it)"
        )
    return document


def _selector_row(selector: str) -> dict:
    return {
        "name": selector,
        "description": f"Governed shadow graph for the {selector} approved map.",
        "definition": {"method": "tag", "value": selector},
    }


def _existing_list(document: dict, key: str, path: Path) -> list:
    """The value at ``key`` as a list, or ``[]`` when the key is ABSENT.

    Fails CLOSED when the key is PRESENT but not a list (a mapping/scalar/null):
    silently coercing to ``[]`` would rewrite the file dropping that existing
    content -- the same destroy-other-tables' -entries hazard ``_load_document``
    guards. An absent key is the only valid empty case.
    """
    if key not in document:
        return []
    value = document[key]
    if value is None:
        # An explicit `selectors:` / `sources:` with no value is a malformed
        # collection, not an empty one -- refuse rather than silently replace it.
        raise ScaffoldError(
            f"{path.name} has a '{key}:' key with no list value; fix or remove it "
            "before scaffolding (refusing to overwrite it and lose its entries)"
        )
    if not isinstance(value, list):
        raise ScaffoldError(
            f"{path.name} '{key}:' is a {type(value).__name__}, not a list; fix or "
            "remove it before scaffolding (refusing to overwrite it)"
        )
    return value


def merge_selector(root: Path, selector: str) -> bool:
    """Add the ``seshat_table_<id>`` tag selector if absent; True when changed."""
    path = root / _SELECTORS
    document = _load_document(path)
    rows = _existing_list(document, "selectors", path)
    if any(isinstance(row, dict) and row.get("name") == selector for row in rows):
        return False
    document["selectors"] = [*rows, _selector_row(selector)]
    _write_merge_target(root, path, document)
    return True


def _source_entry(name: str, schema: str, tables: list[str]) -> dict:
    return {"name": name, "schema": schema, "tables": [{"name": t} for t in tables]}


def _gold_tables(plan: ScaffoldPlan) -> list[str]:
    dims = [dim.name for dim in plan.dimensions]
    return [plan.fact.name, *dims]


def _existing_table_names(group: dict) -> set[str]:
    tables = group.get("tables")
    return {
        t["name"]
        for t in (tables if isinstance(tables, list) else [])
        if isinstance(t, dict) and isinstance(t.get("name"), str)
    }


def _merge_source_group(group: dict, schema: str, tables: list[str]) -> bool:
    """Union missing table entries INTO an existing group; True when changed.

    A shared ``_sources.yml`` already carries the ``bronze`` / ``migration_gold``
    groups once the first table is scaffolded; a second table must add its NEW
    tables into those same groups (not skip them because the group name exists,
    which would leave the second table's staging/audit SQL referencing undeclared
    sources and break ``dbt parse`` for the whole project).
    """
    group.setdefault("schema", schema)
    existing = _existing_table_names(group)
    missing = [name for name in tables if name not in existing]
    if not missing:
        return False
    current = group.get("tables")
    group["tables"] = [
        *(current if isinstance(current, list) else []),
        *({"name": name} for name in missing),
    ]
    return True


def merge_sources(root: Path, plan: ScaffoldPlan) -> bool:
    """Add/extend the bronze landing source and the migration_gold oracle.

    Adds a missing group whole, OR unions this table's missing tables into an
    already-present group. Idempotent: a re-scaffold of the same table changes
    nothing.
    """
    path = root / _SOURCES
    document = _load_document(path)
    rows = _existing_list(document, "sources", path)
    by_name = {
        row.get("name"): row
        for row in rows
        if isinstance(row, dict) and isinstance(row.get("name"), str)
    }
    desired = {
        "bronze": ("bronze", [plan.source_table]),
        "migration_gold": ("gold", _gold_tables(plan)),
    }
    changed = False
    for name, (schema, tables) in desired.items():
        group = by_name.get(name)
        if group is None:
            rows = [*rows, _source_entry(name, schema, tables)]
            changed = True
        elif _merge_source_group(group, schema, tables):
            changed = True
    if not changed:
        return False
    document.setdefault("version", 2)
    document["sources"] = rows
    _write_merge_target(root, path, document)
    return True


def _model_dir(plan: ScaffoldPlan, model: ModelSpec) -> str:
    return f"dbt/models/{model.layer}/{plan.table_id}"


def write_model_file(root: Path, relative: str, text: str) -> bool:
    """Write one model artifact non-destructively; True when written."""
    return write_if_absent(root, relative, text.encode("utf-8"))
