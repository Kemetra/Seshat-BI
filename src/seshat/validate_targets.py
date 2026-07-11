"""Derive `retail validate` check targets from a filled `source-map.yaml`.

This is the per-table sourcing the live-validator slice (feature 004, FR-008)
named-but-deferred: instead of hardcoding the four target dataclasses, read them
from the table's reviewed mapping artifact (`mappings/<table>/source-map.yaml`,
shape == `templates/source-map.yaml`).

SEPARATE MODULE ON PURPOSE: this parses YAML (pyyaml -- a dev/optional dep), so
it must NOT be imported by `seshat.validate`'s import path, whose stdlib-only
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

from .identifiers import validate_identifier, validate_qualified_identifier
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


def _require_identifier(mapping: dict[str, Any], key: str, ctx: str) -> str:
    return validate_identifier(_require(mapping, key, ctx), context=f"{ctx}.{key}")


def _require_identifier_tuple(
    mapping: dict[str, Any], key: str, ctx: str
) -> tuple[str, ...]:
    value = _require(mapping, key, ctx)
    if isinstance(value, str) or not isinstance(value, list | tuple):
        raise ValueError(f"source-map.yaml: '{key}' in {ctx} must be a list")
    return tuple(validate_identifier(item, context=f"{ctx}.{key}") for item in value)


def _gold_qualify(name: str) -> str:
    """Qualify a gold_star object name to the `gold` schema if it has no schema.

    The live-check SQL uses these names VERBATIM (`FROM {fact}`), never prepending a
    schema -- so a bare `fct_sales` would query the search_path and fail
    (UndefinedTable). A gold_star object IS, by definition (Principle III / RC14), in
    the `gold` schema, so a bare name is qualified to `gold.<name>`. An already-
    qualified name (any `schema.object`, e.g. `gold.fct_sales_rss`) is left untouched,
    so a star sharing the `gold` schema can disambiguate with a suffixed, qualified
    name. Both the bare convention (c086) and the qualified convention work.
    """
    name = validate_qualified_identifier(
        name,
        context="gold_star object name",
        min_parts=1,
        max_parts=2,
    )
    if "." not in name:
        return f"gold.{name}"
    return validate_qualified_identifier(
        name,
        context="gold_star object name",
        min_parts=2,
        max_parts=2,
        allowed_schemas={"gold"},
    )


def load_targets(path: Path | str) -> ValidationTargets:
    """Parse a filled source-map.yaml into the four validate targets.

    Raises FileNotFoundError if the file is absent, and ValueError (naming the
    missing field) if the map omits a section the targets need -- never a raw
    KeyError/AttributeError.
    """
    import yaml  # lazy: dev/optional dep, kept out of seshat.validate's import path

    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"source-map.yaml not found: {path}")

    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except OSError as exc:
        raise ValueError(f"source-map.yaml: could not read {path}: {exc}") from exc
    except yaml.YAMLError as exc:
        raise ValueError(f"source-map.yaml: invalid YAML in {path}: {exc}") from exc

    meta = _require(data, "meta", "top level")
    table_id = _require_identifier(meta, "table_id", "meta")
    pk_columns = _require_identifier_tuple(meta, "primary_key", "meta")
    silver = f"silver.{table_id}"

    star = _require(data, "gold_star", "top level")
    fact = _require(star, "fact", "gold_star")
    # gold_star objects live in the `gold` schema; qualify a bare name so the live
    # check SQL (which uses the name verbatim) resolves. Already-qualified names pass
    # through unchanged. See _gold_qualify.
    fact_name = _gold_qualify(_require(fact, "name", "gold_star.fact"))
    measures = _require_identifier_tuple(fact, "measures", "gold_star.fact")

    dims = _require(star, "dimensions", "gold_star")
    fks: list[tuple[str, str, str]] = []
    for dim in dims:
        dim_name = _gold_qualify(_require(dim, "name", "gold_star.dimensions[]"))
        sk = _require_identifier(dim, "surrogate_key", f"dimension {dim_name}")
        # RC14: fact FK column == dim surrogate key; join dim.<sk> = fct.<sk>.
        fks.append((sk, dim_name, sk))

    date_dim = _require(star, "date_dimension", "gold_star")
    date_dim_name = _gold_qualify(
        _require(date_dim, "name", "gold_star.date_dimension")
    )
    date_sk = _require_identifier(date_dim, "surrogate_key", "gold_star.date_dimension")

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
