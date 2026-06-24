"""Derive `retail validate` check targets from a filled `source-map.yaml`.

This is the per-table sourcing the live-validator slice (feature 004, FR-008)
named-but-deferred: instead of hardcoding the four target dataclasses, read them
from the table's reviewed mapping artifact (`mappings/<table>/source-map.yaml`,
shape == `templates/source-map.yaml`).

SEPARATE MODULE ON PURPOSE: this parses YAML (pyyaml -- a dev/optional dep), so
it must NOT be imported by `retail.validate`'s import path, whose stdlib-only
invariant keeps the static core's `dependencies = []`. The CLI `validate` handler
imports this lazily, the same way it imports psycopg2 lazily.

CONVENTIONS ENCODED HERE (from ADR 0002 RC14 + the medallion playbook):
  * PK / reconciliation silver table = ``silver.<meta.table_id>`` (PK is verified
    on the TRANSFORMED silver output; reconciliation compares silver vs the fact).
  * Each conformed dimension's surrogate key names the fact's FK column too, so the
    orphan join is ``dim.<sk> = fct.<sk>`` (one FK per non-date dimension).
  * The date dimension is checked by ``check_date_coverage`` (calendar spans the
    data), so it is NOT also emitted as an orphan FK -- that would double-cover it.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .validate import (
    DateCoverageTarget,
    OrphanTarget,
    PkTarget,
    ReconcileTarget,
    ValidationTargets,
)

__all__ = ["ValidationTargets", "load_targets"]


def _require(mapping: dict[str, Any], key: str, ctx: str) -> Any:
    if key not in mapping or mapping[key] is None:
        raise ValueError(f"source-map.yaml: missing required '{key}' in {ctx}")
    return mapping[key]


def load_targets(path: Path | str) -> ValidationTargets:
    """Parse a filled source-map.yaml into the four validate targets.

    Raises FileNotFoundError if the file is absent, and ValueError (naming the
    missing field) if the map omits a section the targets need -- never a raw
    KeyError/AttributeError.
    """
    import yaml  # lazy: dev/optional dep, kept out of retail.validate's import path

    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"source-map.yaml not found: {path}")

    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}

    meta = _require(data, "meta", "top level")
    table_id = _require(meta, "table_id", "meta")
    pk_columns = tuple(_require(meta, "primary_key", "meta"))
    silver = f"silver.{table_id}"

    star = _require(data, "gold_star", "top level")
    fact = _require(star, "fact", "gold_star")
    fact_name = _require(fact, "name", "gold_star.fact")
    measures = tuple(_require(fact, "measures", "gold_star.fact"))

    dims = _require(star, "dimensions", "gold_star")
    fks: list[tuple[str, str, str]] = []
    for dim in dims:
        dim_name = _require(dim, "name", "gold_star.dimensions[]")
        sk = _require(dim, "surrogate_key", f"dimension {dim_name}")
        # RC14: fact FK column == dim surrogate key; join dim.<sk> = fct.<sk>.
        fks.append((sk, dim_name, sk))

    date_dim = _require(star, "date_dimension", "gold_star")
    date_dim_name = _require(date_dim, "name", "gold_star.date_dimension")
    date_sk = _require(date_dim, "surrogate_key", "gold_star.date_dimension")

    return ValidationTargets(
        pk=PkTarget(table=silver, pk_columns=pk_columns),
        date_coverage=DateCoverageTarget(
            fact=fact_name,
            fact_date=date_sk,
            date_dim=date_dim_name,
            dim_date=date_sk,
        ),
        orphans=OrphanTarget(fact=fact_name, fks=tuple(fks)),
        reconcile=ReconcileTarget(silver=silver, gold=fact_name, measures=measures),
    )
