"""Derive the governed dbt star from an approved source map (pure, no I/O).

Everything here is derivable from the committed ``source-map.yaml`` alone:
the fact + dimensions from ``gold_star`` (issue #331 tags supply the fact's
grain key and money measures the built graph cannot enumerate), the staging
columns from the kept ``columns[]`` rows, and the exact parity-assertion set
``evidence._validate_parity_set`` requires. Names are normalized the same way
``fact_semantics._fact_name`` does -- a ``gold.``-qualified map name maps to the
bare dbt MODEL name -- so the generated models match what the manifest knows.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from seshat.dbt.contracts import FactBinding, GovernanceError

_IDENTIFIER = re.compile(r"^[a-z][a-z0-9_]*$")


@dataclass(frozen=True, slots=True)
class ColumnSpec:
    """One model output column: either cited to source columns or derived."""

    name: str
    source_columns: tuple[str, ...] = ()
    derivation: str | None = None
    data_type: str = "text"


@dataclass(frozen=True, slots=True)
class ModelSpec:
    """One governed dbt model (staging, dimension, fact, or the parity audit)."""

    name: str
    layer: str
    grain: str
    business_key: tuple[str, ...]
    columns: tuple[ColumnSpec, ...]


@dataclass(frozen=True, slots=True)
class ParityRow:
    """One governed parity assertion the audit model emits."""

    assertion_id: str
    assertion_class: str
    subject: str
    tolerance: str


@dataclass(frozen=True, slots=True)
class MapSource:
    """The committed source map an approved scaffold is derived from.

    Bundles the parsed ``document`` with its repo-relative path and committed git
    blob revision so the derivation takes one cohesive input, not three loose
    positional arguments.
    """

    document: dict
    source_map: str
    source_map_revision: str


@dataclass(frozen=True, slots=True)
class ScaffoldPlan:
    """The complete derived model set for one governed table."""

    table_id: str
    source_table: str
    source_map: str
    source_map_revision: str
    fact: FactBinding
    staging: ModelSpec
    dimensions: tuple[ModelSpec, ...]
    fact_model: ModelSpec
    audit: ModelSpec
    parity: tuple[ParityRow, ...]


class ScaffoldError(GovernanceError):
    """A committed source map cannot be turned into a governed model set."""

    def __init__(self, message: str) -> None:
        super().__init__("DBT_SCAFFOLD_INVALID", message)


def _normalized_name(value: object, label: str) -> str:
    """The bare dbt MODEL name for a (possibly schema-qualified) map relation."""
    normalized = value.rsplit(".", 1)[-1] if isinstance(value, str) else None
    if not isinstance(normalized, str) or not _IDENTIFIER.fullmatch(normalized):
        raise ScaffoldError(f"{label} is not a lowercase relation identifier")
    return normalized


def _require_identifier(value: object, label: str) -> str:
    if not isinstance(value, str) or not _IDENTIFIER.fullmatch(value):
        raise ScaffoldError(f"{label} is not a lowercase identifier")
    return value


# evidence._selected_fact_model / _selected_dimension_subjects classify built
# models by prefix: a dimension MUST be dim_*, and the single fact must be the
# one model that is NOT dim_/stg_/audit_. A dimension without the dim_ prefix, or
# a fact that collides with a reserved prefix, would scaffold + pass static
# validate yet never pass the run-evidence gate -- so fail closed at scaffold.
_RESERVED_PREFIXES = ("dim_", "stg_", "audit_")


def _require_dimension_prefix(name: str) -> None:
    if not name.startswith("dim_"):
        raise ScaffoldError(
            f"dimension model {name!r} must be named dim_* (the run-evidence gate "
            "identifies dimensions by that prefix); rename it in gold_star"
        )


def _require_fact_prefix(name: str) -> None:
    if name.startswith(_RESERVED_PREFIXES):
        raise ScaffoldError(
            f"fact model {name!r} must NOT start with dim_/stg_/audit_ (the "
            "run-evidence gate identifies the fact by excluding those prefixes)"
        )


def _string_list(value: object) -> tuple[str, ...]:
    if isinstance(value, str):
        return (value,)
    if isinstance(value, list):
        return tuple(item for item in value if isinstance(item, str))
    return ()


@dataclass(frozen=True, slots=True)
class _PlanInputs:
    """Resolved identity + the raw ``gold_star`` section for one table."""

    table_id: str
    source_table: str
    source_map: str
    source_map_revision: str
    fact: FactBinding
    fact_grain: str
    gold_star: dict
    # Maps a silver/gold column name back to its REAL bronze source_name, so a
    # gold-star citation resolves to the column that actually exists in bronze
    # (never the renamed silver name -- that would be fabricated provenance).
    bronze_by_silver: dict[str, str]


def _kept_columns(document: dict) -> tuple[dict, ...]:
    """The ``keep``/``derive`` column rows a staging model must reproduce."""
    rows = document.get("columns")
    if not isinstance(rows, list):
        return ()
    return tuple(
        row
        for row in rows
        if isinstance(row, dict) and row.get("decision") in {"keep", "derive"}
    )


def _bronze_by_silver(document: dict) -> dict[str, str]:
    """Map each kept column's silver name (``rename_to`` or, absent that, its
    ``source_name``) to its real bronze ``source_name``.

    This is the single provenance authority: any gold-star reference to a silver
    name resolves through it to a column that genuinely exists in bronze. A
    reference with no matching row is a defect (fail closed), never fabricated.
    """
    lookup: dict[str, str] = {}
    for row in _kept_columns(document):
        source = row.get("source_name")
        if not isinstance(source, str) or not source:
            continue
        rename = row.get("rename_to")
        silver = rename if isinstance(rename, str) and rename else source
        lookup[silver] = source
    return lookup


def _bronze_citation(inputs: _PlanInputs, silver_name: str, context: str) -> str:
    """The ``bronze.<table>.<source_name>`` citation for a silver column, or fail.

    Resolves the silver name to its committed bronze ``source_name`` via the
    kept ``columns[]`` rows. A name that maps to no kept source column is a defect
    (never a fabricated citation) -- but it also legitimately covers a
    ``derived_columns`` rollup (RC11, e.g. a business segment with a
    ``derived_from`` source rather than a direct 1:1 rename), which the scaffold
    does not yet wire, so the message distinguishes the two and points at the
    hand-completion path."""
    source = inputs.bronze_by_silver.get(silver_name)
    if source is None:
        raise ScaffoldError(
            f"{context} references {silver_name!r}, which no kept source column "
            "in columns[] maps to. If it is a direct source column, keep it in "
            "columns[] (with rename_to) before scaffolding. If it is a "
            "derived_columns rollup (RC11, a derived_from computation, not a 1:1 "
            "rename), scaffold does not yet generate its provenance -- author that "
            "model column and its meta.seshat citation by hand (tracked follow-up)"
        )
    return f"bronze.{inputs.source_table}.{source}"


def _staging_column(row: dict, source_table: str) -> ColumnSpec | None:
    """A staging column ALWAYS cites its bronze source; a row without a usable
    ``source_name``/``rename_to`` is skipped (it cannot be a valid citation)."""
    source = row.get("source_name")
    if not isinstance(source, str) or not source:
        return None
    rename = row.get("rename_to")
    name = rename if isinstance(rename, str) and rename else source
    if not _IDENTIFIER.fullmatch(name):
        return None
    silver_type = row.get("silver_type")
    return ColumnSpec(
        name=name,
        source_columns=(f"bronze.{source_table}.{source}",),
        derivation=None,
        data_type=silver_type
        if isinstance(silver_type, str) and silver_type
        else "text",
    )


def _staging_model(inputs: _PlanInputs, document: dict) -> ModelSpec:
    columns = tuple(
        spec
        for row in _kept_columns(document)
        if (spec := _staging_column(row, inputs.source_table)) is not None
    )
    if not columns:
        raise ScaffoldError("no kept source columns to stage; the map keeps nothing")
    return ModelSpec(
        name=f"stg_{inputs.table_id}",
        layer="staging",
        grain=inputs.fact_grain,
        business_key=inputs.fact.business_key,
        columns=columns,
    )


def _dimension_model(raw: dict, inputs: _PlanInputs) -> ModelSpec:
    name = _normalized_name(raw.get("name"), "gold_star.dimensions[].name")
    _require_dimension_prefix(name)
    surrogate = _require_identifier(raw.get("surrogate_key"), f"{name} surrogate_key")
    attributes = _string_list(raw.get("attributes"))
    for attr in attributes:
        _require_identifier(attr, f"{name} attribute")
    natural_key = attributes[0] if attributes else surrogate
    columns = [ColumnSpec(name=surrogate, derivation="surrogate_key")]
    columns.extend(
        ColumnSpec(
            name=attr,
            source_columns=(_bronze_citation(inputs, attr, f"{name}.{attr}"),),
        )
        for attr in attributes
    )
    return ModelSpec(
        name=name,
        layer="marts",
        grain=f"one row per governed {natural_key} member",
        business_key=(attributes[0],) if attributes else (surrogate,),
        columns=tuple(columns),
    )


_DATE_COLUMNS = ("full_date", "year", "quarter", "month", "day", "iso_week")


def _date_dimension(inputs: _PlanInputs) -> ModelSpec | None:
    raw = inputs.gold_star.get("date_dimension")
    if not isinstance(raw, dict):
        return None
    name = _normalized_name(raw.get("name"), "gold_star.date_dimension.name")
    _require_dimension_prefix(name)
    surrogate = _require_identifier(raw.get("surrogate_key"), f"{name} surrogate_key")
    columns = tuple(
        ColumnSpec(name=column, derivation="date_spine")
        for column in (surrogate, *_DATE_COLUMNS)
    )
    return ModelSpec(
        name=name,
        layer="marts",
        grain="one row per calendar date in the approved span",
        business_key=(_DATE_COLUMNS[0],),
        columns=columns,
    )


def _dimensions(inputs: _PlanInputs) -> tuple[ModelSpec, ...]:
    raw = inputs.gold_star.get("dimensions")
    entities = [
        _dimension_model(row, inputs)
        for row in (raw if isinstance(raw, list) else [])
        if isinstance(row, dict)
    ]
    date_dim = _date_dimension(inputs)
    if date_dim is not None:
        entities.append(date_dim)
    if not entities:
        raise ScaffoldError("gold_star declares no dimensions to build")
    return tuple(entities)


def _bronze_cited_column(inputs: _PlanInputs, name: str, context: str) -> ColumnSpec:
    """A fact column whose value IS a bronze column (grain key, measure, degenerate
    dim), cited to its real ``source_name`` -- fail closed if the map does not
    stage it (never a fabricated citation)."""
    return ColumnSpec(
        name=name,
        source_columns=(_bronze_citation(inputs, name, context),),
    )


def _string_field(container: dict, key: str) -> tuple[str, ...]:
    return _string_list(container.get(key))


def _governed_measures(inputs: _PlanInputs) -> tuple[str, ...]:
    """Every fact measure the owner declared -- money AND non-money (e.g. an
    additive ``quantity``). The ``gold_star.fact.measures`` list is authoritative:
    the additive_money_measures subset parity reconciles by sum, but ALL declared
    measures are real fact columns the human wants materialized."""
    fact_section = inputs.gold_star.get("fact")
    declared = (
        _string_field(fact_section, "measures")
        if isinstance(fact_section, dict)
        else ()
    )
    # measures[] is the superset; union in additive_money_measures so a map that
    # tags money without re-listing it under measures still gets those columns.
    ordered: list[str] = [*declared]
    ordered.extend(m for m in inputs.fact.additive_money_measures if m not in ordered)
    return tuple(ordered)


def _degenerate_dimensions(inputs: _PlanInputs) -> tuple[str, ...]:
    """The top-level ``gold_star.degenerate_dimensions`` -- attribute-free columns
    that live ON the fact (e.g. ``transaction_id``, ``discount_applied``)."""
    return _string_field(inputs.gold_star, "degenerate_dimensions")


def _fact_columns(
    inputs: _PlanInputs, dimensions: tuple[ModelSpec, ...]
) -> tuple[ColumnSpec, ...]:
    """EVERY governed fact column: the synthetic PK, the grain/business key, one
    FK per dimension, every declared measure (money AND non-money), and every
    degenerate dimension.

    Provenance is honest, never fabricated: the fact's own surrogate PK and every
    dimension FK (``*_sk``) are computed by join, so they carry a governed
    ``surrogate_key`` derivation -- NOT a bronze citation to the renamed silver
    name (which no bronze column has). The grain key, measures, and degenerate
    dimensions ARE columns that exist in bronze, so they resolve to their real
    ``source_name`` through the provenance lookup (fail closed if the map does not
    stage them). ``_dedupe_columns`` collapses a name that is both the business key
    and a degenerate dim (e.g. ``transaction_id``) to one column.
    """
    fact_sk = f"{inputs.fact.name}_sk"
    columns = [ColumnSpec(name=fact_sk, derivation="surrogate_key")]
    columns.extend(
        _bronze_cited_column(inputs, key, "fact business_key")
        for key in inputs.fact.business_key
    )
    columns.extend(
        ColumnSpec(name=dim.columns[0].name, derivation="surrogate_key")
        for dim in dimensions
    )
    columns.extend(
        _bronze_cited_column(inputs, measure, "fact measure")
        for measure in _governed_measures(inputs)
    )
    columns.extend(
        _bronze_cited_column(inputs, degenerate, "fact degenerate_dimension")
        for degenerate in _degenerate_dimensions(inputs)
    )
    return tuple(_dedupe_columns(columns))


def _dedupe_columns(columns: list[ColumnSpec]) -> list[ColumnSpec]:
    seen: set[str] = set()
    unique: list[ColumnSpec] = []
    for column in columns:
        if column.name in seen:
            continue
        seen.add(column.name)
        unique.append(column)
    return unique


def _fact_model(inputs: _PlanInputs, dimensions: tuple[ModelSpec, ...]) -> ModelSpec:
    _require_fact_prefix(inputs.fact.name)
    return ModelSpec(
        name=inputs.fact.name,
        layer="marts",
        grain=inputs.fact_grain,
        business_key=inputs.fact.business_key,
        columns=_fact_columns(inputs, dimensions),
    )


_AUDIT_COLUMNS = (
    "assertion_id",
    "assertion_class",
    "subject",
    "expected",
    "actual",
    "delta",
    "tolerance",
    "passed",
)


def _audit_model(table_id: str) -> ModelSpec:
    return ModelSpec(
        name=f"audit_{table_id}_parity",
        layer="audit",
        grain="one row per required migration-versus-shadow parity assertion",
        business_key=("assertion_id",),
        columns=tuple(
            ColumnSpec(name=name, derivation="parity_measure")
            for name in _AUDIT_COLUMNS
        ),
    )


def _parity_rows(
    inputs: _PlanInputs, dimensions: tuple[ModelSpec, ...]
) -> tuple[ParityRow, ...]:
    """The exact assertion set ``evidence._validate_parity_set`` requires."""
    fact = inputs.fact.name
    rows = [
        ParityRow("fact_row_count", "fact_row_count", fact, "0"),
        ParityRow(
            f"fact_distinct_{'_'.join(inputs.fact.business_key)}",
            "business_key_count",
            f"{fact}.{'.'.join(inputs.fact.business_key)}",
            "0",
        ),
    ]
    rows.extend(
        ParityRow(
            f"fact_{measure}_sum",
            "additive_money_total",
            f"{fact}.{measure}",
            "0.01",
        )
        for measure in inputs.fact.additive_money_measures
    )
    rows.extend(
        ParityRow(
            f"{dim.name}_member_count",
            "dimension_member_count",
            dim.name,
            "0",
        )
        for dim in dimensions
    )
    return tuple(rows)


def build_scaffold_plan(
    source: MapSource,
    table_id: str,
    fact: FactBinding,
) -> ScaffoldPlan:
    """Derive the complete governed model set from an approved source map.

    ``fact`` is the already-validated :class:`FactBinding`
    (``fact_semantics.load_fact_semantics``); this never re-parses the fact
    section, only the star's dimensions and the staging columns.
    """
    document = source.document
    gold_star = document.get("gold_star")
    if not isinstance(gold_star, dict):
        raise ScaffoldError("source map has no gold_star section to scaffold")
    meta = document.get("meta")
    grain = meta.get("grain") if isinstance(meta, dict) else None
    inputs = _PlanInputs(
        table_id=table_id,
        source_table=table_id,
        source_map=source.source_map,
        source_map_revision=source.source_map_revision,
        fact=fact,
        fact_grain=grain if isinstance(grain, str) and grain.strip() else "one row",
        gold_star=gold_star,
        bronze_by_silver=_bronze_by_silver(document),
    )
    dimensions = _dimensions(inputs)
    return ScaffoldPlan(
        table_id=table_id,
        source_table=table_id,
        source_map=source.source_map,
        source_map_revision=source.source_map_revision,
        fact=fact,
        staging=_staging_model(inputs, document),
        dimensions=dimensions,
        fact_model=_fact_model(inputs, dimensions),
        audit=_audit_model(table_id),
        parity=_parity_rows(inputs, dimensions),
    )
