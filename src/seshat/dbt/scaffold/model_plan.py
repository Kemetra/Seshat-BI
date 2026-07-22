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
from dataclasses import dataclass, field

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
    # The parsed docs/quality/conformed-dimension-map.yaml (or None). Read by the
    # orchestrator, threaded here so this module stays pure: a dimension this table
    # declares CONFORMED but does not OWN is reused (referenced), not re-emitted
    # (#418-P1). None -> no reuse -> byte-identical single-table output.
    conformed_map: dict | None = None


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
    # Bare names of conformed dimensions this table REUSES (owned by another star,
    # so no model/contract/parity is emitted here -- the fact still FK-refs them).
    # Empty for a single-table scaffold or an owner star (#418-P1).
    reused_dimensions: tuple[str, ...] = ()
    # The reused dims' full specs (name + surrogate FK), so the fact skeleton SQL
    # can still emit a ``ref('<owner dim>')`` join hint for a dim it does not
    # materialize. Parallel to ``reused_dimensions`` (#418-P1); never rendered as a
    # model/contract/parity row -- rendering iterates ``dimensions`` for those.
    reused_dimension_specs: tuple[ModelSpec, ...] = ()
    # bare reused-dim name -> its OWNING star, so the operator note can say which
    # star to build first (#418-P1).
    reused_dimension_owners: dict[str, str] = field(default_factory=dict)


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
    # Maps a silver/gold column name to its mapped ``silver_type``, so a
    # source-cited fact column carries the same advisory ``data_type`` the
    # staging model does (#418-P2). Absent for a row with no silver_type.
    silver_type_by_name: dict[str, str]
    # Maps a derived_columns rollup name (RC11) to its filled ``derived_from``
    # source column, so a dimension attribute whose provenance is a derivation
    # cites its real bronze source instead of failing closed (#414). Only filled
    # (non-placeholder) derivations appear.
    derived_source_by_name: dict[str, str]


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


def _real_source_column(value: object) -> str | None:
    """A ``derived_from`` value is a usable source column only if it is a non-empty
    string that is not an unfilled template placeholder (``<...>``).

    Mirrors ``drift_semantics._real_source_column`` -- the single convention for
    "is this derived_from a real column or an unfilled placeholder", so the
    scaffold and the drift watcher agree on what counts as a filled derivation.
    """
    if not isinstance(value, str):
        return None
    return value if value and not value.startswith("<") else None


def _derived_lookup_entry(row: object) -> tuple[str, str] | None:
    """A ``(name, filled derived_from)`` pair for one ``derived_columns`` row, or
    ``None`` if the row is malformed, unnamed, or its ``derived_from`` is unfilled."""
    if not isinstance(row, dict):
        return None
    name = row.get("name")
    if not isinstance(name, str) or not name:
        return None
    source = _real_source_column(row.get("derived_from"))
    return (name, source) if source is not None else None


def _derived_source_by_name(document: dict) -> dict[str, str]:
    """Map each ``derived_columns`` entry's name to its filled ``derived_from``
    source column (RC11 rollups; #414).

    ``derived_from`` names the AUTHORITATIVE column the rollup derives from -- a
    real column that exists (as a bronze ``source_name`` or a kept silver
    ``rename_to``), NEVER the derived name itself (which is absent from bronze).
    Entries whose ``derived_from`` is empty or an unfilled ``<placeholder>`` are
    omitted, so an incomplete rollup still fails closed rather than fabricating a
    citation from the placeholder.
    """
    rows = document.get("derived_columns")
    return dict(
        entry
        for row in (rows if isinstance(rows, list) else [])
        if (entry := _derived_lookup_entry(row)) is not None
    )


def _silver_type_by_name(document: dict) -> dict[str, str]:
    """Map each kept column's silver name to its mapped ``silver_type``.

    The type authority mirroring ``_bronze_by_silver``'s provenance authority:
    both key on the same silver name (``rename_to`` or ``source_name``) off the
    same kept rows, so a source-cited fact column can carry the map's advisory
    ``data_type`` (#418-P2). A row without a non-empty string ``silver_type`` is
    omitted -- the caller then keeps the ``text`` default.
    """
    lookup: dict[str, str] = {}
    for row in _kept_columns(document):
        source = row.get("source_name")
        if not isinstance(source, str) or not source:
            continue
        silver_type = row.get("silver_type")
        if not isinstance(silver_type, str) or not silver_type:
            continue
        rename = row.get("rename_to")
        silver = rename if isinstance(rename, str) and rename else source
        lookup[silver] = silver_type
    return lookup


def _resolve_bronze_source(inputs: _PlanInputs, name: str) -> str | None:
    """Resolve a column name to a REAL bronze ``source_name`` that a kept row
    genuinely provides, or ``None`` -- never a fabricated column.

    Two hops, both grounded in the kept ``columns[]`` rows: the name is either a
    silver name (``rename_to`` / ``source_name`` -> ``bronze_by_silver``), or a raw
    bronze ``source_name`` some kept row already carries. The second hop lets a
    ``derived_from`` that names the bronze column directly (not a silver rename)
    still resolve, while refusing a name no kept row maps to bronze.
    """
    source = inputs.bronze_by_silver.get(name)
    if source is not None:
        return source
    # `name` may itself be a raw bronze source_name (a derived_from pointing at the
    # unrenamed column). Honor it ONLY if a kept row actually provides it.
    if name in inputs.bronze_by_silver.values():
        return name
    return None


def _bronze_citation(inputs: _PlanInputs, silver_name: str, context: str) -> str:
    """The ``bronze.<table>.<source_name>`` citation for a silver column, or fail.

    Resolves the name to its committed bronze ``source_name`` via the kept
    ``columns[]`` rows. Two provenance shapes resolve honestly:

    * a direct 1:1 kept column (``bronze_by_silver``), and
    * a ``derived_columns`` rollup (RC11, #414): a governed derivation whose
      ``derived_from`` names the AUTHORITATIVE bronze source column it computes
      from -- cited to THAT real column, so a rollup-bearing map scaffolds
      end-to-end instead of being hand-completed.

    A name that resolves to no real bronze column is a defect (never a fabricated
    citation): a rollup with an unfilled ``<placeholder>`` derived_from, or an
    attribute that is neither kept nor derived. The message distinguishes the
    kept-column and derived_columns paths and points at the hand-completion path."""
    source = _resolve_bronze_source(inputs, silver_name)
    if source is None:
        derived_from = inputs.derived_source_by_name.get(silver_name)
        if derived_from is not None:
            # It IS a filled rollup, but its derived_from does not resolve to a
            # real bronze column -- refuse rather than fabricate that source.
            resolved = _resolve_bronze_source(inputs, derived_from)
            if resolved is not None:
                return f"bronze.{inputs.source_table}.{resolved}"
        raise ScaffoldError(
            f"{context} references {silver_name!r}, which resolves to no real "
            "bronze source column. If it is a direct source column, keep it in "
            "columns[] (with rename_to) before scaffolding. If it is a "
            "derived_columns rollup (RC11, a derived_from computation), give it a "
            "filled derived_from that names a kept bronze source column -- an "
            "unfilled <placeholder> or a column no kept row provides cannot be "
            "cited (author that model column and its meta.seshat citation by hand)"
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


def _bare_dim_name(name: str) -> str:
    """The bare dimension name the conformed-dimension map keys on: an optional
    ``<schema>.`` prefix stripped, lowercased (mirrors HR1's ``_bare``)."""
    return name.rsplit(".", 1)[-1].strip().lower()


def _reuses_dimension(decl: object, table_id: str) -> bool:
    """True iff ``table_id`` REUSES (does not own) the conformed dim ``decl``
    declares: status ``conformed`` with a ``stars`` list of >=2 entries in which
    ``table_id`` is a member but is NOT the OWNER (the FIRST entry, #418-P1). Any
    other shape -> not reused (the dim is owned and emitted as today).

    Owner is ``stars[0]`` compared directly (NOT "in stars[1:]"): a human may
    accidentally repeat the owner later in the list (``[a, b, a]``) -- ``a`` is
    still the owner and must NOT be told to reuse its own dim (which would leave
    the dim materialized by nobody). ``stars`` is an unvalidated authority field
    (HR1 checks only ``status``), so this must be robust to a duplicate entry."""
    if not isinstance(decl, dict) or decl.get("status") != "conformed":
        return False
    stars = decl.get("stars")
    if not isinstance(stars, list) or len(stars) < 2:
        return False
    return table_id in stars and table_id != stars[0]


def _governed_star_id(document: dict, table_id: str) -> str:
    """The GOVERNED star id the conformed-dimension map keys ``stars`` on.

    Mirrors HR1's ``conformed_dimension._star_id`` EXACTLY -- ``meta.table_id``,
    then top-level ``source_id``, then the directory ``table_id`` fallback -- so
    scaffold resolves reuse against the SAME identifier the authority (and HR1)
    declares. Using the raw CLI/directory ``table_id`` would miss a legitimate
    reuser whose mapping directory differs from its governed star id (#419 review).
    """
    meta = document.get("meta")
    if isinstance(meta, dict) and isinstance(meta.get("table_id"), str):
        return meta["table_id"]
    source_id = document.get("source_id")
    if isinstance(source_id, str):
        return source_id
    return table_id


def _conformed_reuse(conformed_map: dict | None, star_id: str) -> dict[str, str]:
    """Map each bare dim name ``star_id`` REUSES (does not own) to its OWNING star,
    read from the conformed-dimension map (#418-P1).

    ``star_id`` is the GOVERNED star id (:func:`_governed_star_id`), matching what
    the map's ``stars`` entries and HR1 use -- NOT the raw CLI/directory table id.
    The owner is ``stars[0]`` -- carried so the operator note can name which star
    to build first. Fail-SAFE: an absent/malformed map (or any dim not meeting
    :func:`_reuses_dimension`) yields no reuse -> every dim is owned and emitted
    as today.

    NOTE: HR1 validates a conformed dim's ``status`` and its surrogate/attribute
    conformance across DISCOVERED same-named stars, but it does NOT validate the
    ``stars`` LIST contents (that ``stars[0]`` names a real governed star which
    actually declares this dim). A mistyped/absent owner therefore suppresses the
    reuser's model and leaves a dangling ``ref()`` caught at ``dbt parse`` -- not a
    clean scaffold-time refusal. Validating the owner requires the cross-table
    governed-star view tracked as a #418 follow-up.
    """
    dims = conformed_map.get("dimensions") if isinstance(conformed_map, dict) else None
    if not isinstance(dims, dict):
        return {}
    return {
        _bare_dim_name(name): decl["stars"][0]
        for name, decl in dims.items()
        if isinstance(name, str) and _reuses_dimension(decl, star_id)
    }


def _bronze_cited_column(inputs: _PlanInputs, name: str, context: str) -> ColumnSpec:
    """A fact column whose value IS a bronze column (grain key, measure, degenerate
    dim), cited to its real ``source_name`` -- fail closed if the map does not
    stage it (never a fabricated citation).

    Carries the map's ``silver_type`` as the advisory ``data_type`` when the row
    declared one (#418-P2), so the fact contract's type reflects the mapped target
    -- consistent with the staging model. Falls back to the ``text`` default
    otherwise.
    """
    silver_type = inputs.silver_type_by_name.get(name)
    return ColumnSpec(
        name=name,
        source_columns=(_bronze_citation(inputs, name, context),),
        data_type=silver_type if silver_type else "text",
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


def _plan_inputs(source: MapSource, table_id: str, fact: FactBinding) -> _PlanInputs:
    """Resolve the ``gold_star`` section and the provenance/type lookups into the
    one bundle every derivation step reads. Fails closed on a missing gold_star."""
    document = source.document
    gold_star = document.get("gold_star")
    if not isinstance(gold_star, dict):
        raise ScaffoldError("source map has no gold_star section to scaffold")
    meta = document.get("meta")
    grain = meta.get("grain") if isinstance(meta, dict) else None
    return _PlanInputs(
        table_id=table_id,
        source_table=table_id,
        source_map=source.source_map,
        source_map_revision=source.source_map_revision,
        fact=fact,
        fact_grain=grain if isinstance(grain, str) and grain.strip() else "one row",
        gold_star=gold_star,
        bronze_by_silver=_bronze_by_silver(document),
        silver_type_by_name=_silver_type_by_name(document),
        derived_source_by_name=_derived_source_by_name(document),
    )


@dataclass(frozen=True, slots=True)
class _PartitionedDimensions:
    """Declared dims split into what this star OWNS vs REUSES (#418-P1).

    ``declared`` drives the fact's FK-per-dimension list -- a conformed dim the
    fact points at is a real FK even when another star owns its MODEL. ``owned``
    drives models, contracts, and parity; a ``reused`` dim's model lives under its
    owning star and the fact ``ref()``s it there.

    NOTE (#418 follow-up): reuse drops the reuser's WHOLE dim spec, so an attribute
    the reuser declares that the OWNER's dim lacks is not preserved -- HR1 allows
    divergent attribute sets, and reconciling them needs the owner's map (the
    cross-table view scaffold does not load here). Latent until a real conformed
    collision exists; documented in the design spec.
    """

    declared: tuple[ModelSpec, ...]
    owned: tuple[ModelSpec, ...]
    reused: tuple[ModelSpec, ...]
    # bare reused-dim name -> its OWNING star, for the operator note.
    owners: dict[str, str]


def _partition_dimensions(
    inputs: _PlanInputs, conformed_map: dict | None, star_id: str
) -> _PartitionedDimensions:
    declared = _dimensions(inputs)
    reuse = _conformed_reuse(conformed_map, star_id)
    owned = tuple(dim for dim in declared if _bare_dim_name(dim.name) not in reuse)
    reused = tuple(dim for dim in declared if _bare_dim_name(dim.name) in reuse)
    if not owned:
        raise ScaffoldError(
            "every declared dimension is a conformed dimension owned by another "
            "star, so this table would materialize no dimension model of its own; "
            "at least one owned dimension is required to scaffold a star"
        )
    return _PartitionedDimensions(
        declared=declared, owned=owned, reused=reused, owners=reuse
    )


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
    inputs = _plan_inputs(source, table_id, fact)
    star_id = _governed_star_id(source.document, table_id)
    dims = _partition_dimensions(inputs, source.conformed_map, star_id)
    return ScaffoldPlan(
        table_id=table_id,
        source_table=table_id,
        source_map=source.source_map,
        source_map_revision=source.source_map_revision,
        fact=fact,
        staging=_staging_model(inputs, source.document),
        dimensions=dims.owned,
        # The fact FK loop iterates ALL declared dims (owned + reused); models and
        # parity iterate only the owned subset.
        fact_model=_fact_model(inputs, dims.declared),
        audit=_audit_model(table_id),
        parity=_parity_rows(inputs, dims.owned),
        reused_dimensions=tuple(_bare_dim_name(dim.name) for dim in dims.reused),
        reused_dimension_specs=dims.reused,
        reused_dimension_owners=dims.owners,
    )
