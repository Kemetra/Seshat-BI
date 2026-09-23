"""Per-table build-engine resolution for the dagster medallion assets (spec 135).

The `silver_tables` / `gold_tables` assets resolve a build engine per table and
layer from an explicit committed flag. Allowed values: ``migrations`` (the
default) and ``dbt``. The engine is NEVER inferred: an absent file, malformed
YAML, non-mapping document, absent layer key, or any value other than the exact
token ``dbt`` FAILS CLOSED to ``migrations`` (FR-001). Only the literal ``dbt``
engages the dbt engine.

The flag lives inside the table's human-reviewed committed working set at
``mappings/<table>/build-engine.yaml`` (per-layer keys), so flipping an engine
is itself a reviewed, committed, attributable change -- the compensating control
for the unattended self-accepted plan digest (plan-review R1). An environment
variable, CLI flag, or any runtime input MUST NOT select the engine.

This is the ONE tested resolver: the orchestration assets import it through a
thin re-export (``tower_bi_orchestration.engine``) and ``seshat dagster doctor``
imports it directly, so both report the SAME resolved engine (FR-010). The
module is stdlib-only at import time; ``yaml`` is imported lazily inside the
resolver exactly as the gate readers do.
"""

from __future__ import annotations

import re
from pathlib import Path

MIGRATIONS = "migrations"
DBT = "dbt"

# The generic committed flag file (Principle VII: a placeholder-driven name, not
# a table specific one). Per-layer keys allow a mixed configuration (FR-015).
ENGINE_FILE = "build-engine.yaml"

_SAFE_IDENTIFIER = re.compile(r"^[a-z][a-z0-9_]*$")


def _engine_path(root: Path, table: str) -> Path:
    return Path(root) / "mappings" / table / ENGINE_FILE


def engine_flag_uncommitted(root: Path, table: str) -> bool:
    """True when a flag file exists but is untracked or carries local edits.

    Such a flag is IGNORED (the resolver falls back to ``migrations``); the
    doctor reports it so the operator knows why dbt is not engaged."""
    if not _SAFE_IDENTIFIER.fullmatch(table):
        return False
    if not _engine_path(root, table).is_file():
        return False
    from seshat.gitstate import is_tracked_and_clean

    return not is_tracked_and_clean(Path(root), f"mappings/{table}/{ENGINE_FILE}")


def _layer_value(root: Path, table: str, layer: str) -> str | None:
    """Return the raw layer value from the COMMITTED flag file, or None.

    The flag is the compensating control for the self-accepted plan digest, so
    only a committed, clean flag counts: an untracked or locally edited file is
    read as absent, and the parsed text is the HEAD blob, never the worktree.
    Never raises and never surfaces the path: any read/parse problem yields None
    so the caller falls through to the fail-closed ``migrations`` default.
    """
    if not _engine_path(root, table).is_file():
        return None
    from seshat.gitstate import committed_text

    text = committed_text(Path(root), f"mappings/{table}/{ENGINE_FILE}")
    if text is None:
        return None
    import yaml  # lazy: keeps the static core import path stdlib-only

    try:
        document = yaml.safe_load(text)
    except yaml.YAMLError:
        return None
    if not isinstance(document, dict):
        return None
    value = document.get(layer)
    return value if isinstance(value, str) else None


def resolve_build_engine(root: Path, table: str, layer: str) -> str:
    """Resolve the build engine for one table+layer, fail-closed to migrations.

    Returns ``"dbt"`` ONLY when the committed flag names it exactly for this
    layer; every other case (unsafe identifiers, absent/untracked/dirty/
    malformed/non-mapping file, absent key, any non-``dbt`` value) returns
    ``"migrations"``.
    """
    if not _SAFE_IDENTIFIER.fullmatch(table) or not _SAFE_IDENTIFIER.fullmatch(layer):
        return MIGRATIONS
    return DBT if _layer_value(root, table, layer) == DBT else MIGRATIONS
