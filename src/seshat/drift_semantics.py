"""Extract the returns/PII semantic rulings from a source-map.yaml into a
seshat.drift.DriftSemantics, so retail drift's live leg can fire the
returns_rule_drift / pii_surface_drift classes.

SEPARATE MODULE ON PURPOSE (mirrors validate_targets.py): this parses YAML
(pyyaml, an optional/dev dep), so it must NOT be on seshat.drift's import path,
whose stdlib-only invariant keeps the static core dependency-free. The CLI
imports this lazily. This module depends on seshat.drift (for DriftSemantics),
never the reverse -- the pure core gains no new dependency.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .drift import DriftSemantics


def _dropped_pii(columns: list[dict[str, Any]]) -> frozenset[str]:
    """Columns flagged PII AND dropped -- the only ones that can 'reappear'. A
    pii:true + decision:keep column never left the mapped output, so it is not a
    reappearance candidate. Missing pii -> false; missing decision -> not drop."""
    return frozenset(
        c["source_name"]
        for c in columns
        if c.get("pii") is True and c.get("decision") == "drop" and c.get("source_name")
    )


def _real_source_column(value: object) -> str | None:
    """A `derived_from` value is a usable source column only if it is a non-empty
    string that is not an unfilled template placeholder (`<...>`)."""
    if not isinstance(value, str):
        return None
    if not value or value.startswith("<"):  # empty or a <placeholder>
        return None
    return value


def _returns_column(doc: dict[str, Any]) -> str | None:
    """The AUTHORITATIVE SOURCE column the returns rule keys on: the is_return
    derived column's `derived_from`. classify_drift watches the profiled BRONZE
    source columns, so the derived name (is_return, absent from bronze) would
    never fire -- derived_from names the real source column. None when
    derived_columns is empty/absent, no is_return entry exists, or derived_from
    is an unfilled placeholder (<...>)."""
    for d in doc.get("derived_columns") or []:
        if d.get("name") == "is_return":
            return _real_source_column(d.get("derived_from"))
    return None


def load_drift_semantics(source_map_path: str | Path) -> DriftSemantics:
    """Parse source-map.yaml into a DriftSemantics. Raises ValueError on
    malformed yaml or a missing top-level `columns` key."""
    import yaml  # lazy: optional dep, never on the static-core import path

    text = Path(source_map_path).read_text(encoding="utf-8")
    doc = yaml.safe_load(text)
    if not isinstance(doc, dict) or "columns" not in doc:
        raise ValueError(
            f"source-map.yaml: missing required top-level 'columns' ({source_map_path})"
        )
    columns = doc.get("columns") or []
    return DriftSemantics(
        returns_column=_returns_column(doc),
        dropped_pii_columns=_dropped_pii(columns),
    )
