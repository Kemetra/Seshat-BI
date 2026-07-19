-- Governed parity audit: shadow dbt build vs the migration-built gold (the oracle).
-- Mirrors warehouse/gold's RC16 reconciliation. SK-AGNOSTIC by design: compares
-- counts / sums / distinct business keys only, NEVER surrogate-key values (the
-- migration used IDENTITY, the dbt dims use row_number(), so SKs legitimately differ).
-- Expected-side reads gold.* (migration); actual-side reads the dbt refs (shadow).
-- Expected RC16 values: fact rows 248,593; SUM(gross_sales) 38,804,001.54;
-- SUM(quantity) 286,098.392.
with parity_values as (
    select
        'fact_row_count'::text as assertion_id,
        'fact_row_count'::text as assertion_class,
        'fct_sales_c086'::text as subject,
        (select count(*)::numeric from {{ source('migration_gold', 'fct_sales_c086') }}) as expected_value,
        (select count(*)::numeric from {{ ref('fct_sales_c086') }}) as actual_value,
        0::numeric as tolerance_value

    union all

    -- composite business key (reference_no, item_no) -- NOT a single column.
    -- v0.5.1 requires the subject as <fact>.<col1>.<col2> (dot-joined, ordered),
    -- matching the approved grain key derived from gold_star.fact.business_key.
    select
        'fact_distinct_grain_key',
        'business_key_count',
        'fct_sales_c086.reference_no.item_no',
        (select count(distinct (reference_no, item_no))::numeric from {{ source('migration_gold', 'fct_sales_c086') }}),
        (select count(distinct (reference_no, item_no))::numeric from {{ ref('fct_sales_c086') }}),
        0::numeric

    union all

    select
        'fact_gross_sales_sum',
        'additive_money_total',
        'fct_sales_c086.gross_sales',
        (select coalesce(sum(gross_sales), 0)::numeric from {{ source('migration_gold', 'fct_sales_c086') }}),
        (select coalesce(sum(gross_sales), 0)::numeric from {{ ref('fct_sales_c086') }}),
        0.01::numeric

    -- NOTE: fact_quantity_sum (additive_quantity_total) and fact_return_row_count
    -- (flag_row_count) were dropped to conform to v0.5.1's 4-class governed parity
    -- enum (fact_row_count, business_key_count, dimension_member_count,
    -- additive_money_total). quantity is not money and is_return is a flag, so neither
    -- is a governed additive-money parity class; SUM(quantity) parity is still verified
    -- out-of-band in warehouse/gold's RC16 reconciliation.

    union all

    select
        'dim_product_member_count',
        'dimension_member_count',
        'dim_product_c086',
        (select count(*)::numeric from {{ source('migration_gold', 'dim_product_c086') }}),
        (select count(*)::numeric from {{ ref('dim_product_c086') }}),
        0::numeric

    union all

    select
        'dim_billing_type_member_count',
        'dimension_member_count',
        'dim_billing_type_c086',
        (select count(*)::numeric from {{ source('migration_gold', 'dim_billing_type_c086') }}),
        (select count(*)::numeric from {{ ref('dim_billing_type_c086') }}),
        0::numeric

    union all

    select
        'dim_customer_member_count',
        'dimension_member_count',
        'dim_customer_c086',
        (select count(*)::numeric from {{ source('migration_gold', 'dim_customer_c086') }}),
        (select count(*)::numeric from {{ ref('dim_customer_c086') }}),
        0::numeric

    union all

    select
        'dim_staff_member_count',
        'dimension_member_count',
        'dim_staff_c086',
        (select count(*)::numeric from {{ source('migration_gold', 'dim_staff_c086') }}),
        (select count(*)::numeric from {{ ref('dim_staff_c086') }}),
        0::numeric

    union all

    select
        'dim_date_member_count',
        'dimension_member_count',
        'dim_date_c086',
        (select count(*)::numeric from {{ source('migration_gold', 'dim_date_c086') }}),
        (select count(*)::numeric from {{ ref('dim_date_c086') }}),
        0::numeric
)

select
    assertion_id,
    assertion_class,
    subject,
    expected_value::text as expected,
    actual_value::text as actual,
    abs(expected_value - actual_value)::text as delta,
    tolerance_value::text as tolerance,
    abs(expected_value - actual_value) <= tolerance_value as passed
from parity_values
order by assertion_id
