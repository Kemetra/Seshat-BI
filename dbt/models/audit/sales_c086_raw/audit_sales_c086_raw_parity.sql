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

    -- composite business key (reference_no, item_no) -- NOT a single column
    select
        'fact_distinct_grain_key',
        'business_key_count',
        'fct_sales_c086.(reference_no,item_no)',
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

    union all

    select
        'fact_quantity_sum',
        'additive_quantity_total',
        'fct_sales_c086.quantity',
        (select coalesce(sum(quantity), 0)::numeric from {{ source('migration_gold', 'fct_sales_c086') }}),
        (select coalesce(sum(quantity), 0)::numeric from {{ ref('fct_sales_c086') }}),
        0.001::numeric

    union all

    select
        'fact_return_row_count',
        'flag_row_count',
        'fct_sales_c086.is_return',
        (select count(*) filter (where is_return)::numeric from {{ source('migration_gold', 'fct_sales_c086') }}),
        (select count(*) filter (where is_return)::numeric from {{ ref('fct_sales_c086') }}),
        0::numeric

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
