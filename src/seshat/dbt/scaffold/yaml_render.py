"""Render gate-valid ``_models.yml`` contract rows from a scaffold plan.

The row shape is the one ``project._model_contract`` reads: a top-level
``meta.seshat`` (NOT under ``config`` -- nesting it there silently orphans the
model), the ``seshat_table_<id>`` selector tag under ``config.tags``, and one
``meta.seshat`` citation per output column.

Each column carries an ADVISORY ``data_type`` (issue #406 item 3) surfacing the
intended Postgres type without ``config.contract.enforced``. That is deliberate:
the parity-proven worked example (``dbt/models/**/retail_store_sales``) ships
NO enforced contract, and an enforced contract with a scaffold-guessed type would
REJECT the human's correctly-typed completed SQL (e.g. an integer surrogate key
against a ``text`` guess) at build -- recreating the very "can't get there" wall
this issue removes. ``data_type`` documents the intent; the human owns the cast.
"""

from __future__ import annotations

from .model_plan import ColumnSpec, ModelSpec, ScaffoldPlan


def _column_meta(column: ColumnSpec) -> dict:
    if column.source_columns:
        return {"source_columns": list(column.source_columns)}
    return {"derivation": column.derivation}


def _column_row(column: ColumnSpec, selector: str, tests: tuple[dict, ...]) -> dict:
    row: dict = {"name": column.name}
    # data_type is ADVISORY and only meaningful for a source-cited column, where
    # the map's silver_type is authoritative; a derived column's type is the
    # human's call (do not guess it), so it is omitted there.
    if column.source_columns:
        row["data_type"] = column.data_type
    row["meta"] = {"seshat": _column_meta(column)}
    if tests:
        row["data_tests"] = [_tagged_test(test, selector) for test in tests]
    return row


def _tagged_test(test: dict, selector: str) -> dict:
    name = test["name"]
    body: dict = {"config": {"tags": [selector]}}
    if "arguments" in test:
        body = {"arguments": dict(test["arguments"]), "config": {"tags": [selector]}}
    return {name: body}


def _column_tests(
    name: str, unique_col: str, not_null_cols: frozenset[str]
) -> tuple[dict, ...]:
    tests: list[dict] = []
    if name == unique_col:
        tests.append({"name": "unique"})
    if name in not_null_cols:
        tests.append({"name": "not_null"})
    return tuple(tests)


def _synthetic_key_column(model: ModelSpec) -> str | None:
    """The surrogate/PK column when the model has one (dims, the fact, the audit).

    Preferred over the natural business key: a dimension's ``-1`` unknown-member
    row NULLs the natural key, which would fail ``not_null`` on correct data. A
    staging model has no such column."""
    for column in model.columns:
        if column.derivation in {"surrogate_key", "date_spine", "parity_measure"}:
            return column.name
    return None


def _key_test_targets(model: ModelSpec) -> tuple[str, frozenset[str]]:
    """(column that carries ``unique``, columns that carry ``not_null``).

    A single synthetic PK is both unique and not_null. Absent one (staging), the
    grain business key is tested: EACH component gets ``not_null``, but ``unique``
    is emitted ONLY for a single-column key -- a composite grain's uniqueness is a
    multi-column property that dbt's column-level ``unique`` cannot express, so a
    single-column ``unique`` on one component would fail on correct data (a
    composite uniqueness test would be a model-level
    ``dbt_utils.unique_combination_of_columns``, out of scope for the scaffold)."""
    synthetic = _synthetic_key_column(model)
    if synthetic is not None:
        return synthetic, frozenset({synthetic})
    key = model.business_key
    unique_col = key[0] if len(key) == 1 else ""
    return unique_col, frozenset(key)


def _model_columns(model: ModelSpec, selector: str) -> list[dict]:
    unique_col, not_null_cols = _key_test_targets(model)
    return [
        _column_row(
            column, selector, _column_tests(column.name, unique_col, not_null_cols)
        )
        for column in model.columns
    ]


def _model_row(model: ModelSpec, plan: ScaffoldPlan, selector: str) -> dict:
    return {
        "name": model.name,
        "config": {"tags": [selector]},
        "meta": {
            "seshat": {
                "table_id": plan.table_id,
                "source_map": plan.source_map,
                "source_map_revision": plan.source_map_revision,
                "grain": model.grain,
                "business_key": list(model.business_key),
                "authority": "derived",
            }
        },
        "columns": _model_columns(model, selector),
    }


def render_models_document(
    models: tuple[ModelSpec, ...], plan: ScaffoldPlan, selector: str
) -> dict:
    """A dbt ``_models.yml`` document for one layer of the scaffold plan."""
    return {
        "version": 2,
        "models": [_model_row(model, plan, selector) for model in models],
    }
