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


def _layer_value(root: Path, table: str, layer: str) -> str | None:
    """Return the raw layer value from the committed flag file, or None.

    Never raises and never surfaces the path: any read/parse problem yields None
    so the caller falls through to the fail-closed ``migrations`` default.
    """
    path = _engine_path(root, table)
    if not path.is_file():
        return None
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
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
    layer; every other case (unsafe identifiers, absent/malformed/non-mapping
    file, absent key, any non-``dbt`` value) returns ``"migrations"``.
    """
    if not _SAFE_IDENTIFIER.fullmatch(table) or not _SAFE_IDENTIFIER.fullmatch(layer):
        return MIGRATIONS
    return DBT if _layer_value(root, table, layer) == DBT else MIGRATIONS
