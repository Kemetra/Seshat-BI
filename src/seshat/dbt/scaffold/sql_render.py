"""Render skeleton transformation SQL and the concrete parity-audit SQL.

The staging / dimension / fact bodies are SKELETONS: they select the exact
governed output columns (so a completed ``contract.enforced: true`` build sees
the declared shape) but leave the joins, casts, and surrogate-key logic as an
explicit ``TODO`` for the human to complete against the live database -- the
scaffold targets the static gate, not a runnable build (see the package
docstring). The parity-audit SQL, by contrast, is COMPLETE and gate-shaped: it
emits exactly the assertion rows ``dbt show --select audit_<t>_parity`` consumes.
"""

from __future__ import annotations

from .model_plan import ModelSpec, ParityRow, ScaffoldPlan

_TODO = (
    "-- TODO(seshat dbt scaffold): complete the transformation logic below.\n"
    "-- The SELECT list is the governed output contract (do not change the column\n"
    "-- names or count); fill in the joins, casts, and key derivation, then run\n"
    "-- `seshat dbt validate` / `plan` / `build`.\n"
)


def _select_list(model: ModelSpec) -> str:
    return ",\n".join(f"    null as {column.name}" for column in model.columns)


def render_staging_sql(plan: ScaffoldPlan) -> str:
    columns = _select_list(plan.staging)
    return (
        f"{_TODO}"
        "with source_rows as (\n"
        f"    select * from {{{{ source('bronze', '{plan.source_table}') }}}}\n"
        ")\n\n"
        "select\n"
        f"{columns}\n"
        "from source_rows\n"
    )


def render_dimension_sql(model: ModelSpec, plan: ScaffoldPlan) -> str:
    columns = _select_list(model)
    return (
        f"{_TODO}"
        "-- Add the governed unknown member (surrogate key -1) with `union all`\n"
        "-- unless this dimension declares has_unknown_member: false.\n"
        "select\n"
        f"{columns}\n"
        f"from {{{{ ref('stg_{plan.table_id}') }}}}\n"
    )


def render_date_dimension_sql(model: ModelSpec) -> str:
    columns = _select_list(model)
    return (
        f"{_TODO}"
        "-- Build a CONTIGUOUS calendar with generate_series over the approved\n"
        "-- span (RC15); never SELECT DISTINCT a date column.\n"
        "select\n"
        f"{columns}\n"
        "from (select 1) as date_spine_placeholder\n"
    )


def render_fact_sql(plan: ScaffoldPlan) -> str:
    columns = _select_list(plan.fact_model)
    # The fact FKs point at BOTH the dims this star owns AND any conformed dim it
    # reuses from another star (#418-P1) -- a reused dim is materialized under its
    # owner but the fact still ref()s it, so its join hint must appear here too.
    refs = "\n".join(
        f"-- join {{{{ ref('{dim.name}') }}}} to resolve {dim.columns[0].name}"
        for dim in (*plan.dimensions, *plan.reused_dimension_specs)
    )
    return (
        f"{_TODO}"
        f"{refs}\n"
        "select\n"
        f"{columns}\n"
        f"from {{{{ ref('stg_{plan.table_id}') }}}} as s\n"
    )


def _parity_value(row: ParityRow, plan: ScaffoldPlan, which: str) -> str:
    """The migration-oracle (source) or shadow (ref) SQL expression for a row."""
    if row.assertion_class == "business_key_count":
        return _count_distinct(plan.fact.name, plan.fact.business_key, which)
    if row.assertion_class == "additive_money_total":
        measure = row.subject.split(".", 1)[1]
        return _sum_measure(plan.fact.name, measure, which)
    return _count_star(row.subject, which)  # fact_row_count + dimension_member_count


def _relation(subject: str, which: str) -> str:
    model = subject.split(".", 1)[0]
    if which == "expected":
        return f"{{{{ source('migration_gold', '{model}') }}}}"
    return f"{{{{ ref('{model}') }}}}"


def _count_star(subject: str, which: str) -> str:
    return f"(select count(*)::numeric from {_relation(subject, which)})"


def _count_distinct(model: str, keys: tuple[str, ...], which: str) -> str:
    """Distinct-count the grain key. A COMPOSITE key is wrapped as a parenthesized
    ROW expression -- ``count(distinct (a, b))`` -- because Postgres ``count``
    takes exactly ONE distinct expression (``count(distinct a, b)`` is a syntax
    error). A single-column key stays the plain ``count(distinct col)`` it was."""
    expression = keys[0] if len(keys) == 1 else f"({', '.join(keys)})"
    return (
        f"(select count(distinct {expression})::numeric from {_relation(model, which)})"
    )


def _sum_measure(model: str, measure: str, which: str) -> str:
    return (
        f"(select coalesce(sum({measure}), 0)::numeric from {_relation(model, which)})"
    )


def _parity_branch(row: ParityRow, plan: ScaffoldPlan) -> str:
    expected = _parity_value(row, plan, "expected")
    actual = _parity_value(row, plan, "actual")
    return (
        "    select\n"
        f"        '{row.assertion_id}'::text as assertion_id,\n"
        f"        '{row.assertion_class}'::text as assertion_class,\n"
        f"        '{row.subject}'::text as subject,\n"
        f"        {expected} as expected_value,\n"
        f"        {actual} as actual_value,\n"
        f"        {row.tolerance}::numeric as tolerance_value"
    )


def render_audit_sql(plan: ScaffoldPlan) -> str:
    branches = "\n\n    union all\n\n".join(
        _parity_branch(row, plan) for row in plan.parity
    )
    return (
        "with parity_values as (\n"
        f"{branches}\n"
        ")\n\n"
        "select\n"
        "    assertion_id,\n"
        "    assertion_class,\n"
        "    subject,\n"
        "    expected_value::text as expected,\n"
        "    actual_value::text as actual,\n"
        "    abs(expected_value - actual_value)::text as delta,\n"
        "    tolerance_value::text as tolerance,\n"
        "    abs(expected_value - actual_value) <= tolerance_value as passed\n"
        "from parity_values\n"
        "order by assertion_id\n"
    )
