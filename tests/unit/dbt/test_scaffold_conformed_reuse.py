"""#418-P1 -- conformed-dimension reuse across stars (model-plan derivation).

Two stars share the conformed dim ``dim_customer_rss``. The conformed-dimension
map (docs/quality/conformed-dimension-map.yaml) is the authority: ``stars[0]``
OWNS (materializes) the dim; every later star REUSES it (no dim model, the fact
FK ``ref()``s the owner). Bare dim name in the map, matching HR1. Driver-free:
no live DB, no dbt -- the generated reuser plan is fed through the gate's own
validators.
"""

from __future__ import annotations

import pytest

from seshat.dbt.contracts import FactBinding
from seshat.dbt.scaffold import model_plan, sql_render, yaml_render

pytestmark = pytest.mark.unit

TABLE_ID = "retail_store_sales"
REVISION = "d" * 40
SOURCE_MAP = f"mappings/{TABLE_ID}/source-map.yaml"
_OWNER_TABLE = "retail_store_sales"
_REUSER_TABLE = "returns_line"

# The same committed-map shape test_dbt_scaffold uses: a customer dim + a date
# dim + one money measure.
_MAP = {
    "meta": {"table_id": TABLE_ID, "grain": "one row = one retail transaction"},
    "columns": [
        {
            "source_name": "transaction_id",
            "decision": "keep",
            "rename_to": "transaction_id",
        },
        {"source_name": "customer_id", "decision": "keep", "rename_to": "customer_id"},
        {
            "source_name": "total_spent",
            "decision": "keep",
            "rename_to": "total_spent",
            "silver_type": "numeric(12,2)",
        },
    ],
    "gold_star": {
        "fact": {
            "name": "gold.fct_sales_rss",
            "grain": "one row = one retail transaction",
            "business_key": "transaction_id",
            "measures": ["total_spent"],
            "additive_money_measures": ["total_spent"],
        },
        "dimensions": [
            {
                "name": "gold.dim_customer_rss",
                "surrogate_key": "customer_sk",
                "has_unknown_member": True,
                "attributes": ["customer_id"],
            },
        ],
        "date_dimension": {
            "name": "gold.dim_date_rss",
            "surrogate_key": "date_sk",
            "method": "generate_series",
        },
    },
}

_FACT = FactBinding(
    name="fct_sales_rss",
    business_key=("transaction_id",),
    additive_money_measures=("total_spent",),
)


def _conformed_map() -> dict:
    return {
        "dimensions": {
            "dim_customer_rss": {
                "status": "conformed",
                "stars": [_OWNER_TABLE, _REUSER_TABLE],
            }
        }
    }


def _doc_for(star_id: str) -> dict:
    """``_MAP`` with its governed star id (``meta.table_id``) set to ``star_id`` --
    reuse keys on the governed star id (like HR1), so a test scaffolding a given
    star must give the document that star's identity."""
    return {**_MAP, "meta": {**_MAP["meta"], "table_id": star_id}}


def _source_with_map(
    document: dict, conformed_map: dict | None
) -> model_plan.MapSource:
    return model_plan.MapSource(
        document=document,
        source_map=SOURCE_MAP,
        source_map_revision=REVISION,
        conformed_map=conformed_map,
    )


def _all_models(plan: model_plan.ScaffoldPlan):
    return (plan.staging, *plan.dimensions, plan.fact_model, plan.audit)


def _member_count_subjects(plan: model_plan.ScaffoldPlan) -> set[str]:
    return {
        r.subject for r in plan.parity if r.assertion_class == "dimension_member_count"
    }


def test_owner_star_still_materializes_the_conformed_dim() -> None:
    """The FIRST star in the map's stars[] list OWNS the dim -- its model, contract
    and parity are emitted exactly as today (#418-P1)."""
    plan = model_plan.build_scaffold_plan(
        _source_with_map(_MAP, _conformed_map()), _OWNER_TABLE, _FACT
    )
    assert "dim_customer_rss" in {d.name for d in plan.dimensions}
    assert plan.reused_dimensions == ()  # the owner reuses nothing
    assert "dim_customer_rss" in _member_count_subjects(plan)


def test_reuser_star_omits_the_conformed_dim_model_but_keeps_the_fact_fk() -> None:
    """A non-owner star REUSES the dim: NO dim_customer_rss model (avoids the
    duplicate-model-name dbt-parse failure) and NO member-count parity row for it,
    but the fact STILL carries its customer_sk FK (surrogate_key derivation), and
    the fact SQL ref()s the owner's dim (#418-P1)."""
    plan = model_plan.build_scaffold_plan(
        _source_with_map(_doc_for(_REUSER_TABLE), _conformed_map()),
        _REUSER_TABLE,
        _FACT,
    )
    dim_names = {d.name for d in plan.dimensions}
    assert "dim_customer_rss" not in dim_names  # NOT materialized by the reuser
    assert "dim_date_rss" in dim_names  # the date dim (not conformed) still is
    assert "dim_customer_rss" in plan.reused_dimensions
    # the fact keeps the FK as a surrogate_key derivation (never fabricated)
    fk = next(c for c in plan.fact_model.columns if c.name == "customer_sk")
    assert fk.derivation == "surrogate_key"
    assert fk.source_columns == ()
    # no member-count parity assertion for the reused dim (owner asserts it)
    subjects = _member_count_subjects(plan)
    assert "dim_customer_rss" not in subjects
    assert "dim_date_rss" in subjects
    # the fact skeleton SQL still names the owner's dim via ref()
    assert "ref('dim_customer_rss')" in sql_render.render_fact_sql(plan)


def test_reuser_plan_passes_the_gate_and_parity_validators() -> None:
    """The end-to-end proof: a reuser star's generated contracts pass the real
    gate's _model_contract with zero blockers and its parity set validates exactly
    (#418-P1) -- so a multi-star conformed map scaffolds end-to-end."""
    from seshat.dbt.contracts import ParityAssertion
    from seshat.dbt.evidence import _validate_parity_set
    from seshat.dbt.project import _ContractContext, _model_contract

    plan = model_plan.build_scaffold_plan(
        _source_with_map(_doc_for(_REUSER_TABLE), _conformed_map()),
        _REUSER_TABLE,
        _FACT,
    )
    selector = f"seshat_table_{_REUSER_TABLE}"
    ctx = _ContractContext(
        selector_name=selector,
        table_id=_REUSER_TABLE,
        source_map=SOURCE_MAP,
        source_map_revision=REVISION,
    )
    for model in _all_models(plan):
        document = yaml_render.render_models_document((model,), plan, selector)
        blockers: list = []
        contract = _model_contract(ctx, document["models"][0], blockers)
        assert blockers == [], (model.name, [b.code for b in blockers])
        assert contract is not None
    assertions = tuple(
        ParityAssertion(
            assertion_id=r.assertion_id,
            assertion_class=r.assertion_class,
            subject=r.subject,
            expected="1",
            actual="1",
            delta="0",
            tolerance=r.tolerance,
            passed=True,
        )
        for r in plan.parity
    )
    unique_ids = tuple(sorted(f"model.seshat_bi.{m.name}" for m in _all_models(plan)))
    _validate_parity_set(assertions, unique_ids, plan.fact)  # must not raise


def test_no_conformed_map_means_every_dim_is_owned() -> None:
    """No conformed map (the current committed state) -> reuse set is empty ->
    output byte-identical to today; the reuser table owns every dim (#418-P1)."""
    plan = model_plan.build_scaffold_plan(
        _source_with_map(_doc_for(_REUSER_TABLE), None), _REUSER_TABLE, _FACT
    )
    assert plan.reused_dimensions == ()
    assert "dim_customer_rss" in {d.name for d in plan.dimensions}


def test_distinct_status_is_never_reused() -> None:
    """A dim declared `distinct` (deliberately separate) is never reused, even by a
    non-first star (#418-P1)."""
    distinct_map = {
        "dimensions": {
            "dim_customer_rss": {
                "status": "distinct",
                "stars": [_OWNER_TABLE, _REUSER_TABLE],
            }
        }
    }
    plan = model_plan.build_scaffold_plan(
        _source_with_map(_doc_for(_REUSER_TABLE), distinct_map), _REUSER_TABLE, _FACT
    )
    assert plan.reused_dimensions == ()
    assert "dim_customer_rss" in {d.name for d in plan.dimensions}


def test_malformed_conformed_map_is_ignored_no_reuse() -> None:
    """A malformed conformed map (not the expected shape) is treated as no map ->
    no reuse, no crash (#418-P1 fail-safe)."""
    for bad in ({"dimensions": "not-a-mapping"}, {"unexpected": True}, {}):
        plan = model_plan.build_scaffold_plan(
            _source_with_map(_doc_for(_REUSER_TABLE), bad), _REUSER_TABLE, _FACT
        )
        assert plan.reused_dimensions == ()
        assert "dim_customer_rss" in {d.name for d in plan.dimensions}


def test_owner_rule_is_deterministic_from_the_same_map() -> None:
    """Reversing which table is scaffolded flips owner/reuser deterministically
    from the SAME map -- ownership is map-order-derived, not run-order (#418-P1)."""
    cmap = _conformed_map()
    owner_plan = model_plan.build_scaffold_plan(
        _source_with_map(_MAP, cmap), _OWNER_TABLE, _FACT
    )
    reuser_plan = model_plan.build_scaffold_plan(
        _source_with_map(_doc_for(_REUSER_TABLE), cmap), _REUSER_TABLE, _FACT
    )
    assert "dim_customer_rss" in {d.name for d in owner_plan.dimensions}
    assert "dim_customer_rss" not in {d.name for d in reuser_plan.dimensions}


def test_reuse_resolves_the_governed_star_id_not_the_directory_id() -> None:
    """#419 review: the conformed map's ``stars`` use the GOVERNED star id
    (meta.table_id / source_id), like HR1. A reuser whose mapping DIRECTORY id
    differs from its governed star id must still be recognized -- reuse is keyed on
    the governed id resolved from the document, not the CLI/directory table_id."""
    # the map declares the governed id `returns_governed`, NOT the directory id
    cmap = {
        "dimensions": {
            "dim_customer_rss": {
                "status": "conformed",
                "stars": [_OWNER_TABLE, "returns_governed"],
            }
        }
    }
    # document carries meta.table_id = the GOVERNED id; the CLI passes the DIRECTORY
    # id (which differs) as table_id.
    doc = {**_MAP, "meta": {**_MAP["meta"], "table_id": "returns_governed"}}
    plan = model_plan.build_scaffold_plan(
        _source_with_map(doc, cmap), "returns_dir_name_differs", _FACT
    )
    # recognized as a reuser via the governed id, despite the directory mismatch
    assert plan.reused_dimensions == ("dim_customer_rss",)
    assert "dim_customer_rss" not in {d.name for d in plan.dimensions}


def test_reuse_falls_back_to_source_id_then_directory_id() -> None:
    """Star-id resolution mirrors HR1: source_id when meta.table_id is absent, then
    the directory table_id as the last fallback (#419 review)."""
    # no meta.table_id -> resolve via source_id
    cmap = {
        "dimensions": {
            "dim_customer_rss": {"status": "conformed", "stars": [_OWNER_TABLE, "sid"]}
        }
    }
    doc = {k: v for k, v in _MAP.items() if k != "meta"}
    doc = {**doc, "source_id": "sid", "meta": {"grain": "one row"}}
    plan = model_plan.build_scaffold_plan(_source_with_map(doc, cmap), "any_dir", _FACT)
    assert plan.reused_dimensions == ("dim_customer_rss",)


def test_owner_is_stars0_even_if_it_is_repeated_later_in_the_list() -> None:
    """M1 regression: a human-duplicated owner entry (stars: [owner, reuser, owner])
    must NOT make the owner reuse its OWN dim -- else nobody materializes it and the
    reuser's ref() dangles. Owner is stars[0], compared directly (#418-P1)."""
    dup_map = {
        "dimensions": {
            "dim_customer_rss": {
                "status": "conformed",
                "stars": [_OWNER_TABLE, _REUSER_TABLE, _OWNER_TABLE],
            }
        }
    }
    owner_plan = model_plan.build_scaffold_plan(
        _source_with_map(_MAP, dup_map), _OWNER_TABLE, _FACT
    )
    # the owner still MATERIALIZES its own dim despite the duplicate entry
    assert "dim_customer_rss" in {d.name for d in owner_plan.dimensions}
    assert owner_plan.reused_dimensions == ()
    reuser_plan = model_plan.build_scaffold_plan(
        _source_with_map(_doc_for(_REUSER_TABLE), dup_map), _REUSER_TABLE, _FACT
    )
    assert reuser_plan.reused_dimensions == ("dim_customer_rss",)
    assert reuser_plan.reused_dimension_owners["dim_customer_rss"] == _OWNER_TABLE
