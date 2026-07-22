"""The generated dbt model set must pass the gate's OWN validators, offline.

These tests feed the scaffold output straight through ``project`` (model
contracts) and ``evidence`` (parity coverage) -- the same functions the real
gate runs -- so a scaffold that would trip DBT_MODEL_CONTRACT_MISSING,
DBT_MODEL_AUTHORITY_INVALID, DBT_COLUMN_CITATION_MISSING, DBT_MODEL_ORPHANED, or
DBT_ARTIFACT_INTEGRITY (parity) fails here. Driver-free: no live DB, no dbt.
"""

from __future__ import annotations

import pytest
import yaml

from seshat.dbt.contracts import FactBinding
from seshat.dbt.scaffold import model_plan, sql_render, yaml_render

pytestmark = pytest.mark.unit

TABLE_ID = "retail_store_sales"
REVISION = "d" * 40
SELECTOR = f"seshat_table_{TABLE_ID}"
SOURCE_MAP = f"mappings/{TABLE_ID}/source-map.yaml"

# A committed-map-shaped gold_star: schema-qualified relation names (the
# fact_semantics normalization strips the `gold.` qualifier), one money measure,
# a date dimension. Mirrors mappings/retail_store_sales/source-map.yaml's shape.
_MAP = {
    "meta": {"table_id": TABLE_ID, "grain": "one row = one retail transaction"},
    "columns": [
        {
            "source_name": "transaction_id",
            "decision": "keep",
            "rename_to": "transaction_id",
            "silver_type": "text",
        },
        {
            "source_name": "customer_id",
            "decision": "keep",
            "rename_to": "customer_id",
            "silver_type": "text",
        },
        {
            "source_name": "total_spent",
            "decision": "keep",
            "rename_to": "total_spent",
            "silver_type": "numeric(12,2)",
        },
        {
            "source_name": "transaction_date",
            "decision": "keep",
            "rename_to": "transaction_date",
            "silver_type": "date",
        },
        {"source_name": "legacy_flag", "decision": "drop"},
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


def _source(document: dict) -> model_plan.MapSource:
    return model_plan.MapSource(
        document=document, source_map=SOURCE_MAP, source_map_revision=REVISION
    )


def _plan() -> model_plan.ScaffoldPlan:
    return model_plan.build_scaffold_plan(_source(_MAP), TABLE_ID, _FACT)


def _all_models(plan: model_plan.ScaffoldPlan):
    return (plan.staging, *plan.dimensions, plan.fact_model, plan.audit)


# --------------------------------------------------------------------------- #
# Model-plan derivation
# --------------------------------------------------------------------------- #
def test_plan_derives_the_full_star_with_normalized_names() -> None:
    plan = _plan()

    assert plan.staging.name == "stg_retail_store_sales"
    assert plan.fact_model.name == "fct_sales_rss"  # gold. qualifier stripped
    dim_names = {dim.name for dim in plan.dimensions}
    assert dim_names == {"dim_customer_rss", "dim_date_rss"}
    assert plan.audit.name == "audit_retail_store_sales_parity"


def test_exactly_one_model_is_the_fact_by_exclusion() -> None:
    """evidence._selected_fact_model finds the fact by EXCLUSION of dim_/stg_/audit_."""
    names = [model.name for model in _all_models(_plan())]
    facts = [name for name in names if not name.startswith(("dim_", "stg_", "audit_"))]
    assert facts == ["fct_sales_rss"]


# --------------------------------------------------------------------------- #
# The generated _models.yml passes project._model_contract with zero blockers
# --------------------------------------------------------------------------- #
def _context() -> object:
    from seshat.dbt.project import _ContractContext

    return _ContractContext(
        selector_name=SELECTOR,
        table_id=TABLE_ID,
        source_map=SOURCE_MAP,
        source_map_revision=REVISION,
    )


def test_generated_contracts_pass_the_model_validator() -> None:
    from seshat.dbt.project import _model_contract

    plan = _plan()
    context = _context()
    for model in _all_models(plan):
        document = yaml_render.render_models_document((model,), plan, SELECTOR)
        row = document["models"][0]
        blockers: list = []
        contract = _model_contract(context, row, blockers)
        assert blockers == [], (model.name, [b.code for b in blockers])
        assert contract is not None
        assert contract.authority == "derived"
        assert contract.business_key
        assert contract.columns


def test_every_column_cites_source_or_governed_derivation() -> None:
    plan = _plan()
    allowed = {"surrogate_key", "date_spine", "unknown_member", "parity_measure"}
    for model in _all_models(plan):
        for column in model.columns:
            assert column.source_columns or column.derivation in allowed, (
                model.name,
                column.name,
            )


def test_advisory_data_types_are_emitted_without_an_enforced_contract() -> None:
    """data_type surfaces the intended type (issue #406 item 3) but the contract is
    NOT enforced: the parity-proven worked example ships no enforced contract, and
    an enforced type guess would reject the human's correctly-typed completed SQL
    (e.g. an integer surrogate key vs a `text` guess). Advisory only."""
    plan = _plan()
    document = yaml_render.render_models_document(
        (plan.staging, plan.fact_model), plan, SELECTOR
    )
    staging = document["models"][0]
    fact = document["models"][1]

    assert "contract" not in staging["config"]
    total = next(c for c in staging["columns"] if c["name"] == "total_spent")
    assert total["data_type"] == "numeric(12,2)"
    # A derived column (the fact surrogate key) carries NO guessed data_type.
    sk = next(c for c in fact["columns"] if c["name"] == "fct_sales_rss_sk")
    assert "data_type" not in sk
    assert sk["meta"]["seshat"]["derivation"] == "surrogate_key"


# --------------------------------------------------------------------------- #
# The generated parity set passes evidence._validate_parity_set exactly
# --------------------------------------------------------------------------- #
def _parity_assertions(plan: model_plan.ScaffoldPlan):
    from seshat.dbt.contracts import ParityAssertion

    return tuple(
        ParityAssertion(
            assertion_id=row.assertion_id,
            assertion_class=row.assertion_class,
            subject=row.subject,
            expected="1",
            actual="1",
            delta="0",
            tolerance=row.tolerance,
            passed=True,
        )
        for row in plan.parity
    )


def _selected_unique_ids(plan: model_plan.ScaffoldPlan) -> tuple[str, ...]:
    names = [model.name for model in _all_models(plan)]
    return tuple(sorted(f"model.seshat_bi.{name}" for name in names))


def test_generated_parity_set_matches_the_built_graph_exactly() -> None:
    from seshat.dbt.evidence import _validate_parity_set

    plan = _plan()
    _validate_parity_set(
        _parity_assertions(plan),
        _selected_unique_ids(plan),
        plan.fact,
    )  # must not raise


def test_parity_subjects_have_the_governed_shape() -> None:
    plan = _plan()
    by_class: dict[str, list[str]] = {}
    for row in plan.parity:
        by_class.setdefault(row.assertion_class, []).append(row.subject)

    assert by_class["fact_row_count"] == ["fct_sales_rss"]
    assert by_class["business_key_count"] == ["fct_sales_rss.transaction_id"]
    assert by_class["additive_money_total"] == ["fct_sales_rss.total_spent"]
    assert set(by_class["dimension_member_count"]) == {
        "dim_customer_rss",
        "dim_date_rss",
    }


def test_parity_assertion_ids_are_safe_and_unique() -> None:
    import re

    plan = _plan()
    ids = [row.assertion_id for row in plan.parity]
    assert len(ids) == len(set(ids))
    for assertion_id in ids:
        assert re.fullmatch(r"[a-z][a-z0-9_]*", assertion_id), assertion_id


# --------------------------------------------------------------------------- #
# The generated audit SQL is gate-shaped (parse-able by evidence.parse_parity_rows)
# --------------------------------------------------------------------------- #
def test_audit_sql_emits_every_assertion_and_the_output_columns() -> None:
    plan = _plan()
    sql = sql_render.render_audit_sql(plan).lower()

    for row in plan.parity:
        assert f"'{row.assertion_id}'" in sql
        assert f"'{row.subject}'" in sql
    for output in ("assertion_id", "assertion_class", "subject", "passed"):
        assert f" as {output}" in sql
    assert "source('migration_gold', 'fct_sales_rss')" in sql
    assert "ref('fct_sales_rss')" in sql


def test_skeleton_sql_selects_exactly_the_contract_columns() -> None:
    plan = _plan()
    staging_sql = sql_render.render_staging_sql(plan)

    for column in plan.staging.columns:
        assert f"as {column.name}" in staging_sql
    assert "TODO" in staging_sql


def test_factless_fact_needs_no_money_assertions() -> None:
    factless_map = {
        **_MAP,
        "gold_star": {
            **_MAP["gold_star"],
            "fact": {
                **_MAP["gold_star"]["fact"],
                "measures": [],
                "additive_money_measures": [],
            },
        },
    }
    fact = FactBinding(
        name="fct_sales_rss",
        business_key=("transaction_id",),
        additive_money_measures=(),
    )
    plan = model_plan.build_scaffold_plan(_source(factless_map), TABLE_ID, fact)

    money = [r for r in plan.parity if r.assertion_class == "additive_money_total"]
    assert money == []


def test_scaffold_error_on_missing_gold_star() -> None:
    with pytest.raises(model_plan.ScaffoldError):
        model_plan.build_scaffold_plan(
            _source({"meta": {"table_id": TABLE_ID}}), TABLE_ID, _FACT
        )


def test_rendered_models_document_is_valid_yaml() -> None:
    plan = _plan()
    document = yaml_render.render_models_document(plan.dimensions, plan, SELECTOR)
    round_trip = yaml.safe_load(yaml.safe_dump(document))

    assert round_trip["version"] == 2
    assert len(round_trip["models"]) == len(plan.dimensions)


# --------------------------------------------------------------------------- #
# BLOCKER 2 regression -- provenance is never fabricated
# --------------------------------------------------------------------------- #
# A map whose gold columns are RENAMED from their bronze source_name, so a
# citation to the silver name (the bug) is a bronze column that does not exist.
_RENAMED_MAP = {
    "meta": {"table_id": TABLE_ID, "grain": "one row = one txn"},
    "columns": [
        {"source_name": "TxnId", "decision": "keep", "rename_to": "transaction_id"},
        {"source_name": "CustId", "decision": "keep", "rename_to": "customer_id"},
        {
            "source_name": "TotalSpent",
            "decision": "keep",
            "rename_to": "total_spent",
            "silver_type": "numeric(12,2)",
        },
        {"source_name": "TxnDate", "decision": "keep", "rename_to": "transaction_date"},
    ],
    "gold_star": {
        "fact": {
            "name": "gold.fct_sales_rss",
            "business_key": "transaction_id",
            "measures": ["total_spent"],
            "additive_money_measures": ["total_spent"],
        },
        "dimensions": [
            {
                "name": "gold.dim_customer_rss",
                "surrogate_key": "customer_sk",
                "attributes": ["customer_id"],
            },
        ],
        "date_dimension": {"name": "gold.dim_date_rss", "surrogate_key": "date_sk"},
    },
}


def _renamed_plan() -> model_plan.ScaffoldPlan:
    return model_plan.build_scaffold_plan(_source(_RENAMED_MAP), TABLE_ID, _FACT)


def test_fact_cites_the_real_bronze_source_name_not_the_renamed_name() -> None:
    plan = _renamed_plan()
    bk = next(c for c in plan.fact_model.columns if c.name == "transaction_id")
    money = next(c for c in plan.fact_model.columns if c.name == "total_spent")

    assert bk.source_columns == (f"bronze.{TABLE_ID}.TxnId",)
    assert money.source_columns == (f"bronze.{TABLE_ID}.TotalSpent",)


def test_dim_attribute_cites_the_real_bronze_source_name() -> None:
    plan = _renamed_plan()
    dim = next(d for d in plan.dimensions if d.name == "dim_customer_rss")
    attr = next(c for c in dim.columns if c.name == "customer_id")

    assert attr.source_columns == (f"bronze.{TABLE_ID}.CustId",)


def test_fact_and_dim_surrogate_keys_are_derivations_not_fabricated_citations() -> None:
    plan = _renamed_plan()
    fact_sk = next(c for c in plan.fact_model.columns if c.name == "fct_sales_rss_sk")
    customer_fk = next(c for c in plan.fact_model.columns if c.name == "customer_sk")
    date_fk = next(c for c in plan.fact_model.columns if c.name == "date_sk")

    for column in (fact_sk, customer_fk, date_fk):
        assert column.derivation == "surrogate_key", column.name
        assert column.source_columns == ()  # no fabricated bronze citation


def test_gold_star_reference_to_unstaged_column_fails_closed() -> None:
    broken = {
        **_RENAMED_MAP,
        "columns": [
            c for c in _RENAMED_MAP["columns"] if c["rename_to"] != "total_spent"
        ],
    }
    # total_spent is still an additive_money_measure but no longer staged.
    with pytest.raises(model_plan.ScaffoldError, match="total_spent"):
        model_plan.build_scaffold_plan(_source(broken), TABLE_ID, _FACT)


# --------------------------------------------------------------------------- #
# Item 3 regression -- key tests target the correct column
# --------------------------------------------------------------------------- #
def test_staging_key_tests_target_the_grain_key_not_the_first_map_column() -> None:
    """The grain key is NOT first in map order (transaction_id is column 3 here),
    so keying tests on columns[0] would assert uniqueness on the wrong column."""
    reordered = {
        **_MAP,
        "columns": [
            {
                "source_name": "customer_id",
                "decision": "keep",
                "rename_to": "customer_id",
            },
            {
                "source_name": "total_spent",
                "decision": "keep",
                "rename_to": "total_spent",
            },
            {
                "source_name": "transaction_id",
                "decision": "keep",
                "rename_to": "transaction_id",
            },
        ],
    }
    plan = model_plan.build_scaffold_plan(_source(reordered), TABLE_ID, _FACT)
    doc = yaml_render.render_models_document((plan.staging,), plan, SELECTOR)
    columns = doc["models"][0]["columns"]

    tested = [c["name"] for c in columns if "data_tests" in c]
    assert tested == ["transaction_id"]  # the grain key, not customer_id (col 0)


def test_dimension_key_tests_target_the_surrogate_not_the_natural_key() -> None:
    """A dim's -1 unknown-member row has a NULL natural key, so not_null must sit
    on the surrogate key, never the natural business key."""
    plan = _plan()
    dim = next(d for d in plan.dimensions if d.name == "dim_customer_rss")
    doc = yaml_render.render_models_document((dim,), plan, SELECTOR)
    columns = doc["models"][0]["columns"]

    tested = [c["name"] for c in columns if "data_tests" in c]
    assert tested == ["customer_sk"]  # the surrogate, not customer_id


# --------------------------------------------------------------------------- #
# Items 6 & 7 regression -- fail closed on unbuildable star shapes
# --------------------------------------------------------------------------- #
def test_non_dim_prefixed_dimension_fails_closed() -> None:
    bad = {
        **_MAP,
        "gold_star": {
            **_MAP["gold_star"],
            "dimensions": [
                {
                    "name": "gold.customer",
                    "surrogate_key": "customer_sk",
                    "attributes": ["customer_id"],
                },
            ],
        },
    }
    with pytest.raises(model_plan.ScaffoldError, match="dim_"):
        model_plan.build_scaffold_plan(_source(bad), TABLE_ID, _FACT)


def test_non_identifier_dimension_attribute_fails_closed() -> None:
    bad = {
        **_MAP,
        "gold_star": {
            **_MAP["gold_star"],
            "dimensions": [
                {
                    "name": "gold.dim_customer_rss",
                    "surrogate_key": "customer_sk",
                    "attributes": ["Bad Name"],
                },
            ],
        },
    }
    with pytest.raises(model_plan.ScaffoldError, match="attribute"):
        model_plan.build_scaffold_plan(_source(bad), TABLE_ID, _FACT)


def test_fact_named_with_reserved_prefix_fails_closed() -> None:
    fact = FactBinding(
        name="dim_sales",  # would be misclassified as a dimension by evidence
        business_key=("transaction_id",),
        additive_money_measures=("total_spent",),
    )
    with pytest.raises(model_plan.ScaffoldError, match="dim_/stg_/audit_"):
        model_plan.build_scaffold_plan(_source(_MAP), TABLE_ID, fact)


# --------------------------------------------------------------------------- #
# FIX 1 regression -- composite grain never emits a single-column `unique`
# --------------------------------------------------------------------------- #
_COMPOSITE_MAP = {
    "meta": {"table_id": TABLE_ID, "grain": "one row = one invoice line"},
    "columns": [
        {"source_name": "invoice_no", "decision": "keep", "rename_to": "invoice_no"},
        {"source_name": "line_no", "decision": "keep", "rename_to": "line_no"},
        {
            "source_name": "amount",
            "decision": "keep",
            "rename_to": "amount",
            "silver_type": "numeric(12,2)",
        },
    ],
    "gold_star": {
        "fact": {
            "name": "gold.fct_lines_rss",
            "business_key": ["invoice_no", "line_no"],
            "measures": ["amount"],
            "additive_money_measures": ["amount"],
        },
        "dimensions": [
            {
                "name": "gold.dim_invoice_rss",
                "surrogate_key": "invoice_sk",
                "attributes": ["invoice_no"],
            },
        ],
    },
}
_COMPOSITE_FACT = FactBinding(
    name="fct_lines_rss",
    business_key=("invoice_no", "line_no"),
    additive_money_measures=("amount",),
)


def _test_names(column: dict) -> set[str]:
    return {next(iter(t)) for t in column.get("data_tests", [])}


def test_composite_grain_staging_has_no_single_column_unique() -> None:
    """A composite grain [invoice_no, line_no] must NOT put `unique` on either
    component alone (that fails on correct data); both get `not_null`."""
    plan = model_plan.build_scaffold_plan(
        _source(_COMPOSITE_MAP), TABLE_ID, _COMPOSITE_FACT
    )
    doc = yaml_render.render_models_document((plan.staging,), plan, SELECTOR)
    by_name = {c["name"]: c for c in doc["models"][0]["columns"]}

    assert "unique" not in _test_names(by_name["invoice_no"])
    assert "unique" not in _test_names(by_name["line_no"])
    assert "not_null" in _test_names(by_name["invoice_no"])
    assert "not_null" in _test_names(by_name["line_no"])
    # No column anywhere in the composite-grain staging model carries `unique`.
    assert all("unique" not in _test_names(c) for c in doc["models"][0]["columns"])


def test_single_column_grain_staging_keeps_unique_and_not_null() -> None:
    """The single-column case is unchanged: the grain key is unique + not_null."""
    plan = _plan()
    doc = yaml_render.render_models_document((plan.staging,), plan, SELECTOR)
    by_name = {c["name"]: c for c in doc["models"][0]["columns"]}

    assert _test_names(by_name["transaction_id"]) == {"unique", "not_null"}


# --------------------------------------------------------------------------- #
# FIX 2 regression -- unstaged reference remedy names the derived_columns path
# --------------------------------------------------------------------------- #
# --------------------------------------------------------------------------- #
# FIX #1 regression -- the fact carries EVERY governed column, not just money
# --------------------------------------------------------------------------- #
# A map that declares a NON-money measure (quantity, additive but not money) and a
# DEGENERATE dimension (discount_applied) -- both real fact columns the human
# declared that the pre-fix _fact_columns dropped. Both are staged in columns[]
# (renamed from a distinct bronze source_name) so their provenance is verifiable.
_FULL_FACT_MAP = {
    "meta": {"table_id": TABLE_ID, "grain": "one row = one retail transaction"},
    "columns": [
        {"source_name": "TxnId", "decision": "keep", "rename_to": "transaction_id"},
        {"source_name": "CustId", "decision": "keep", "rename_to": "customer_id"},
        {
            "source_name": "Qty",
            "decision": "keep",
            "rename_to": "quantity",
            "silver_type": "numeric(12,2)",
        },
        {
            "source_name": "TotalSpent",
            "decision": "keep",
            "rename_to": "total_spent",
            "silver_type": "numeric(12,2)",
        },
        {
            "source_name": "Discount",
            "decision": "keep",
            "rename_to": "discount_applied",
            "silver_type": "boolean",
        },
    ],
    "gold_star": {
        "fact": {
            "name": "gold.fct_sales_rss",
            "business_key": "transaction_id",
            "measures": ["quantity", "total_spent"],
            "additive_money_measures": ["total_spent"],
        },
        "dimensions": [
            {
                "name": "gold.dim_customer_rss",
                "surrogate_key": "customer_sk",
                "attributes": ["customer_id"],
            },
        ],
        "degenerate_dimensions": ["transaction_id", "discount_applied"],
    },
}


def _full_fact_plan() -> model_plan.ScaffoldPlan:
    return model_plan.build_scaffold_plan(_source(_FULL_FACT_MAP), TABLE_ID, _FACT)


def test_fact_includes_non_money_measure_and_degenerate_dim() -> None:
    """The fact must carry the non-money measure (quantity) and the degenerate dim
    (discount_applied) the map declares -- not only the additive money measure."""
    plan = _full_fact_plan()
    by_name = {c.name: c for c in plan.fact_model.columns}

    # Non-money measure and degenerate dim are present, cited to REAL bronze names.
    assert by_name["quantity"].source_columns == (f"bronze.{TABLE_ID}.Qty",)
    assert by_name["total_spent"].source_columns == (f"bronze.{TABLE_ID}.TotalSpent",)
    assert by_name["discount_applied"].source_columns == (
        f"bronze.{TABLE_ID}.Discount",
    )
    # None of them fabricates a citation or claims a spurious derivation.
    for name in ("quantity", "total_spent", "discount_applied"):
        assert by_name[name].derivation is None


def test_fact_columns_carry_the_mapped_silver_type() -> None:
    """A source-cited fact column (grain key, measure, degenerate dim) must carry
    the map's ``silver_type`` as its advisory ``data_type``, consistent with the
    staging model (#418-P2). Before the fix these ColumnSpecs defaulted to ``text``
    regardless of the mapped target type, so the generated native contract's
    ``data_type`` did not reflect the map."""
    plan = _full_fact_plan()
    by_name = {c.name: c for c in plan.fact_model.columns}

    # Measures and the degenerate dim reflect their mapped silver_type...
    assert by_name["quantity"].data_type == "numeric(12,2)"
    assert by_name["total_spent"].data_type == "numeric(12,2)"
    assert by_name["discount_applied"].data_type == "boolean"
    # ...and the advisory type surfaces in the rendered contract, unenforced.
    document = yaml_render.render_models_document((plan.fact_model,), plan, SELECTOR)
    fact = document["models"][0]
    assert "contract" not in fact["config"]
    qty = next(c for c in fact["columns"] if c["name"] == "quantity")
    assert qty["data_type"] == "numeric(12,2)"
    # A derived FK still carries NO guessed data_type (surrogate key).
    fk = next(c for c in fact["columns"] if c["name"] == "customer_sk")
    assert "data_type" not in fk


def test_fact_column_without_a_mapped_silver_type_defaults_to_text() -> None:
    """A source-cited fact column whose kept row has no ``silver_type`` keeps the
    ``text`` default (the pre-#418 behavior for unspecified types)."""
    plan = _renamed_plan()  # TxnId/CustId rows carry no silver_type
    bk = next(c for c in plan.fact_model.columns if c.name == "transaction_id")
    assert bk.data_type == "text"


def test_fact_column_set_is_exactly_the_governed_columns() -> None:
    """The complete governed set: synthetic PK + business key + one FK per dim +
    every declared measure + every degenerate dim, with the business-key/degenerate
    overlap (transaction_id) collapsed to a single column."""
    plan = _full_fact_plan()
    names = [c.name for c in plan.fact_model.columns]

    assert set(names) == {
        "fct_sales_rss_sk",  # synthetic PK
        "transaction_id",  # business key == a degenerate dim (deduped to one)
        "customer_sk",  # dimension FK
        "quantity",  # non-money measure
        "total_spent",  # money measure
        "discount_applied",  # degenerate dim
    }
    assert len(names) == len(set(names))  # transaction_id appears exactly once


def test_fact_degenerate_reference_to_unstaged_column_fails_closed() -> None:
    """A degenerate dimension that no kept columns[] row maps to fails closed
    (never a fabricated citation) -- same posture as the measure/key path."""
    broken = {
        **_FULL_FACT_MAP,
        "gold_star": {
            **_FULL_FACT_MAP["gold_star"],
            "degenerate_dimensions": ["transaction_id", "not_staged_flag"],
        },
    }
    with pytest.raises(model_plan.ScaffoldError, match="not_staged_flag"):
        model_plan.build_scaffold_plan(_source(broken), TABLE_ID, _FACT)


# --------------------------------------------------------------------------- #
# FIX #2 regression -- composite grain count(distinct) is valid PostgreSQL
# --------------------------------------------------------------------------- #
def test_composite_business_key_audit_counts_a_row_expression() -> None:
    """A composite key must render count(distinct (a, b)) -- a ROW expression --
    because Postgres count() rejects count(distinct a, b)."""
    plan = model_plan.build_scaffold_plan(
        _source(_COMPOSITE_MAP), TABLE_ID, _COMPOSITE_FACT
    )
    sql = sql_render.render_audit_sql(plan)

    assert "count(distinct (invoice_no, line_no))" in sql
    assert "count(distinct invoice_no, line_no)" not in sql  # the rejected form


def test_single_column_business_key_audit_counts_the_bare_column() -> None:
    """A single-column key stays the plain count(distinct col) -- no parens churn."""
    sql = sql_render.render_audit_sql(_plan())

    assert "count(distinct transaction_id)" in sql


# --------------------------------------------------------------------------- #
# #414 -- a derived_columns (RC11 rollup) dim attribute cites its derived_from
# bronze source instead of failing closed; a placeholder/unresolvable one still
# fails closed (never a fabricated citation).
# --------------------------------------------------------------------------- #
def _rollup_map(derived_from: str) -> dict:
    """A map whose dim attribute (customer_segment) is an RC11 rollup living in
    derived_columns, deriving from ``derived_from`` (a real bronze source col)."""
    return {
        **_MAP,
        "columns": [
            # customer_segment_code is the AUTHORITATIVE bronze source the rollup
            # derives from; it is kept so its bronze source_name is verifiable.
            {
                "source_name": "cust_seg_code",
                "decision": "keep",
                "rename_to": "customer_segment_code",
            },
            *_MAP["columns"],
        ],
        "derived_columns": [
            {
                "name": "customer_segment",
                "type": "text",
                "derived_from": derived_from,
                "mapping_source": "templates/assumptions.md",
                "unmapped_default": "UNMAPPED",
            }
        ],
        "gold_star": {
            **_MAP["gold_star"],
            "dimensions": [
                {
                    "name": "gold.dim_customer_rss",
                    "surrogate_key": "customer_sk",
                    "attributes": ["customer_segment"],
                },
            ],
        },
    }


def test_derived_rollup_attribute_cites_its_derived_from_bronze_source() -> None:
    """A dim attribute whose provenance is a derived_columns rollup (RC11) now cites
    its ``derived_from`` bronze source -- a governed derivation citing the real
    bronze column, scaffolded end-to-end (#414), NOT failing closed and NOT
    fabricating a citation to the derived (bronze-absent) name."""
    plan = model_plan.build_scaffold_plan(
        _source(_rollup_map("customer_segment_code")), TABLE_ID, _FACT
    )
    dim = next(d for d in plan.dimensions if d.name == "dim_customer_rss")
    attr = next(c for c in dim.columns if c.name == "customer_segment")
    # customer_segment_code renames the bronze `cust_seg_code`, so the citation
    # resolves THROUGH the provenance authority to the real bronze source_name.
    assert attr.source_columns == (f"bronze.{TABLE_ID}.cust_seg_code",)


def test_derived_rollup_from_a_direct_bronze_source_name() -> None:
    """``derived_from`` may name a bronze ``source_name`` directly (not a silver
    rename); the citation resolves to that exact bronze column (#414)."""
    plan = model_plan.build_scaffold_plan(
        # derive straight from the raw bronze source_name of a kept column
        _source(_rollup_map("cust_seg_code")),
        TABLE_ID,
        _FACT,
    )
    dim = next(d for d in plan.dimensions if d.name == "dim_customer_rss")
    attr = next(c for c in dim.columns if c.name == "customer_segment")
    assert attr.source_columns == (f"bronze.{TABLE_ID}.cust_seg_code",)


def test_derived_rollup_with_placeholder_derived_from_fails_closed() -> None:
    """A rollup whose ``derived_from`` is an unfilled ``<placeholder>`` (or empty)
    is NOT a real citation -- it still fails closed with the derived_columns remedy,
    never fabricating provenance from the placeholder (#414)."""
    with pytest.raises(model_plan.ScaffoldError, match="derived_columns") as err:
        model_plan.build_scaffold_plan(
            _source(_rollup_map("<grouping_dim_col>")), TABLE_ID, _FACT
        )
    assert "customer_segment" in str(err.value)


def test_derived_rollup_whose_derived_from_is_not_in_bronze_fails_closed() -> None:
    """A rollup deriving from a column that no kept row maps to a real bronze
    source still fails closed -- the derived_from must resolve to a bronze column
    that genuinely exists, never a fabricated one (#414)."""
    with pytest.raises(model_plan.ScaffoldError) as err:
        model_plan.build_scaffold_plan(
            _source(_rollup_map("no_such_bronze_col")), TABLE_ID, _FACT
        )
    assert "customer_segment" in str(err.value)


def test_plain_missing_attribute_still_names_derived_columns_remedy() -> None:
    """An attribute that is neither a kept columns[] source NOR a derived_columns
    rollup still fails closed with the remedy naming BOTH paths (#414 keeps the
    original guidance for the genuinely-absent case)."""
    rollup_map = {
        **_MAP,
        "gold_star": {
            **_MAP["gold_star"],
            "dimensions": [
                {
                    "name": "gold.dim_customer_rss",
                    "surrogate_key": "customer_sk",
                    "attributes": ["customer_segment"],  # nowhere in the map
                },
            ],
        },
    }
    with pytest.raises(model_plan.ScaffoldError, match="derived_columns") as err:
        model_plan.build_scaffold_plan(_source(rollup_map), TABLE_ID, _FACT)
    assert "customer_segment" in str(err.value)


# #418-P1 conformed-dimension reuse tests live in test_scaffold_conformed_reuse.py
# (self-contained, to keep this file focused and under the module-size threshold).
